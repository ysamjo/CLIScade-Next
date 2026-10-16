"""Opt-in NAS-E2E. Im CLIScade-Container ausführen, nur cliscade-smoke verändern."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from cliscade_next.agents import Agent
from cliscade_next.config import Settings
from cliscade_next.orchestrator import Orchestrator

key = os.environ["CLISCADE_API_KEY"]
settings = Settings(
    Path("/projects"), Path("/data/smoke-ledger"), "http://agent-server:8000", key
)
agents = {
    name: Agent(
        name,
        ("/usr/local/bin/python", "/projects/.cliscade-verification/acp_fixture.py"),
    )
    for name in ("fixture-a", "fixture-b")
}
service = Orchestrator(settings, agents=agents)
client = httpx.Client(
    base_url="http://canvas:8000", headers={"X-Session-API-Key": key}, timeout=180
)
proof_path = Path("/data/deployment-proof.json")


def call(method, path, body=None):
    response = client.request(method, path, json=body)
    if response.is_error:
        print(
            {
                "path": path,
                "status": response.status_code,
                "detail": response.text[:2000],
            }
        )
    response.raise_for_status()
    return response.json()


def complete(attempt):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        attempt = service.refresh(attempt["id"])
        if attempt["status"] in ("completed", "failed", "needs_review", "uncertain"):
            break
        time.sleep(1)
    assert attempt["status"] == "completed", attempt["error"]
    assert attempt["checkpoint"]["verified_checks"]
    return attempt


deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    try:
        if all(
            client.get(path).status_code == 200
            for path in ("/ready", "/api/automation/health", "/cliscade/v1/projects")
        ):
            break
    except httpx.HTTPError:
        pass
    time.sleep(1)
else:
    raise RuntimeError("Compose-Dienste wurden nicht rechtzeitig bereit")


if sys.argv[1] == "prepare":
    project = settings.projects / "cliscade-smoke"
    project.mkdir(exist_ok=True)
    if not (project / ".git").exists():
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(project),
                "-c",
                "user.name=CLIScade Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--allow-empty",
                "-qm",
                "Testprojekt initialisieren",
            ],
            check=True,
        )
    base = "/cliscade/v1/projects/cliscade-smoke"
    call("POST", base + "/initialize", {})
    task = call(
        "POST",
        base + "/tasks",
        {
            "title": "Docker: ACP und Neustart prüfen",
            "acceptance": "Prüfbeleg und Handoff bleiben erhalten",
        },
    )
    first = complete(service.start("cliscade-smoke", task["id"], "fixture-a"))
    receipt = call("POST", base + "/backups", {})
    assert receipt["restore_verified"]
    cron_task = call(
        "POST",
        base + "/tasks",
        {"title": "Geschlossene Aufgabe im nativen Scheduler überspringen"},
    )
    call("PATCH", base + "/tasks/" + cron_task["id"], {"status": "closed"})
    automation = call(
        "POST",
        base + "/tasks/" + cron_task["id"] + "/schedule",
        {"cron": "0 0 1 1 *", "timezone": "Europe/Berlin", "agent_id": "auto"},
    )
    native = "/api/automation/v1/" + automation["id"]
    run = call("POST", native + "/dispatch")
    proof = {
        "task_id": task["id"],
        "attempt_id": first["id"],
        "session_id": first["session_id"],
        "automation_id": automation["id"],
        "automation_run": run["id"],
        "backup": receipt,
    }
    proof_path.write_text(json.dumps(proof))
    print({"phase": "prepared", **proof})
else:
    proof = json.loads(proof_path.read_text())
    first = service.ledger.get(proof["attempt_id"])
    session = service.runner.attach(
        agents["fixture-a"], Path(first["workspace"]), first["session_id"]
    )
    try:
        assert session.state()["status"] == "finished"
    finally:
        session.close()
    second = complete(
        service.start(
            "cliscade-smoke", proof["task_id"], "fixture-b", source_id=first["id"]
        )
    )
    assert second["workspace"] == first["workspace"]
    assert second["checkpoint"]["verified_checks"]
    runs = call("GET", "/api/automation/v1/" + proof["automation_id"] + "/runs")
    selected = next(run for run in runs["runs"] if run["id"] == proof["automation_run"])
    call("PATCH", "/api/automation/v1/" + proof["automation_id"], {"state": "INACTIVE"})
    print(
        {
            "phase": "recovered",
            "first_session": first["session_id"],
            "handoff_session": second["session_id"],
            "automation_status": selected["status"],
            "task_persisted": call(
                "GET", "/cliscade/v1/projects/cliscade-smoke/tasks/" + proof["task_id"]
            )["id"],
        }
    )
    assert selected["status"] == "COMPLETED", selected
