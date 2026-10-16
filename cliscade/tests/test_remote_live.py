"""Opt-in: Anbieter-Inferenz, Secret-Lookup und echter Server-Neustart."""

import os
import subprocess
import time
from pathlib import Path

import pytest
from openhands.sdk.workspace import RemoteWorkspace

from cliscade_next.agents import registry
from cliscade_next.beads import Beads
from cliscade_next.config import Settings
from cliscade_next.orchestrator import Orchestrator
from cliscade_next.routing import Routing


@pytest.mark.skipif(
    os.environ.get("CLISCADE_REMOTE_LIVE") != "1",
    reason="Remote-Anbieterprüfung nicht angefordert",
)
def test_claude_remote_secret_lookup_and_server_restart(tmp_path):
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
    subprocess.run(
        [
            "bd",
            "init",
            "--non-interactive",
            "--prefix",
            "cn",
            "--skip-agents",
            "--skip-hooks",
        ],
        cwd=project,
        check=True,
        capture_output=True,
        timeout=60,
    )
    settings = Settings(
        tmp_path,
        tmp_path / "state",
        os.environ["AGENT_SERVER_URL"],
        os.environ["SESSION_API_KEY"],
    )
    workspace = RemoteWorkspace(
        host=settings.agent_server, working_dir=str(project), api_key=settings.api_key
    )
    try:
        for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"):
            response = workspace.client.put(
                "/api/settings/secrets",
                json={
                    "name": name,
                    "value": os.environ[name],
                },
            )
            response.raise_for_status()
    finally:
        workspace.client.close()
    task = Beads(project).create(
        "Schreibe acp-proof.txt mit genau ACP_REMOTE_OK",
        acceptance="Datei existiert mit dem angeforderten Inhalt",
    )
    agents = {"claude-code": registry()["claude-code"]}
    service = Orchestrator(settings, agents=agents)
    result = Routing(service).start("project", task["id"])
    attempt = result["attempt"]
    assert attempt and attempt["status"] == "running"
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        attempt = service.refresh(attempt["id"])
        if attempt["status"] in ("completed", "failed", "cancelled", "uncertain"):
            break
        time.sleep(1)
    assert attempt["status"] == "completed", attempt["status"]
    assert (
        Path(attempt["workspace"], "acp-proof.txt").read_text().strip()
        == "ACP_REMOTE_OK"
    )
    control = os.environ.get("CLISCADE_SERVER_CONTROL")
    run = os.environ.get("CLISCADE_RESTART_RUN")
    if control and run:
        subprocess.run(
            [control, "restart", "--run", run],
            check=True,
            capture_output=True,
            timeout=90,
        )
        attached = service.runner.attach(
            agents["claude-code"], Path(attempt["workspace"]), attempt["session_id"]
        )
        try:
            assert attached.state()["status"] == "finished"
        finally:
            attached.close()
        restored = Orchestrator(settings, agents=agents).ledger.get(attempt["id"])
        assert restored["checkpoint"] == attempt["checkpoint"]
