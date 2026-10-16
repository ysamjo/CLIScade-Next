"""Opt-in: echtes Beads + Agent Server + zwei kontrollierte ACP-Sessions."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from cliscade_next.agents import Agent
from cliscade_next.beads import Beads
from cliscade_next.config import Settings
from cliscade_next.consensus import Consensus
from cliscade_next.orchestrator import Orchestrator


@pytest.mark.skipif(not os.environ.get("AGENT_SERVER_URL"), reason="Agent Server fehlt")
def test_real_beads_remote_sdk_handoff_and_persisted_attempt(tmp_path):
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
    beads = Beads(project)
    task = beads.create("ACP-Übergabe", acceptance="Prüfbeleg erhalten")
    settings = Settings(
        tmp_path,
        tmp_path / "state",
        os.environ["AGENT_SERVER_URL"],
        os.environ["SESSION_API_KEY"],
    )
    command = (sys.executable, str(Path(__file__).with_name("acp_fixture.py")))
    agents = {name: Agent(name, command) for name in ("fixture-a", "fixture-b")}
    service = Orchestrator(settings, agents=agents)
    first = service.start("project", task["id"], "fixture-a")
    assert first["status"] == "running", first
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        first = service.refresh(first["id"])
        if first["status"] == "completed":
            break
        time.sleep(1)
    assert first["status"] == "completed"
    assert first["checkpoint"]["verified_checks"][0]["exit_code"] == 0
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
            agents["fixture-a"], Path(first["workspace"]), first["session_id"]
        )
        try:
            assert attached.state()["status"] == "finished"
        finally:
            attached.close()
    service = Orchestrator(settings, agents=agents)
    second = service.start("project", task["id"], "fixture-b", source_id=first["id"])
    assert second["status"] == "running", second
    assert second["session_id"] != first["session_id"]
    assert second["workspace"] == first["workspace"]
    assert second["checkpoint"]["source_attempt"] == first["id"]
    assert second["checkpoint"]["verified_checks"]
    assert Beads(project).show(task["id"])["assignee"] == "fixture-b"

    consensus_task = beads.create("Zwei unabhängige Lösungen")
    consensus = Consensus(service)
    group = consensus.start("project", consensus_task["id"], ["fixture-a", "fixture-b"])
    assert len({attempt["workspace"] for attempt in group["attempts"]}) == 2
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        group = consensus.get(group["id"])
        if group["status"] == "completed":
            break
        time.sleep(1)
    assert group["status"] == "completed", group
    assert group["result"]["correctness_verified"] is False
    assert len(group["result"]["results"]) == 2
    assert all(result["checks"] for result in group["result"]["results"])
