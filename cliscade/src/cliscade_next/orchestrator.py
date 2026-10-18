"""Beads-Arbeitseinheiten mit unabhängigen OpenHands-Conversations verbinden."""

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from filelock import FileLock, Timeout

from cliscade_next import isolation
from cliscade_next.agents import OpenHands, registry
from cliscade_next.beads import Beads
from cliscade_next.context import Handoff, git, load_rules, report_from_claims, snapshot
from cliscade_next.ledger import Ledger
from cliscade_next.projects import link_beads


def evidence(events):
    starts, checks, claims = {}, [], []
    native_starts = {}
    for event in events:
        action = event.get("action") or {}
        if (
            event.get("kind") == "ActionEvent"
            and event.get("tool_name") == "terminal"
            and isinstance(action.get("command"), str)
        ):
            native_starts[event.get("id")] = event
        if (
            event.get("kind") == "ObservationEvent"
            and event.get("tool_name") == "terminal"
        ):
            start = native_starts.get(event.get("action_id"))
            output = event.get("observation") or {}
            code = output.get("exit_code")
            if (
                start
                and start.get("tool_call_id") == event.get("tool_call_id")
                and type(code) is int
                and code >= 0
                and not output.get("timeout")
            ):
                checks.append(
                    {
                        "command": start["action"]["command"],
                        "exit_code": code,
                        "event_id": event.get("id"),
                        "verification": "tool_receipt",
                        "independently_reproduced": False,
                        "timestamp": event.get("timestamp"),
                    }
                )
                native_starts.pop(event["action_id"])
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
        report = report_from_claims(claims)
        base_revision = (
            attempt.get("base_revision")
            or old.get("git", {}).get("base_revision")
            or old.get("git", {}).get("revision")
        )
        current_git = snapshot(workspace, base_revision)
        current_git["working_directory"] = str(workspace)
        for check in checks:
            check["checkpoint_revision"] = current_git["revision"]
            check["execution_revision_known"] = False
        baseline = (old.get("isolation") or {}).get("baseline")
        isolation_state = isolation.check(
            baseline, isolation.snapshot(self.settings.projects)
        )
        if baseline is not None:
            isolation_state["baseline"] = baseline
        errors = [
            {
                "code": event.get("code"),
                "reported_by": "OpenHands ConversationErrorEvent",
                "timestamp": event.get("timestamp"),
            }
            for event in events
            if event.get("kind") == "ConversationErrorEvent"
        ]
        if isolation_state["changed_projects"]:
            errors.append(
                {
                    "code": "IsolationViolation",
                    "reported_by": "git status of registered projects",
                    "timestamp": None,
                    "detail": isolation_state["changed_projects"],
                }
            )
        return Handoff(
            task=beads.show(attempt["task_id"]),
            rules=load_rules(project, workspace, current_git["base_revision"]),
            project_knowledge=beads.context(),
            git=current_git,
            verified_checks=checks or old.get("verified_checks", []),
            runtime_errors=errors,
            isolation=isolation_state,
            agent_claims=claims or old.get("agent_claims", []),
            decisions=report.decisions if report else old.get("decisions", []),
            open_steps=report.open_steps
            if report
            else (old.get("open_steps") or ["Abnahmekriterien am Git-Stand prüfen"]),
            source_attempt=attempt.get("source_id"),
        ).model_dump()

    def start(
        self,
        project_name,
        task_id,
        agent_id,
        source_id=None,
        *,
        allow_parallel=False,
        assign=True,
        request_key=None,
        request_fingerprint=None,
        consensus_id=None,
        initial_context=None,
        model=None,
    ):
        if agent_id not in self.agents or not self.agents[agent_id].enabled:
            raise ValueError("Agent ist nicht freigegeben")
        agent = replace(
            self.agents[agent_id],
            model=model if model is not None else self.agents[agent_id].model,
        )
        project = self.settings.project(project_name)
        self.settings.state.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.settings.state / "dispatch.lock"), timeout=30):
            fingerprint = (
                request_fingerprint
                or hashlib.sha256(
                    json.dumps(
                        [project_name, task_id, agent_id, source_id]
                        + ([model] if model is not None else [])
                    ).encode()
                ).hexdigest()
            )
            if request_key:
                existing = self.ledger.request(request_key, fingerprint)
                if existing:
                    return existing
            if model is not None or agent_id == "openhands":
                discovery = self.runner.probe(agent)
                models = {
                    item["model_id"] for item in discovery.get("available_models", [])
                }
                if discovery.get("error") or agent.model not in models:
                    raise ValueError("Modell ist für diesen Agenten nicht verfügbar")
            with self.ledger.connect() as db:
                group = db.execute(
                    "SELECT id FROM consensus WHERE project=? AND task_id=? "
                    "AND status IN ('preparing','running','needs_review') "
                    "AND id != ?",
                    (project_name, task_id, consensus_id or ""),
                ).fetchone()
            if group:
                raise ValueError("Aufgabe besitzt einen aktiven Konsenslauf")
            self.beads_factory(project).ensure_startable(task_id)
            if not allow_parallel and any(
                item["id"] != source_id
                and item["status"]
                in (
                    "preparing",
                    "submitted",
                    "running",
                    "cancelling",
                    "uncertain",
                    "needs_review",
                )
                for item in self.ledger.list(project_name, task_id)
            ):
                raise ValueError(
                    "Für diese Aufgabe läuft bereits eine Ausführung oder Prüfung"
                )
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
                if git(
                    project, "status", "--porcelain", "--", ".", ":(exclude).beads"
                ).strip():
                    raise ValueError(
                        "Projekt zuerst committen; neue Worktrees beginnen bei HEAD"
                    )
                workspace = (
                    self.settings.projects / ".cliscade-worktrees" / str(uuid4())
                )
                workspace.parent.mkdir(parents=True, exist_ok=True)
                branch = f"cliscade/{task_id}-{str(uuid4())[:8]}"
                git(project, "worktree", "add", "-b", branch, str(workspace), "HEAD")
                link_beads(project, workspace)
            attempt = self.ledger.create(
                project_name,
                task_id,
                agent_id,
                workspace,
                source_id,
                request_key,
                fingerprint,
                model=agent.model,
                base_revision=(
                    source["checkpoint"]["git"].get("base_revision")
                    or source["checkpoint"]["git"]["revision"]
                    if source
                    else git(workspace, "rev-parse", "HEAD").strip()
                ),
            )
            session = None
            try:
                checkpoint = self.checkpoint(attempt)
                if initial_context:
                    checkpoint.update(initial_context)
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
                if assign:
                    self.beads_factory(project).assign(
                        task_id, agent_id, previous=source["agent"] if source else None
                    )
                # Zustand aller Projekte nach dem Assign, direkt vor dem Submit:
                # so zählt weder die eigene Vorbereitung noch die Beads-Änderung
                # als Verletzung, aber jeder Schreibzugriff des Agenten danach.
                checkpoint["isolation"] = {
                    "ok": True,
                    "changed_projects": [],
                    "baseline": isolation.snapshot(self.settings.projects),
                }
                self.ledger.update(attempt["id"], checkpoint=checkpoint)
                session = self.runner.attach(agent, workspace)
                self.ledger.update(
                    attempt["id"],
                    session_id=session.id,
                    prompt_sent=1,
                    status="submitted",
                    error=None,
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
            try:
                with FileLock(str(self.settings.state / "dispatch.lock"), timeout=0):
                    attempt = self.ledger.get(attempt_id)
                    if not attempt["session_id"]:
                        return self.ledger.update(
                            attempt_id,
                            status="needs_review",
                            error=(
                                "Vorbereitung unterbrochen; kein automatischer Neustart"
                            ),
                        )
            except Timeout:
                return attempt
        session = self.runner.attach(
            self.attempt_agent(attempt),
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
            self.attempt_agent(attempt),
            Path(attempt["workspace"]),
            attempt["session_id"],
        )
        try:
            session.cancel()
        finally:
            session.close()
        return self.refresh(attempt_id)

    def resume(self, attempt_id):
        source = self.refresh(attempt_id)
        if (
            source["status"] not in ("cancelled", "failed", "needs_review")
            or not source["session_id"]
        ):
            raise ValueError("Nur angehaltene oder fehlgeschlagene Sessions fortsetzen")
        with FileLock(str(self.settings.state / "dispatch.lock"), timeout=30):
            self.beads_factory(
                self.settings.project(source["project"])
            ).ensure_startable(source["task_id"])
            attempt = self.ledger.create(
                source["project"],
                source["task_id"],
                source["agent"],
                source["workspace"],
                source["id"],
                model=source.get("model"),
                base_revision=(
                    source.get("base_revision")
                    or source["checkpoint"]["git"].get("base_revision")
                    or source["checkpoint"]["git"]["revision"]
                ),
            )
            checkpoint = self.checkpoint(source)
            checkpoint["source_attempt"] = source["id"]
            self.ledger.update(
                attempt["id"],
                session_id=source["session_id"],
                checkpoint=checkpoint,
                prompt_sent=1,
                status="submitted",
            )
            session = None
            try:
                session = self.runner.attach(
                    self.attempt_agent(source),
                    Path(source["workspace"]),
                    source["session_id"],
                )
                session.submit(Handoff.model_validate(checkpoint).prompt())
                return self.ledger.update(attempt["id"], status="running")
            except Exception:
                return self.ledger.update(
                    attempt["id"],
                    status="uncertain",
                    error="Fortsetzung prüfen; kein automatisches Replay",
                )
            finally:
                if session:
                    session.close()

    def attempt_agent(self, attempt):
        agent = self.agents[attempt["agent"]]
        return replace(agent, model=attempt.get("model") or agent.model)
