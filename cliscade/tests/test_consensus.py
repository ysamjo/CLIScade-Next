import subprocess
from pathlib import Path

import pytest

from cliscade_next.consensus import Consensus


def test_independent_worktrees_compare_untracked_content_without_merging(system):
    service, runner, settings = system
    group = Consensus(service).start("project", "cn-1", ["one", "two"])
    attempts = group["attempts"]
    assert len({item["workspace"] for item in attempts}) == 2
    for attempt, text in zip(
        attempts, ["first solution", "second solution"], strict=True
    ):
        Path(attempt["workspace"], "result.txt").write_text(text)
        runner.sessions[attempt["session_id"]]["status"] = "finished"
    result = Consensus(service).get(group["id"])
    assert result["status"] == "completed"
    assert result["result"]["patch_agreement"] is False
    assert result["result"]["correctness_verified"] is False
    assert not (settings.projects / "project/result.txt").exists()


def test_uncertain_consensus_start_never_launches_remaining_agents(system):
    service, runner, _ = system
    runner.fail_submit = True
    result = Consensus(service).start("project", "cn-1", ["one", "two"])
    assert result["status"] == "needs_review"
    assert len(runner.sessions) == 1
    assert result["result"]["patch_agreement"] is False


@pytest.mark.parametrize("binary", [False, True])
def test_committed_solutions_are_compared_against_the_common_revision(system, binary):
    service, runner, _ = system
    consensus = Consensus(service)
    group = consensus.start("project", "cn-1", ["one", "two"])
    for index, attempt in enumerate(group["attempts"]):
        workspace = Path(attempt["workspace"])
        (workspace / "result.txt").write_bytes(
            bytes([0, index + 1]) if binary else f"solution {index}".encode()
        )
        commit(workspace)
        runner.sessions[attempt["session_id"]]["status"] = "finished"
    result = consensus.get(group["id"])
    assert result["status"] == "completed"
    assert result["result"]["patch_agreement"] is False
    assert all(item["diff"] for item in result["result"]["results"])


def test_symlink_and_regular_file_are_not_the_same_result(system):
    service, runner, _ = system
    consensus = Consensus(service)
    group = consensus.start("project", "cn-1", ["one", "two"])
    first, second = group["attempts"]
    (Path(first["workspace"]) / "result").symlink_to("target")
    (Path(second["workspace"]) / "result").write_text("target")
    for attempt in group["attempts"]:
        runner.sessions[attempt["session_id"]]["status"] = "finished"
    assert consensus.get(group["id"])["result"]["patch_agreement"] is False


def commit(workspace):
    subprocess.run(["git", "-C", str(workspace), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(workspace),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Lösung sichern",
        ],
        check=True,
    )


def test_handoff_keeps_changes_committed_by_previous_agent(system):
    service, runner, _ = system
    first = service.start("project", "cn-1", "one")
    workspace = Path(first["workspace"])
    (workspace / "result.txt").write_text("committed solution")
    commit(workspace)
    runner.sessions[first["session_id"]]["status"] = "finished"
    first = service.refresh(first["id"])
    second = service.start("project", "cn-1", "two", source_id=first["id"])
    assert second["checkpoint"]["git"]["base_revision"] == first["base_revision"]
    assert "+committed solution" in second["checkpoint"]["git"]["diff"]


def test_consensus_carries_the_chosen_model_per_participant(system):
    service, runner, settings = system
    group = Consensus(service).start(
        "project", "cn-1", ["one", "two"], models={"two": "special/model"}
    )
    models = {
        attempt["agent"]: attempt["model"] for attempt in group["attempts"]
    }
    assert models == {"one": None, "two": "special/model"}
    # Der Ledger trägt das Modell, damit die Auswahl über den Lauf hinaus sichtbar bleibt.
    for attempt in group["attempts"]:
        saved = service.ledger.get(attempt["id"])
        assert saved["model"] == attempt["model"]


def test_model_for_a_non_participant_is_refused(system):
    service, _, _ = system
    with pytest.raises(ValueError, match="keinem Teilnehmer"):
        Consensus(service).start(
            "project", "cn-1", ["one", "two"], models={"three": "x/y"}
        )
