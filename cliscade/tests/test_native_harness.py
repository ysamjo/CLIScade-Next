from types import SimpleNamespace

import httpx
import pytest

from cliscade_next.agents import Agent, OpenHands, registry


def test_native_harness_uses_omniroute_profile_and_keeps_secrets_off_discovery(
    monkeypatch,
):
    from openhands.sdk.agent import ACPAgent

    calls = []
    client_type = httpx.Client

    def handle(request):
        calls.append(request)
        if request.url.path == "/api/profiles/OmniRoute":
            assert request.headers["X-Expose-Secrets"] == "plaintext"
            return httpx.Response(
                200,
                json={
                    "config": {
                        "model": "openai/c1",
                        "base_url": "http://gateway/v1",
                        "api_key": "private-test-key",
                        "native_tool_calling": True,
                    }
                },
            )
        assert request.url == "http://gateway/v1/models"
        assert request.headers["Authorization"] == "Bearer private-test-key"
        return httpx.Response(200, json={"data": [{"id": "c1"}, {"id": "ant"}]})

    monkeypatch.setattr(
        "cliscade_next.agents.httpx.Client",
        lambda **kwargs: client_type(transport=httpx.MockTransport(handle)),
    )
    runner = OpenHands(SimpleNamespace())
    with client_type(
        base_url="http://server", transport=httpx.MockTransport(handle)
    ) as client:
        workspace = SimpleNamespace(client=client, working_dir="/projects/run-worktree")
        agent = registry()["openhands"]
        assert agent.command == ()
        discovery = runner.native_discovery(workspace, agent)
        assert discovery["available_models"] == [
            {"model_id": "openai/ant"},
            {"model_id": "openai/c1"},
        ]
        assert "private-test-key" not in str(discovery)
        native = runner.native_agent(
            workspace, Agent("openhands", (), model="openai/ant")
        )
        assert not isinstance(native, ACPAgent)
        assert native.llm.model == "openai/ant"
        assert native.llm.base_url == "http://gateway/v1"
        assert native.llm.api_key.get_secret_value() == "private-test-key"
        assert "/projects/run-worktree" in native.agent_context.system_message_suffix
        assert {"terminal", "file_editor"}.issubset(
            {tool.name for tool in native.tools}
        )


def test_missing_native_profile_is_a_sanitized_failure():
    with httpx.Client(
        base_url="http://server",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(404, text="private-detail")
        ),
    ) as client:
        with pytest.raises(RuntimeError, match="OmniRoute") as error:
            OpenHands(SimpleNamespace()).native_profile(SimpleNamespace(client=client))
        assert "private-detail" not in str(error.value)
