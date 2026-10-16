"""Beads-Arbeitseinheiten mit unabhängigen OpenHands-Conversations verbinden."""

import time
from pathlib import Path
from uuid import uuid4

from filelock import FileLock

from cliscade_next.agents import OpenHands, registry
from cliscade_next.beads import Beads
from cliscade_next.context import Handoff, git, load_rules, snapshot
from cliscade_next.ledger import Ledger


def evidence(events):
    starts, checks, claims = {}, [], []
    for event in events:
        action = event.get("action") or {}
        if event.get("kind") == "ActionEvent" and action.get("kind") == "FinishAction":
            claims.append(
                {
                    "verified": False,
                    "event_id": event.get("id"),
                    "message": action.get("message", ""),
                }
            )
        if event.get("kind") == "ACPToolCallEvent":
            tool_id = event.get("tool_call_id")
            raw = event.get("raw_input")
            if event.get("status") in ("pending", "in_progress") and isinstance(
                raw, dict
            ):
                command = raw.get("command")
                if isinstance(command, str):
                    starts[tool_id] = command
            output = event.get("raw_output")
            if tool_id in starts and isinstance(output, dict):
                code = output.get("exit_code", output.get("exitCode"))
                if type(code) is int and event.get("status") in ("completed", "failed"):
                    checks.append(
                        {
                            "command": starts.pop(tool_id),
                            "exit_code": code,
                            "event_id": event.get("id"),
                            "verification": "tool_receipt",
                            "independently_reproduced": False,
                            "timestamp": event.get("timestamp"),
                        }
                    )
        if event.get("kind") == "MessageEvent" and event.get("source") == "agent":
            claims.append(
                {
                    "verified": False,
                    "event_id": event.get("id"),
                    "message": event.get("llm_message", {}),
                }
            )
    return checks, claims


class Orchestrator:
    def __init__(
        self, settings, runner=None, beads_factory=Beads, agents=None, settle_seconds=30
    ):
        self.settings = settings
        self.ledger = Ledger(settings.state)
        self.runner = runner or OpenHands(settings)
        self.beads_factory = beads_factory
        self.agents = agents if agents is not None else registry()
        self.settle_seconds = settle_seconds

    def checkpoint(self, attempt, events=()):
        project = self.settings.project(attempt["project"])
        beads = self.beads_factory(project)
        workspace = Path(attempt["workspace"])
        checks, claims = evidence(events)
        old = attempt.get("checkpoint") or {}
        return Handoff(
            task=beads.show(attempt["task_id"]),
            rules=load_rules(project, workspace),
            project_knowledge=beads.context(),
            git=snapshot(workspace),
            verified_checks=checks or old.get("verified_checks", []),
            agent_claims=claims or old.get("agent_claims", []),
            decisions=old.get("decisions", []),
            open_steps=old.get("open_steps")
            or ["Abnahmekriterien am Git-Stand prüfen"],
            source_attempt=attempt.get("source_id"),
        ).model_dump()

    def start(self, project_name, task_id, agent_id, source_id=None):
        if agent_id not in self.agents:
            raise ValueError("ACP-Agent ist nicht freigegeben")
        project = self.settings.project(project_name)
        self.settings.state.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.settings.state / "dispatch.lock"), timeout=30):
            source = self.refresh(source_id) if source_id else None
            if source:
                if (source["project"], source["task_id"]) != (project_name, task_id):
                    raise ValueError("Übergabe gehört zu einer anderen Aufgabe")
                if source["status"] in ("uncertain", "preparing", "needs_review"):
                    raise ValueError(
                        "Unsicherer Stand: zuerst Session und Dateien prüfen"
                    )
                if source["status"] not in ("completed", "failed", "cancelled"):
                    raise ValueError("Ausführung vor der Übergabe anhalten")
                workspace = Path(source["workspace"])
            else:
                workspace = (
                    self.settings.projects / ".cliscade-worktrees" / str(uuid4())
                )
                workspace.parent.mkdir(parents=True, exist_ok=True)
                git(project, "worktree", "add", "--detach", str(workspace), "HEAD")
            attempt = self.ledger.create(
                project_name, task_id, agent_id, workspace, source_id
            )
            session = None
            try:
                checkpoint = self.checkpoint(attempt)
                if source:
                    checkpoint.update(
                        {
                            key: source["checkpoint"][key]
                            for key in (
                                "verified_checks",
                                "agent_claims",
                                "decisions",
                                "open_steps",
                            )
                        }
                    )
                    checkpoint["source_attempt"] = source_id
                prompt = Handoff.model_validate(checkpoint).prompt()
                self.ledger.update(attempt["id"], checkpoint=checkpoint)
                self.beads_factory(project).assign(
                    task_id, agent_id, previous=source["agent"] if source else None
                )
                session = self.runner.attach(self.agents[agent_id], workspace)
                self.ledger.update(
                    attempt["id"],
                    session_id=session.id,
                    prompt_sent=1,
                    status="submitted",
                )
                session.submit(prompt)
                return self.ledger.update(attempt["id"], status="running")
            except Exception:
                saved = self.ledger.get(attempt["id"])
                return self.ledger.update(
                    attempt["id"],
                    status="uncertain"
                    if saved["prompt_sent"]
                    else "preparation_failed",
                    error="Ausführung fehlgeschlagen; Session und Arbeitsstand prüfen",
                )
            finally:
                if session:
                    session.close()

    def refresh(self, attempt_id):
        attempt = self.ledger.get(attempt_id)
        if attempt["status"] in (
            "completed",
            "failed",
            "cancelled",
            "preparation_failed",
        ):
            return attempt
        if not attempt["session_id"]:
            return self.ledger.update(
                attempt_id,
                status="needs_review",
                error="Vorbereitung unterbrochen; kein automatischer Neustart",
            )
        session = self.runner.attach(
            self.agents[attempt["agent"]],
            Path(attempt["workspace"]),
            attempt["session_id"],
        )
        try:
            state = session.state()
            status = state["status"]
            if status in ("finished", "error", "stuck", "paused"):
                seen = attempt["terminal_seen"]
                if status == "finished" and (
                    seen is None or time.time() - seen < self.settle_seconds
                ):
                    if seen is None:
                        self.ledger.update(attempt_id, terminal_seen=time.time())
                    if self.settle_seconds:
                        return self.ledger.get(attempt_id)
                terminal = {
                    "finished": "completed",
                    "error": "failed",
                    "stuck": "failed",
                    "paused": "cancelled"
                    if attempt["status"] == "cancelling"
                    else "needs_review",
                }
                return self.ledger.update(
                    attempt_id,
                    status=terminal[status],
                    checkpoint=self.checkpoint(attempt, state["events"]),
                )
            if status == "running":
                return self.ledger.update(
                    attempt_id, terminal_seen=None, status="running"
                )
            return attempt
        finally:
            session.close()

    def cancel(self, attempt_id):
        attempt = self.ledger.get(attempt_id)
        if not attempt["session_id"] or attempt["status"] in (
            "completed",
            "failed",
            "cancelled",
        ):
            raise ValueError("Keine aktive Session vorhanden")
        self.ledger.update(attempt_id, status="cancelling")
        session = self.runner.attach(
            self.agents[attempt["agent"]],
            Path(attempt["workspace"]),
            attempt["session_id"],
        )
        try:
            session.cancel()
        finally:
            session.close()
        return self.refresh(attempt_id)
