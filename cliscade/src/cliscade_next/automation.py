"""Native OpenHands-Automationen mit unveränderlichem CLIScade-Dispatch-Bundle."""

import gzip
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

import httpx


def bundle(config):
    output = io.BytesIO()
    files = {
        "cliscade-dispatch.py": Path(__file__).with_name("scheduled.py").read_bytes(),
        "cliscade.json": json.dumps(config).encode(),
        "cliscade-dispatch.py.lock": Path(__file__)
        .with_name("scheduled.py.lock")
        .read_bytes(),
    }
    with tarfile.open(fileobj=output, mode="w") as tar:
        for name, value in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(value)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(value))
    return gzip.compress(output.getvalue(), mtime=0)


class Automation:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport
        self.url = os.environ.get(
            "CLISCADE_AUTOMATION_URL", "http://127.0.0.1:18001/api/automation"
        )
        self.internal_url = os.environ.get(
            "CLISCADE_INTERNAL_URL", "http://cliscade:18002"
        )

    def create(self, project, task_id, agent_id, cron, timezone):
        config = {
            "project": project,
            "task_id": task_id,
            "agent_id": agent_id,
            "url": self.internal_url,
        }
        archive = bundle(config)
        identity = hashlib.sha256(
            archive + json.dumps([cron, timezone]).encode()
        ).hexdigest()
        with httpx.Client(
            base_url=self.url.rstrip("/") + "/",
            transport=self.transport,
            headers={"X-Session-API-Key": self.settings.api_key},
            timeout=90,
        ) as client:
            upload = client.post(
                "v1/uploads",
                params={"name": f"cliscade-{task_id}.tar.gz"},
                headers={"Content-Type": "application/gzip"},
                content=archive,
            )
            upload.raise_for_status()
            tarball_path = upload.json().get("tarball_path")
            if not tarball_path:
                raise RuntimeError(
                    "OpenHands-Automation hat das Bundle nicht gespeichert"
                )
            response = client.post(
                "v1",
                json={
                    "name": f"CLIScade: {project} / {task_id}",
                    "trigger": {"type": "cron", "schedule": cron, "timezone": timezone},
                    "tarball_path": tarball_path,
                    "entrypoint": (
                        "uv run --script --locked cliscade-dispatch.py cliscade.json"
                    ),
                    "state": "ACTIVE",
                    "timeout": 1800,
                    "template": {
                        "id": "cliscade-" + identity,
                        "version": "1",
                        "config": config,
                    },
                },
            )
            response.raise_for_status()
            return response.json()
