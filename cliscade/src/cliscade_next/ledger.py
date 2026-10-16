"""Dauerhafte Ausführungszuordnung ohne zweite Aufgaben-Datenbank."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


class Ledger:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "attempts.sqlite"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY, project TEXT NOT NULL,
                    task_id TEXT NOT NULL, agent TEXT NOT NULL,
                    workspace TEXT NOT NULL, status TEXT NOT NULL,
                    session_id TEXT, prompt_sent INTEGER NOT NULL DEFAULT 0,
                    source_id TEXT, checkpoint TEXT, error TEXT, terminal_seen REAL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ'))
                );
                CREATE UNIQUE INDEX IF NOT EXISTS active_workspace
                ON attempts(workspace)
                WHERE status IN ('preparing','submitted','running','cancelling');
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, project, task_id, agent, workspace, source_id=None):
        attempt_id = str(uuid4())
        with self.connect() as db:
            db.execute(
                "INSERT INTO attempts (id,project,task_id,agent,workspace,status,"
                "source_id) VALUES (?,?,?,?,?,'preparing',?)",
                (attempt_id, project, task_id, agent, str(workspace), source_id),
            )
        return self.get(attempt_id)

    def get(self, attempt_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM attempts WHERE id=?", (attempt_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Ausführung nicht gefunden")
        item = dict(row)
        if item["checkpoint"]:
            item["checkpoint"] = json.loads(item["checkpoint"])
        return item

    def list(self, project, task_id=None):
        sql = "SELECT id FROM attempts WHERE project=?"
        args = [project]
        if task_id:
            sql += " AND task_id=?"
            args.append(task_id)
        with self.connect() as db:
            rows = db.execute(sql + " ORDER BY created_at,id", args).fetchall()
        return [self.get(row["id"]) for row in rows]

    def update(self, attempt_id, **fields):
        allowed = {
            "status",
            "session_id",
            "prompt_sent",
            "checkpoint",
            "error",
            "terminal_seen",
        }
        if not fields or fields.keys() - allowed:
            raise ValueError("Ungültige Ausführungsänderung")
        if "checkpoint" in fields:
            fields["checkpoint"] = json.dumps(fields["checkpoint"], ensure_ascii=False)
        columns = ",".join(f"{key}=?" for key in fields)
        with self.connect() as db:
            db.execute(
                f"UPDATE attempts SET {columns} WHERE id=?",
                [*fields.values(), attempt_id],
            )
        return self.get(attempt_id)
