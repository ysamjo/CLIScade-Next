from dataclasses import replace

from fastapi.testclient import TestClient

from cliscade_next.agents import Agent
from cliscade_next.api import create_app
from cliscade_next.ledger import Ledger


def test_task_model_is_validated_persisted_and_kept_on_resume(system):
    service, runner, settings = system
    service.agents["openhands"] = Agent("openhands", (), model="openai/c1")
    runner.probe = lambda agent: {
        "available_models": [{"model_id": model} for model in ("openai/c1", "other")]
    }
    seen = []
    original = runner.attach

    def attach(agent, workspace, session_id=None):
        seen.append(agent)
        return original(agent, workspace, session_id)

    runner.attach = attach
    with TestClient(create_app(settings, service)) as client:
        client.headers["X-Session-API-Key"] = "key"
        url = "/cliscade/v1/projects/project/attempts"
        body = {
            "task_id": "cn-1",
            "agent_id": "openhands",
            "model": "openai/c1",
            "request_key": "run-1",
        }
        invalid = client.post(url, json=body | {"model": "not-offered"})
        assert invalid.status_code == 400
        assert service.ledger.list("project") == []
        first = client.post(url, json=body).json()
        assert first["status"] == "running"
        assert first["model"] == seen[-1].model == "openai/c1"
        assert client.post(url, json=body).json()["id"] == first["id"]
        assert client.post(url, json=body | {"model": "other"}).status_code == 400
        service.cancel(first["id"])
        service.agents["openhands"] = replace(
            service.agents["openhands"], model="other"
        )
        resumed = service.resume(first["id"])
        assert resumed["model"] == "openai/c1"
        assert seen[-1].model == "openai/c1"
        assert Ledger(settings.state).get(resumed["id"])["model"] == "openai/c1"
        service.cancel(resumed["id"])
        handoff = client.post(
            url,
            json={
                "task_id": "cn-1",
                "agent_id": "two",
                "model": "other",
                "source_id": resumed["id"],
            },
        ).json()
        assert handoff["model"] == seen[-1].model == "other"
        assert handoff["workspace"] == first["workspace"]
        assert handoff["checkpoint"]["source_attempt"] == resumed["id"]
        assert service.agents["two"].model is None


def test_existing_ledger_adds_model_without_losing_session(system):
    service, _, settings = system
    first = service.start("project", "cn-1", "one")
    with service.ledger.connect() as db:
        db.execute("ALTER TABLE attempts DROP COLUMN model")
    saved = Ledger(settings.state).get(first["id"])
    assert saved["model"] is None
    assert saved["session_id"] == first["session_id"]


def test_auto_route_does_not_silently_ignore_a_requested_model(system):
    service, _, settings = system
    with TestClient(create_app(settings, service)) as client:
        response = client.post(
            "/cliscade/v1/projects/project/attempts",
            headers={"X-Session-API-Key": "key"},
            json={"task_id": "cn-1", "agent_id": "auto", "model": "specific"},
        )
    assert response.status_code == 400
    assert service.ledger.list("project") == []


def test_native_checks_need_matching_tool_receipts_and_completed_processes():
    from openhands.sdk.tool.schema import Action, Observation
    from openhands.tools.terminal.definition import TerminalAction, TerminalObservation

    from cliscade_next.orchestrator import evidence

    wire_action = Action.model_validate(
        TerminalAction(command="pytest -q").model_dump(mode="json")
    )
    wire_observation = Observation.model_validate(
        TerminalObservation(command="pytest -q", exit_code=0).model_dump(mode="json")
    )
    action = {
        "kind": "ActionEvent",
        "id": "a1",
        "tool_name": "terminal",
        "tool_call_id": "t1",
        "action": wire_action.model_dump(mode="json"),
    }
    observation = {
        "kind": "ObservationEvent",
        "action_id": "a1",
        "tool_name": "terminal",
        "tool_call_id": "t1",
        "observation": wire_observation.model_dump(mode="json"),
    }
    assert evidence([observation])[0] == []
    assert evidence([action, observation | {"tool_call_id": "wrong"}])[0] == []
    assert evidence([action, observation | {"observation": {"exit_code": -1}}])[0] == []
    checks, _ = evidence([action, observation])
    assert checks[0]["command"] == "pytest -q"
    assert checks[0]["exit_code"] == 0
    assert checks[0]["independently_reproduced"] is False


def test_polling_a_live_dispatch_does_not_mark_preparation_as_interrupted(system):
    service, runner, _ = system
    original = runner.attach

    def attach(agent, workspace, session_id=None):
        preparing = service.ledger.list("project")[-1]
        observed = service.refresh(preparing["id"])
        assert observed["status"] == "preparing"
        assert observed["error"] is None
        return original(agent, workspace, session_id)

    runner.attach = attach
    result = service.start("project", "cn-1", "one")
    assert result["status"] == "running"
    assert result["error"] is None
    orphan = service.ledger.create("project", "cn-2", "one", "/unused-test-workspace")
    assert service.refresh(orphan["id"])["status"] == "needs_review"
