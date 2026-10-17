import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cliscade_next import acp_login
from cliscade_next.agents import registry


def transport(monkeypatch, connected=False, method="external"):
    connection = SimpleNamespace(
        initialize=AsyncMock(
            return_value=SimpleNamespace(
                auth_methods=[SimpleNamespace(id=method)],
            )
        ),
        ext_method=AsyncMock(
            return_value={
                "userInfo": {
                    "userId": "fixture-account" if connected else "",
                    "accessToken": "never-export",
                }
            }
        ),
        authenticate=AsyncMock(),
    )
    launches = []

    @asynccontextmanager
    async def spawn(client, *command, **options):
        launches.append((command, options))
        yield connection, None

    monkeypatch.setattr(acp_login, "spawn_agent_process", spawn)
    monkeypatch.setattr(
        acp_login,
        "ACP_ACCOUNT_COMMANDS",
        {
            "codebuddy": ("native-codebuddy", "--acp"),
            "antigravity": ("native-antigravity",),
        },
    )
    return connection, launches


def test_codebuddy_keeps_existing_account_without_forcing_reauthentication(monkeypatch):
    connection, launches = transport(monkeypatch, connected=True)
    assert asyncio.run(acp_login.account("codebuddy", "login")) is True
    connection.authenticate.assert_not_awaited()
    assert len(launches) == 1
    assert launches[0][1]["cwd"]


def test_codebuddy_login_uses_native_international_method_and_status_never_logs_in(
    monkeypatch,
):
    connection, _ = transport(monkeypatch)
    assert asyncio.run(acp_login.account("codebuddy", "status")) is False
    connection.authenticate.assert_not_awaited()
    assert asyncio.run(acp_login.account("codebuddy", "login")) is True
    connection.authenticate.assert_awaited_once_with(method_id="external")


def test_unadvertised_auth_is_rejected(monkeypatch):
    connection, _ = transport(monkeypatch, method="other")
    assert asyncio.run(acp_login.account("codebuddy", "login")) is False
    connection.authenticate.assert_not_awaited()


def test_antigravity_uses_google_and_status_does_not_open_a_browser(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    connection, launches = transport(monkeypatch, method="oauth-personal")
    assert asyncio.run(acp_login.account("antigravity", "status")) is False
    assert not launches
    assert asyncio.run(acp_login.account("antigravity", "login")) is True
    marker = tmp_path / ".cliscade-accounts" / "antigravity"
    marker.parent.mkdir()
    marker.touch()
    assert asyncio.run(acp_login.account("antigravity", "status")) is True
    assert launches[-1][1]["env"]["BROWSER"] == "/usr/bin/false"
    assert connection.authenticate.await_count == 2


def test_priority_agents_can_be_configured_without_replacing_commands(
    tmp_path, monkeypatch
):
    import json

    agents = registry()
    assert [agent.id for agent in sorted(agents.values(), key=lambda a: a.priority)][
        :2
    ] == [
        "antigravity",
        "codebuddy",
    ]
    path = tmp_path / "routing.json"
    path.write_text(
        json.dumps(
            {
                "antigravity": {"enabled": False},
                "codebuddy": {"model": "reported-model"},
            }
        )
    )
    monkeypatch.setenv("CLISCADE_AGENT_CONFIG", str(path))
    configured = registry()
    assert configured["antigravity"].enabled is False
    assert configured["codebuddy"].model == "reported-model"
    assert configured["codebuddy"].priority == agents["codebuddy"].priority
    assert configured["codebuddy"].command == agents["codebuddy"].command


def test_account_helper_starts_without_loading_the_execution_sdk(tmp_path):
    import os
    import subprocess
    import sys

    script = """
import asyncio
import importlib.abc
import sys
class NoExecutionSDK(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "openhands" or fullname.startswith("openhands."):
            raise AssertionError("Auth darf das Ausführungs-SDK nicht laden")
sys.meta_path.insert(0, NoExecutionSDK())
from cliscade_next.acp_login import account
assert asyncio.run(account("antigravity", "status")) is False
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
