import importlib.util
import io
import json
from pathlib import Path

import pytest
from openhands.sdk.settings.model import OpenHandsAgentSettings

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "configure_omniroute", ROOT / "deploy/configure-omniroute.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("activate", [False, True])
def test_profile_uses_gateway_and_only_explicit_activation_changes_harness(
    monkeypatch, activate
):
    requests = []

    def reply(request, timeout):
        requests.append(request)
        return io.BytesIO(json.dumps({"data": [{"id": "coding"}]}).encode())

    monkeypatch.setattr(module, "urlopen", reply)
    result = module.configure(
        "http://omniroute:20128/v1/",
        "http://agent-server:8000/",
        "coding",
        "gateway-secret",
        "session-secret",
        activate,
    )
    assert requests[0].full_url == "http://omniroute:20128/v1/models"
    assert requests[0].get_header("Authorization") == "Bearer gateway-secret"
    profile = json.loads(requests[1].data)
    assert profile["llm"]["base_url"] == "http://omniroute:20128/v1"
    assert profile["llm"]["model"] == "openai/coding"
    assert profile["llm"]["api_key"] == "gateway-secret"
    assert requests[1].get_header("X-session-api-key") == "session-secret"
    assert result["activated"] == activate
    if activate:
        payload = json.loads(requests[2].data)
        settings = OpenHandsAgentSettings.model_validate(payload["agent_settings_diff"])
        assert settings.agent_kind == "openhands"
        assert settings.llm.native_tool_calling is True
        assert payload["active_agent_profile_id"] is None
    else:
        assert len(requests) == 2


def test_missing_model_does_not_modify_openhands(monkeypatch):
    calls = []

    def reply(*args, **kwargs):
        calls.append(args)
        return io.BytesIO(b'{"data": []}')

    monkeypatch.setattr(module, "urlopen", reply)
    with pytest.raises(ValueError, match="nicht angeboten"):
        module.configure(
            "http://gateway/v1", "http://server", "missing", "key", "session", True
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "gateway,key",
    [
        ("http://user:password@host/v1", "key"),
        ("http://host/v1?key=secret", "key"),
        ("http://host/v1", ""),
    ],
)
def test_invalid_configuration_never_sends_credentials(monkeypatch, gateway, key):
    def unexpected(*args, **kwargs):
        pytest.fail("Keine Anfrage mit ungültiger Konfiguration senden")

    monkeypatch.setattr(module, "urlopen", unexpected)
    with pytest.raises(ValueError):
        module.configure(gateway, "http://server", "coding", key, "session", True)
