from fastapi.testclient import TestClient

from cliscade_next.api import create_app
from cliscade_next.config import Settings
from cliscade_next.context import Handoff, report_from_claims
from cliscade_next.orchestrator import evidence


def test_api_requires_key_and_refuses_unknown_provider_and_extra_task_fields(tmp_path):
    (tmp_path / "project").mkdir()
    app = create_app(
        Settings(tmp_path, tmp_path / "state", "http://localhost:8000", "test-key")
    )
    client = TestClient(app)
    assert client.get("/cliscade/v1/projects").status_code == 401
    client.headers["X-Session-API-Key"] = "test-key"
    assert client.get("/cliscade/v1/projects").json()[0]["id"] == "project"
    assert (
        client.post(
            "/cliscade/v1/projects/project/attempts",
            json={
                "task_id": "cn-1",
                "agent_id": "sh -c arbitrary",
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/cliscade/v1/projects/project/tasks",
            json={
                "title": "Test",
                "shell": "arbitrary",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/cliscade/v1/projects/project/attempts",
            json={
                "task_id": "--help",
                "agent_id": "codex",
            },
        ).status_code
        == 422
    )


def test_claimed_checks_are_not_tool_evidence_and_budget_preserves_rules():
    checks, claims = evidence(
        [
            {
                "kind": "MessageEvent",
                "source": "agent",
                "llm_message": {
                    "content": [{"type": "text", "text": "pytest exit_code=0"}]
                },
            }
        ]
    )
    assert checks == [] and claims[0]["verified"] is False
    handoff = Handoff(
        task={"id": "cn-1"},
        rules=[{"text": "Regeln behalten"}],
        project_knowledge={"big": "x" * 70000},
        git={"revision": "abc"},
    )
    prompt = handoff.prompt()
    assert len(prompt) <= 64000
    assert "Regeln behalten" in prompt and "project_knowledge" in prompt
    assert '"omitted": ["project_knowledge"]' in prompt


def test_structured_agent_report_cannot_claim_verified_checks():
    report = report_from_claims(
        [
            {
                "message": '<cliscade-report>{"schema_version":1,'
                '"decisions":["API behalten"],"open_steps":["Review"]}'
                "</cliscade-report>"
            }
        ]
    )
    assert report.decisions == ["API behalten"]
    assert report.open_steps == ["Review"]
    assert (
        report_from_claims(
            [
                {
                    "message": '<cliscade-report>{"schema_version":1,'
                    '"verified_checks":["pytest passed"]}</cliscade-report>'
                }
            ]
        )
        is None
    )
