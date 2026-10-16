import json
import subprocess
from pathlib import Path

import pytest

from cliscade_next.agents import Agent
from cliscade_next.config import Settings
from cliscade_next.ledger import Ledger
from cliscade_next.orchestrator import Orchestrator


class FakeBeads:
    def __init__(self, project):
        self.project = project

    def show(self, task_id):
        return {"id": task_id, "title": "Rechne", "acceptance_criteria": "Tests grün"}

    def context(self):
        return {"memories": {"rule": "Deutsche UI"}, "workflow": "bd ready"}

    def ensure_startable(self, task_id):
        return self.show(task_id)

    def update(self, task_id, **fields):
        return self.show(task_id) | fields

    def assign(self, task_id, agent_id, previous=None):
        return self.show(task_id) | {"assignee": agent_id}


class FakeSession:
    def __init__(self, session_id, state):
        self.id, self.value = session_id, state

    def submit(self, prompt):
        self.value["prompt"] = prompt
        if self.value.get("fail_submit"):
            raise RuntimeError("Verbindung unterbrochen")
        self.value["status"] = "running"

    def state(self):
        return self.value

    def cancel(self):
        self.value["status"] = "paused"

    def close(self):
        pass


class FakeOpenHands:
    def __init__(self):
        self.sessions = {}
        self.fail_submit = False

    def attach(self, agent, workspace, session_id=None):
        session_id = session_id or str(len(self.sessions) + 1)
        state = self.sessions.setdefault(
            session_id,
            {
                "status": "idle",
                "events": [],
                "fail_submit": self.fail_submit,
            },
        )
        return FakeSession(session_id, state)


@pytest.fixture
def system(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(project),
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=Test",
            "commit",
            "--allow-empty",
            "-qm",
            "Start",
        ],
        check=True,
    )
    settings = Settings(tmp_path, tmp_path / "state", "http://localhost:8000", "key")
    runner = FakeOpenHands()
    service = Orchestrator(
        settings,
        runner=runner,
        beads_factory=FakeBeads,
        agents={"one": Agent("one", ("one",)), "two": Agent("two", ("two",))},
        settle_seconds=0,
    )
    return service, runner, settings


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
