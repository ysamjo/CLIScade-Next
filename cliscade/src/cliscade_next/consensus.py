"""Unabhängige ACP-Versuche vergleichen, ohne Ergebnisse automatisch zu mergen."""

import hashlib
import json
from uuid import uuid4

from filelock import FileLock

from cliscade_next.context import git


class Consensus:
    def __init__(self, service):
        self.service = service

    def start(self, project, task_id, agents):
        if not 2 <= len(set(agents)) == len(agents) <= 4:
            raise ValueError("Konsens benötigt zwei bis vier verschiedene ACP-Agenten")
        if any(
            agent not in self.service.agents or not self.service.agents[agent].enabled
            for agent in agents
        ):
            raise ValueError("ACP-Agent ist nicht freigegeben")
        directory = self.service.settings.project(project)
        ledger = self.service.ledger
        group_id = str(uuid4())
        with FileLock(str(self.service.settings.state / "consensus.lock"), timeout=30):
            with FileLock(
                str(self.service.settings.state / "dispatch.lock"), timeout=30
            ):
                self._reserve(project, task_id, group_id, agents, directory)
            beads = self.service.beads_factory(directory)
            revision = git(directory, "rev-parse", "HEAD").strip()
            baseline = {
                "task": beads.show(task_id),
                "project_knowledge": beads.context(),
            }
            attempts = []
            try:
                beads.assign(task_id, "consensus-" + group_id)
                for agent in agents:
                    if git(directory, "rev-parse", "HEAD").strip() != revision:
                        raise ValueError(
                            "Git-Revision hat sich während des Konsensstarts geändert"
                        )
                    attempt = self.service.start(
                        project,
                        task_id,
                        agent,
                        allow_parallel=True,
                        assign=False,
                        consensus_id=group_id,
                        initial_context=baseline,
                    )
                    attempts.append(attempt["id"])
                    with ledger.connect() as db:
                        db.execute(
                            "UPDATE consensus SET attempts=? WHERE id=?",
                            (json.dumps(attempts), group_id),
                        )
                    if attempt["status"] != "running":
                        break
            except Exception:
                with ledger.connect() as db:
                    db.execute(
                        "UPDATE consensus SET status='interrupted' WHERE id=?",
                        (group_id,),
                    )
                raise
            with ledger.connect() as db:
                db.execute(
                    "UPDATE consensus SET status='running' WHERE id=?", (group_id,)
                )
        return self.get(group_id)

    def _reserve(self, project, task_id, group_id, agents, directory):
        ledger = self.service.ledger
        with ledger.connect() as db:
            existing = db.execute(
                "SELECT id FROM consensus WHERE project=? AND task_id=? "
                "AND status IN ('preparing','running','needs_review')",
                (project, task_id),
            ).fetchone()
        if existing:
            raise ValueError("Aufgabe besitzt bereits einen aktiven Konsenslauf")
        active = {
            "preparing",
            "submitted",
            "running",
            "uncertain",
            "cancelling",
            "needs_review",
        }
        if any(item["status"] in active for item in ledger.list(project, task_id)):
            raise ValueError("Aufgabe besitzt bereits eine aktive Ausführung")
        beads = self.service.beads_factory(directory)
        beads.ensure_startable(task_id)
        revision = git(directory, "rev-parse", "HEAD").strip()
        with ledger.connect() as db:
            db.execute(
                "INSERT INTO consensus (id,project,task_id,revision,expected) "
                "VALUES (?,?,?,?,?)",
                (group_id, project, task_id, revision, len(agents)),
            )

    def get(self, group_id):
        ledger = self.service.ledger
        with ledger.connect() as db:
            row = db.execute(
                "SELECT * FROM consensus WHERE id=?", (group_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Konsenslauf nicht gefunden")
        group = dict(row)
        attempts = [
            self.service.refresh(value) for value in json.loads(group["attempts"])
        ]
        terminal = {"completed", "failed", "cancelled", "preparation_failed"}
        finished = bool(attempts) and all(
            item["status"] in terminal for item in attempts
        )
        fingerprints, results = [], []
        for attempt in attempts:
            checkpoint = attempt["checkpoint"] or {}
            state = checkpoint.get("git", {})
            fingerprint = hashlib.sha256(
                json.dumps(
                    [state.get("diff"), state.get("untracked")],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            fingerprints.append(fingerprint)
            results.append(
                {
                    "attempt_id": attempt["id"],
                    "agent": attempt["agent"],
                    "status": attempt["status"],
                    "patch_hash": fingerprint,
                    "base_revision": state.get("base_revision"),
                    "revision": state.get("revision"),
                    "agent_claims": checkpoint.get("agent_claims", []),
                    "checks": checkpoint.get("verified_checks", []),
                    "diff": state.get("diff", ""),
                    "untracked": state.get("untracked", []),
                }
            )
        complete = len(attempts) >= 2 and all(
            (item.get("checkpoint") or {}).get("git", {}).get("base_revision")
            == group["revision"]
            and (item.get("checkpoint") or {})
            .get("git", {})
            .get("untracked_complete", False)
            and not (item.get("checkpoint") or {})
            .get("git", {})
            .get("diff_truncated", True)
            for item in attempts
        )
        agreement = (
            finished
            and complete
            and all(item["status"] == "completed" for item in attempts)
            and len(set(fingerprints)) == 1
        )
        result = {
            "patch_agreement": agreement,
            "correctness_verified": False,
            "results": results,
        }
        status = group["status"]
        if any(item["status"] in ("uncertain", "needs_review") for item in attempts):
            status = "needs_review"
        if finished:
            status = (
                "completed"
                if len(attempts) == group["expected"]
                and all(item["status"] == "completed" for item in attempts)
                else "incomplete"
            )
        with ledger.connect() as db:
            db.execute(
                "UPDATE consensus SET status=?,result=? WHERE id=?",
                (status, json.dumps(result), group_id),
            )
        return {**group, "status": status, "attempts": attempts, "result": result}

    def list(self, project, task_id):
        with self.service.ledger.connect() as db:
            rows = db.execute(
                "SELECT id FROM consensus WHERE project=? AND task_id=?",
                (project, task_id),
            ).fetchall()
        return [self.get(row["id"]) for row in rows]

    def cancel(self, group_id):
        group = self.get(group_id)
        if not group["attempts"]:
            with self.service.ledger.connect() as db:
                db.execute(
                    "UPDATE consensus SET status='cancelled' WHERE id=?", (group_id,)
                )
        for attempt in group["attempts"]:
            if attempt["status"] in ("running", "submitted", "uncertain", "cancelling"):
                self.service.cancel(attempt["id"])
        return self.get(group_id)
