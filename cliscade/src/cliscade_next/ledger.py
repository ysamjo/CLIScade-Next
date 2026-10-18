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
                    route_trace TEXT, base_revision TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ'))
                );
                CREATE UNIQUE INDEX IF NOT EXISTS active_workspace
                ON attempts(workspace)
                WHERE status IN ('preparing','submitted','running','cancelling');
                CREATE TABLE IF NOT EXISTS requests (
                    key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    attempt_id TEXT NOT NULL REFERENCES attempts(id)
                );
                CREATE TABLE IF NOT EXISTS consensus (
                    id TEXT PRIMARY KEY, project TEXT NOT NULL, task_id TEXT NOT NULL,
                    revision TEXT NOT NULL, expected INTEGER NOT NULL,
                    attempts TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'preparing', result TEXT
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(attempts)")}
            if "route_trace" not in columns:
                db.execute("ALTER TABLE attempts ADD COLUMN route_trace TEXT")
            if "base_revision" not in columns:
                db.execute("ALTER TABLE attempts ADD COLUMN base_revision TEXT")
            if "model" not in columns:
                db.execute("ALTER TABLE attempts ADD COLUMN model TEXT")

    def verified_agents(self):
        """Agenten mit mindestens einem abgeschlossenen Lauf, der Spuren hinterließ.

        `completed` allein genügt nicht: ein Lauf kann fertig sein und trotzdem am
        falschen Ort gearbeitet haben. Als Beleg zählt entweder ein Kommando mit
        Exit-Code (`verified_checks`, so arbeitet der native OpenHands-Harness)
        oder eine nachweisbare Änderung im Arbeitsbaum (`git.status`). ACP-Agenten
        führen Werkzeuge über ihr eigenes Protokoll aus; ihre Kommandos landen nicht
        in `verified_checks`. Ohne den Git-Zweig wäre kein ACP-Lauf je belegt,
        obwohl er Dateien geändert hat.
        """
        with self.connect() as db:
            rows = db.execute(
                "SELECT agent, model, checkpoint FROM attempts "
                "WHERE status='completed' AND error IS NULL AND checkpoint IS NOT NULL"
            ).fetchall()
        result = {}
        for row in rows:
            try:
                checkpoint = json.loads(row["checkpoint"])
            except (ValueError, AttributeError):
                continue
            checks = checkpoint.get("verified_checks") or []
            changed = ((checkpoint.get("git") or {}).get("status") or "").strip()
            if not checks and not changed:
                continue
            entry = result.setdefault(row["agent"], {"runs": 0, "models": []})
            entry["runs"] += 1
            if row["model"] and row["model"] not in entry["models"]:
                entry["models"].append(row["model"])
        return result

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(
        self,
        project,
        task_id,
        agent,
        workspace,
        source_id=None,
        request_key=None,
        request_fingerprint=None,
        base_revision=None,
        model=None,
    ):
        attempt_id = str(uuid4())
        with self.connect() as db:
            db.execute(
                "INSERT INTO attempts (id,project,task_id,agent,workspace,status,"
                "source_id,base_revision,model) VALUES (?,?,?,?,?,'preparing',?,?,?)",
                (
                    attempt_id,
                    project,
                    task_id,
                    agent,
                    str(workspace),
                    source_id,
                    base_revision,
                    model,
                ),
            )
            if request_key:
                db.execute(
                    "INSERT INTO requests VALUES (?,?,?)",
                    (request_key, request_fingerprint, attempt_id),
                )
        return self.get(attempt_id)

    def request(self, key, fingerprint):
        with self.connect() as db:
            row = db.execute("SELECT * FROM requests WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        if row["fingerprint"] != fingerprint:
            raise ValueError("Request-ID wurde bereits für andere Parameter verwendet")
        return self.get(row["attempt_id"])

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
        if item["route_trace"]:
            item["route_trace"] = json.loads(item["route_trace"])
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
            "route_trace",
        }
        if not fields or fields.keys() - allowed:
            raise ValueError("Ungültige Ausführungsänderung")
        if "checkpoint" in fields:
            fields["checkpoint"] = json.dumps(fields["checkpoint"], ensure_ascii=False)
        if "route_trace" in fields:
            fields["route_trace"] = json.dumps(fields["route_trace"])
        columns = ",".join(f"{key}=?" for key in fields)
        with self.connect() as db:
            db.execute(
                f"UPDATE attempts SET {columns} WHERE id=?",
                [*fields.values(), attempt_id],
            )
        return self.get(attempt_id)
