"""Beads bleibt die einzige lesbare und schreibbare Aufgabenquelle."""

import json
import os
import re
import subprocess
from pathlib import Path

from filelock import FileLock


class Beads:
    @classmethod
    def initialize(cls, project):
        directory = project / ".beads"
        if directory.exists() or directory.is_symlink():
            cls(project)
            return {"ready": True}
        result = subprocess.run(
            [
                "bd",
                "init",
                "--non-interactive",
                "--prefix",
                "cn",
                "--skip-agents",
                "--skip-hooks",
                "--stealth",
            ],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode:
            raise RuntimeError("Beads-Einrichtung fehlgeschlagen; bd doctor prüfen")
        return {"ready": True}

    @staticmethod
    def validate_id(task_id):
        if not isinstance(task_id, str) or not re.fullmatch(
            r"[a-zA-Z][a-zA-Z0-9_.-]{1,150}", task_id
        ):
            raise ValueError("Ungültige Beads-ID")

    def __init__(self, project: Path):
        self.project = project.resolve()
        directory = self.project / ".beads"
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("Beads ist im Projekt nicht eingerichtet")
        self.directory = directory

    def call(self, *args: str, readonly=False, json_output=True):
        command = ["bd", *args, "--sandbox"]
        if readonly:
            command.append("--readonly")
        if json_output:
            command.append("--json")
        env = {**os.environ, "BEADS_DIR": str(self.directory)}
        with FileLock(str(self.directory / "cliscade.lock"), timeout=30):
            result = subprocess.run(
                command,
                cwd=self.project,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        if result.returncode:
            raise RuntimeError("Beads-Zugriff fehlgeschlagen; bd doctor prüfen")
        return json.loads(result.stdout) if json_output else result.stdout

    def tasks(self):
        return self.call("list", "--all", "--limit", "0", readonly=True)

    def show(self, task_id):
        self.validate_id(task_id)
        result = self.call("show", task_id, readonly=True)
        task = result[0] if isinstance(result, list) and result else result
        if not isinstance(task, dict) or task.get("id") != task_id:
            raise ValueError("Beads-Aufgabe nicht gefunden")
        return task

    def create(self, title, description="", acceptance="", priority=2, parent=None):
        args = [
            "create",
            "--title",
            title,
            "--description",
            description,
            "--acceptance",
            acceptance,
            "--priority",
            str(priority),
        ]
        if parent:
            self.validate_id(parent)
            args.extend(["--parent", parent])
        return self.call(*args)

    def update(self, task_id, **fields):
        self.validate_id(task_id)
        allowed = {
            "title",
            "description",
            "acceptance",
            "priority",
            "assignee",
            "status",
        }
        if not fields or fields.keys() - allowed:
            raise ValueError("Ungültige Aufgabenänderung")
        args = ["update", task_id]
        for key, value in fields.items():
            args.extend(["--" + key, str(value)])
        return self.call(*args)

    def dependency(self, task_id, depends_on):
        self.validate_id(task_id)
        self.validate_id(depends_on)
        return self.call("dep", "add", task_id, depends_on)

    def assign(self, task_id, agent_id, previous=None):
        self.validate_id(task_id)
        args = ["update", task_id, "--assignee", agent_id, "--status", "in_progress"]
        if previous:
            args.extend(["--if-assignee", previous, "--if-status", "in_progress"])
        return self.call(*args)

    def context(self):
        return {
            "workflow": self.call(
                "prime", "--full", "--no-memories", readonly=True, json_output=False
            ),
            "memories": self.call("memories", readonly=True),
        }

    def ensure_startable(self, task_id):
        task = self.show(task_id)
        if task["status"] == "open":
            ready = self.call("ready", "--limit", "0", readonly=True)
            if not any(item["id"] == task_id for item in ready):
                raise ValueError(
                    "Beads-Aufgabe ist nicht bereit; Abhängigkeiten prüfen"
                )
        elif task["status"] == "in_progress":
            blocked = self.call("blocked", readonly=True)
            if any(item["id"] == task_id for item in blocked):
                raise ValueError("Beads-Aufgabe hat offene Blocker")
        else:
            raise ValueError("Beads-Aufgabe ist geschlossen oder blockiert")
        return task
