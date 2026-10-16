# /// script
# requires-python = ">=3.13"
# dependencies = ["httpx==0.28.1", "openhands-sdk==1.55.1"]
# ///
"""OpenHands-Automationseinstieg: Aufgaben-API aufrufen, keinen Agenten starten."""

import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from openhands.sdk.workspace import RemoteWorkspace


def dispatch(config, client, run_id, on_start=None, poll_seconds=5, timeout=1500):
    project = quote(config["project"], safe="")
    task_id = quote(config["task_id"], safe="")
    response = client.get(f"/cliscade/v1/projects/{project}/tasks/{task_id}")
    response.raise_for_status()
    if response.json()["status"] == "closed":
        return {"status": "skipped", "reason": "task_closed"}
    response = client.post(
        f"/cliscade/v1/projects/{project}/attempts",
        json={
            "task_id": config["task_id"],
            "agent_id": config["agent_id"],
            "request_key": "automation:" + run_id,
        },
    )
    response.raise_for_status()
    attempt = response.json()
    if on_start:
        on_start(attempt)
    deadline = time.monotonic() + timeout
    terminal = {
        "completed",
        "failed",
        "cancelled",
        "uncertain",
        "needs_review",
        "preparation_failed",
    }
    while attempt["status"] not in terminal and time.monotonic() < deadline:
        time.sleep(poll_seconds)
        response = client.get(f"/cliscade/v1/attempts/{attempt['id']}")
        response.raise_for_status()
        attempt = response.json()
    if attempt["status"] != "completed":
        raise RuntimeError(
            f"Ausführung {attempt['id']} benötigt Prüfung: {attempt['status']}"
        )
    return attempt


def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    key = os.environ["SESSION_API_KEY"]
    workspace = RemoteWorkspace(
        host=os.environ["AGENT_SERVER_URL"],
        api_key=key,
        working_dir=os.environ["WORKSPACE_BASE"],
    )
    try:
        with (
            workspace,
            httpx.Client(
                base_url=config["url"], timeout=600, headers={"X-Session-API-Key": key}
            ) as client,
        ):

            def started(attempt):
                if attempt.get("session_id"):
                    workspace.register_conversation(attempt["session_id"])

            attempt = dispatch(
                config, client, os.environ["AUTOMATION_RUN_ID"], on_start=started
            )
            print(
                json.dumps(
                    {"attempt_id": attempt.get("id"), "status": attempt["status"]}
                )
            )
    finally:
        workspace.client.close()


if __name__ == "__main__":
    main()
