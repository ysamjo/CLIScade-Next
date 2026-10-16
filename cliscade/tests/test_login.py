import json
import sqlite3
import sys
import time

import pytest
from fastapi.testclient import TestClient

from cliscade_next.api import create_app
from cliscade_next.config import Settings
from cliscade_next.login import PROVIDERS, LoginService, login_challenge


def test_challenge_only_exposes_provider_urls_and_codes():
    output = "\x1b[31mhttps://auth.openai.com/codex/device\x1b[0m\nab3d-efG2H\n"
    output += (
        "access_token=secret https://evil.test/steal https://auth.openai.com.evil.test/"
    )
    result = login_challenge("codex", output)
    assert result == {
        "url": "https://auth.openai.com/codex/device",
        "user_code": "ab3d-efG2H",
    }
    assert login_challenge(
        "claude-code", "https://claude.ai/oauth/authorize?state=x"
    ) == {"url": "https://claude.ai/oauth/authorize?state=x", "user_code": None}


def test_native_login_code_completion_status_and_persistence(tmp_path, monkeypatch):
    script = tmp_path / "cli.py"
    script.write_text("""import pathlib,sys,json
p=pathlib.Path.home()/"signed-in"
if sys.argv[1]=="status":
 print(json.dumps({"loggedIn":p.exists()}));sys.exit(0)
print("https://claude.com/api/oauth/authorize?state=fixture",flush=True)
import time;time.sleep(.1);print("x"*40000,flush=True)
code=input()
if code=="one-time-code": p.write_text("account-login")
""")
    monkeypatch.setitem(
        PROVIDERS,
        "claude-code",
        {
            "login": (sys.executable, str(script), "login"),
            "status": (sys.executable, str(script), "status"),
            "mode": "code",
        },
    )
    service = LoginService(tmp_path)
    first = service.start("claude-code")
    for _ in range(100):
        state = service.current("claude-code")
        if state.get("url"):
            break
        time.sleep(0.02)
    assert state["state"] == "pending"
    assert service.start("claude-code")["id"] == first["id"]
    assert "one-time-code" not in json.dumps(state)
    service.submit("claude-code", first["id"], "one-time-code")
    for _ in range(100):
        if service.current("claude-code")["state"] == "completed":
            break
        time.sleep(0.02)
    assert service.status("claude-code")["connected"] is True
    assert LoginService(tmp_path).status("claude-code")["connected"] is True
    assert "account-login" not in json.dumps(service.current("claude-code"))
    service.close()


def test_api_login_requires_auth_rejects_unknown_and_no_arbitrary_commands(tmp_path):
    client = TestClient(
        create_app(Settings(tmp_path, tmp_path / "state", "http://localhost", "test"))
    )
    assert client.get("/cliscade/v1/agents/codex/login").status_code == 401
    client.headers["X-Session-API-Key"] = "test"
    assert client.post("/cliscade/v1/agents/sh/login", json={}).status_code == 400
    assert (
        client.post(
            "/cliscade/v1/agents/codex/login", json={"command": "echo unsafe"}
        ).status_code
        == 422
    )
    with pytest.raises(ValueError):
        LoginService(tmp_path).submit("codex", "unknown", "code")


def test_cancel_expires_only_owned_login_and_strips_inherited_keys(
    tmp_path, monkeypatch
):
    script = tmp_path / "wait.py"
    script.write_text("import time;time.sleep(60)")
    monkeypatch.setitem(
        PROVIDERS,
        "codex",
        {
            "login": (sys.executable, str(script)),
            "status": (sys.executable, "-c", "exit(1)"),
            "mode": "device",
        },
    )
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/wrong-account")
    service = LoginService(tmp_path)
    assert "OPENAI_API_KEY" not in service.environment()
    assert "CLAUDE_CONFIG_DIR" not in service.environment()
    first = service.start("codex")
    assert service.cancel("codex", first["id"], "expired")["state"] == "expired"
    assert service.jobs["codex"]["process"].poll() is not None
    second = service.start("codex")
    with pytest.raises(ValueError):
        service.cancel("codex", first["id"])
    assert service.current("codex")["id"] == second["id"]
    service.jobs["codex"]["expires_at"] = time.time() + 800
    assert service.current("codex")["state"] == "failed"
    assert service.jobs["codex"]["process"].poll() is not None
    service.close()


def test_account_login_takes_precedence_over_stored_provider_api_keys(
    tmp_path, monkeypatch
):
    from cliscade_next.agents import Agent, OpenHands

    monkeypatch.setenv("CLISCADE_LOGIN_HOME", str(tmp_path))
    (tmp_path / ".cliscade-accounts").mkdir()
    (tmp_path / ".cliscade-accounts/codex").touch()
    assert OpenHands(None).secrets(None, Agent("codex", ("codex-acp",))) == {}


