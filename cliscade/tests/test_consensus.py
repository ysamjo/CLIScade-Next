from pathlib import Path

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
