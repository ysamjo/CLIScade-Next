import json
from pathlib import Path

import pytest
from helpers import FakeBeads

from cliscade_next.ledger import Ledger
from cliscade_next.orchestrator import Orchestrator


def test_task_execution_restart_and_handoff_preserve_uncommitted_files(system):
    service, runner, settings = system
    first = service.start("project", "cn-1", "one")
    workspace = Path(first["workspace"])
    (workspace / "result.txt").write_text("Arbeitsstand")
    runner.sessions[first["session_id"]].update(
        status="finished",
        events=[
            {
                "kind": "MessageEvent",
                "source": "agent",
                "llm_message": {
                    "content": [{"type": "text", "text": "Alle Tests grün"}]
                },
            }
        ],
    )
    recovered = Orchestrator(
        settings,
        runner=runner,
        beads_factory=FakeBeads,
        agents=service.agents,
        settle_seconds=0,
    )
    first = recovered.refresh(first["id"])
    assert first["status"] == "completed"
    assert first["checkpoint"]["verified_checks"] == []
    second = recovered.start("project", "cn-1", "two", source_id=first["id"])
    prompt = json.loads(
        runner.sessions[second["session_id"]]["prompt"].split("\n", 1)[1]
    )
    assert prompt["task"]["acceptance_criteria"] == "Tests grün"
    assert prompt["source_attempt"] == first["id"]
    assert "result.txt" in prompt["git"]["status"]
    assert prompt["agent_claims"]
    assert Path(second["workspace"], "result.txt").read_text() == "Arbeitsstand"
    assert Ledger(settings.state).get(second["id"])["session_id"] != first["session_id"]


def test_uncertain_prompt_delivery_never_replays_and_active_workspace_is_locked(system):
    service, runner, _ = system
    runner.fail_submit = True
    attempt = service.start("project", "cn-1", "one")
    assert attempt["status"] == "uncertain"
    assert attempt["prompt_sent"]
    with pytest.raises(ValueError, match="Unsicher"):
        service.start("project", "cn-1", "two", source_id=attempt["id"])


def test_cancellation_and_handoff_scope(system):
    service, runner, _ = system
    attempt = service.start("project", "cn-1", "one")
    assert service.cancel(attempt["id"])["status"] == "cancelled"
    with pytest.raises(ValueError, match="anderen Aufgabe"):
        service.start("project", "cn-2", "two", source_id=attempt["id"])


def test_resume_is_a_new_attempt_in_the_same_session(system):
    service, runner, _ = system
    first = service.start("project", "cn-1", "one")
    service.cancel(first["id"])
    resumed = service.resume(first["id"])
    assert resumed["id"] != first["id"]
    assert resumed["session_id"] == first["session_id"]
    assert resumed["source_id"] == first["id"]
    assert runner.sessions[first["session_id"]]["status"] == "running"


def test_request_id_survives_restart_without_duplicate_session(system):
    service, runner, settings = system
    first = service.start("project", "cn-1", "one", request_key="automation-run-1")
    restarted = Orchestrator(
        settings, runner=runner, beads_factory=FakeBeads, agents=service.agents
    )
    assert (
        restarted.start("project", "cn-1", "one", request_key="automation-run-1")["id"]
        == first["id"]
    )
    assert len(runner.sessions) == 1
    with pytest.raises(ValueError, match="andere Parameter"):
        restarted.start("project", "cn-2", "one", request_key="automation-run-1")


def test_existing_ledger_adds_baseline_column_without_losing_attempts(system):
    from cliscade_next.ledger import Ledger

    service, _, settings = system
    attempt = service.start("project", "cn-1", "one")
    with service.ledger.connect() as db:
        db.execute("ALTER TABLE attempts DROP COLUMN base_revision")
    saved = Ledger(settings.state).get(attempt["id"])
    assert saved["session_id"] == attempt["session_id"]
    assert saved["base_revision"] is None