def test_completed_codex_login_uses_official_versioned_secret_store(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from cliscade_next.agents import OpenHands

    (tmp_path / ".codex").mkdir()
    credential = json.dumps(
        {"auth_mode": "chatgpt", "tokens": {"refresh_token": "fixture-refresh"}}
    )
    (tmp_path / ".codex/auth.json").write_text(credential)
    client = Mock()
    monkeypatch.setattr(
        "cliscade_next.agents.RemoteWorkspace",
        lambda **kwargs: SimpleNamespace(client=client),
    )
    settings = Settings(
        tmp_path, tmp_path / "state", "http://agent-server:8000", "internal-test"
    )
    OpenHands(settings).save_account("codex", tmp_path)
    client.put.assert_called_once_with(
        "/api/settings/secrets", json={"name": "CODEX_AUTH_JSON", "value": credential}
    )
    client.close.assert_called_once()


def test_opencode_status_reads_oauth_store_without_starting_a_second_cli(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "cliscade_next.login.shutil.which", lambda *args, **kwargs: "/bin/opencode"
    )
    monkeypatch.setattr(
        "cliscade_next.login.subprocess.run",
        lambda *args, **kwargs: pytest.fail(
            "Status darf OpenCodes Login-Initialisierung nicht blockieren"
        ),
    )
    service = LoginService(tmp_path)
    assert service.status("opencode") == {"available": True, "connected": False}
    store = tmp_path / ".local/share/opencode/auth.json"
    store.parent.mkdir(parents=True)
    store.write_text(json.dumps({"openai": {"type": "api", "key": "not-an-account"}}))
    assert service.status("opencode")["connected"] is False
    store.write_text(json.dumps({"openai": {"type": "oauth", "refresh": "old-openai"}}))
    assert service.status("opencode")["connected"] is False
    with sqlite3.connect(store.with_name("opencode.db")) as db:
        db.executescript("""
            CREATE TABLE account (id TEXT, url TEXT, refresh_token TEXT);
            CREATE TABLE account_state (id INTEGER, active_account_id TEXT);
            INSERT INTO account VALUES
                ('own', 'https://opencode.ai/console', 'fixture-refresh');
            INSERT INTO account_state VALUES (1, 'missing');
        """)
        assert service.status("opencode")["connected"] is False
        db.execute("UPDATE account_state SET active_account_id = 'own'")
    assert service.status("opencode")["connected"] is True
    assert "fixture-refresh" not in json.dumps(service.status("opencode"))


def test_kiro_callback_only_reaches_native_listener_with_matching_state(
    tmp_path, monkeypatch
):
    from unittest.mock import Mock

    service = LoginService(tmp_path)
    job = {
        "challenge": {
            "url": (
                "https://app.kiro.dev/signin?redirect_uri=http%3A%2F%2Flocalhost%3A3128"
                "&state=native-state"
            )
        }
    }
    connection = Mock()
    connection.getresponse.return_value.status = 200
    factory = Mock(return_value=connection)
    monkeypatch.setattr("cliscade_next.login.http.client.HTTPConnection", factory)
    for value in (
        "http://evil.test:3128/?code=secret&state=native-state",
        "http://localhost:8000/?code=secret&state=native-state",
        "http://localhost:3128/?code=secret&state=another-login",
        "http://localhost:3128/?state=native-state",
    ):
        with pytest.raises(ValueError):
            service.callback(job, value)
    factory.assert_not_called()
    service.callback(job, "http://localhost:3128/?code=secret&state=native-state")
    factory.assert_called_once_with("127.0.0.1", 3128, timeout=15)
    connection.request.assert_called_once_with(
        "GET", "/?code=secret&state=native-state"
    )
    connection.close.assert_called_once()


def test_native_browser_capture_is_private_and_rejects_other_hosts(
    tmp_path, monkeypatch
):
    from cliscade_next.login import capture_browser

    target = tmp_path / "url"
    monkeypatch.setenv("CLISCADE_LOGIN_URL_FILE", str(target))
    monkeypatch.setattr(sys, "argv", ["browser", "https://evil.test/?secret=code"])
    with pytest.raises(SystemExit):
        capture_browser()
    assert not target.exists()
    monkeypatch.setattr(
        sys, "argv", ["browser", "https://app.kiro.dev/signin?state=test"]
    )
    capture_browser()
    assert target.stat().st_mode & 0o777 == 0o600
    assert target.read_text() == "https://app.kiro.dev/signin?state=test"


def test_kiro_native_portal_callback_completes_and_persists(tmp_path, monkeypatch):
    script = tmp_path / "kiro.py"
    script.write_text("""import os,pathlib,subprocess,sys,json
from http.server import BaseHTTPRequestHandler,HTTPServer
p=pathlib.Path.home()/"signed-in"
if sys.argv[1]=="status":
 print(json.dumps({"accountType":"social"}) if p.exists() else "");sys.exit(0)
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  p.write_text("connected")
  self.send_response(200);self.end_headers();self.wfile.write(b"ok")
 def log_message(self,*args): pass
server=HTTPServer(("127.0.0.1",0),Handler)
url="https://app.kiro.dev/signin?state=native-state&redirect_uri=http%3A%2F%2Flocalhost%3A"+str(server.server_port)
subprocess.run([os.environ["BROWSER"],url],check=True)
print("Opening browser",flush=True)
server.handle_request();server.server_close()
""")
    monkeypatch.setitem(
        PROVIDERS,
        "kiro",
        {
            "login": (sys.executable, str(script), "login"),
            "status": (sys.executable, str(script), "status"),
            "mode": "callback",
        },
    )
    service = LoginService(tmp_path)
    try:
        first = service.start("kiro")
        for _ in range(100):
            state = service.current("kiro")
            if state.get("url"):
                break
            time.sleep(0.02)
        from urllib.parse import parse_qs, urlsplit

        target = parse_qs(urlsplit(state["url"]).query)["redirect_uri"][0]
        service.submit(
            "kiro", first["id"], target + "/?code=one-time&state=native-state"
        )
        for _ in range(100):
            if service.current("kiro")["state"] == "completed":
                break
            time.sleep(0.02)
        assert service.current("kiro")["state"] == "completed"
        assert LoginService(tmp_path).status("kiro")["connected"]
        assert "one-time" not in json.dumps(service.current("kiro"))
    finally:
        service.close()
