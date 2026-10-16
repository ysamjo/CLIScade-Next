from types import SimpleNamespace

from cliscade_next.agents import Agent
from cliscade_next.routing import Routing


def test_fallback_skips_bad_models_and_auth_without_replaying_uncertain_prompt(
    tmp_path,
):
    starts = []

    def probe(agent):
        if agent.id == "first":
            return {"error": {"code": "ACPAuthRequired"}}
        return {"available_models": [{"model_id": "supported"}]}

    def start(project, task, agent, source_id=None, **options):
        starts.append(agent)
        return {"id": "attempt", "prompt_sent": True, "status": "uncertain"}

    service = SimpleNamespace(
        settings=SimpleNamespace(state=tmp_path),
        agents={
            "first": Agent("first", ("acp",), priority=1),
            "second": Agent("second", ("acp",), model="missing", priority=2),
            "third": Agent("third", ("acp",), priority=3),
            "fourth": Agent("fourth", ("acp",), priority=4),
        },
        runner=SimpleNamespace(probe=probe),
        ledger=SimpleNamespace(
            update=lambda attempt_id, **fields: {
                "id": attempt_id,
                "status": "uncertain",
                **fields,
            }
        ),
        start=start,
    )
    result = Routing(service).start("project", "cn-1")
    assert starts == ["third"]
    assert result["attempt"]["status"] == "uncertain"
    assert result["fallback"]
    assert [item["reason"] for item in result["skipped"]] == [
        "ACPAuthRequired",
        "configured_model_unavailable",
    ]
