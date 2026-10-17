"""Authentifizierte Aufgaben-API; Ausführung bleibt im OpenHands Agent Server."""

import hashlib
import hmac
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from cliscade_next.agents import OpenHands
from cliscade_next.automation import Automation
from cliscade_next.backup import backup
from cliscade_next.beads import Beads
from cliscade_next.config import Settings
from cliscade_next.consensus import Consensus
from cliscade_next.login import LoginService
from cliscade_next.orchestrator import Orchestrator
from cliscade_next.repositories import RepositoryWorkspaces
from cliscade_next.routing import Routing


class TaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=32000)
    acceptance: str = Field(default="", max_length=16000)
    priority: int = Field(default=2, ge=0, le=4)
    parent: str | None = None


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=32000)
    acceptance: str | None = Field(default=None, max_length=16000)
    priority: int | None = Field(default=None, ge=0, le=4)
    assignee: str | None = Field(default=None, max_length=200)
    status: str | None = Field(
        default=None, pattern="^(open|in_progress|blocked|closed)$"
    )


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{1,150}$")
    agent_id: str = Field(default="auto", min_length=1, max_length=100)
    source_id: str | None = None
    capability: str = Field(default="coding", pattern="^(coding|review|analysis)$")
    request_key: str | None = Field(default=None, min_length=1, max_length=200)


class DependencyInput(BaseModel):
    depends_on: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{1,150}$")


class ConsensusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{1,150}$")
    agents: list[str] = Field(min_length=2, max_length=4)


class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cron: str = Field(min_length=1, max_length=100)
    timezone: str = Field(default="Europe/Berlin", min_length=1, max_length=100)
    agent_id: str = Field(default="auto", min_length=1, max_length=100)


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginCode(LoginInput):
    id: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=4096)


class RepositoryInput(LoginInput):
    name: str = Field(min_length=3, max_length=200)


def create_app(settings=None, orchestrator=None):
    settings = settings or Settings.from_env()
    service = orchestrator or Orchestrator(settings)

    login = LoginService(
        Path(os.environ.get("CLISCADE_LOGIN_HOME", str(settings.state / "login-home"))),
        on_complete=OpenHands(settings).save_account,
    )

    @asynccontextmanager
    async def lifespan(app):
        yield
        login.close()

    def authenticate(x_session_api_key: Annotated[str, Header()] = ""):
        if not settings.api_key or not hmac.compare_digest(
            x_session_api_key, settings.api_key
        ):
            raise HTTPException(401, "Anmeldung erforderlich")

    app = FastAPI(
        title="CLIScade Next", dependencies=[Depends(authenticate)], lifespan=lifespan
    )
    prefix = "/cliscade/v1"
    repositories = RepositoryWorkspaces(settings)

    @app.get(prefix + "/repository-workspaces")
    def repository_workspaces():
        return repositories.catalog()

    @app.post(prefix + "/repository-workspaces")
    def prepare_repository(body: RepositoryInput):
        return repositories.prepare(body.name)

    @app.exception_handler(ValueError)
    def bad_request(request, error):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(RuntimeError)
    def unavailable(request, error):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.exception_handler(httpx.HTTPError)
    def automation_unavailable(request, error):
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "OpenHands-Automation nicht verfügbar oder Zeitplan abgewiesen; "
                    "Zeitplan und Dienstdaten prüfen"
                )
            },
        )

    @app.exception_handler(sqlite3.IntegrityError)
    def conflict(request, error):
        return JSONResponse(
            status_code=409, content={"detail": "Arbeitsverzeichnis belegt"}
        )

    @app.get(prefix + "/agents/{agent_id}/login")
    def login_state(agent_id: str):
        state = login.current(agent_id)
        if state["state"] == "pending":
            return {**state, "available": True, "connected": False}
        return {**state, **login.status(agent_id)}

    @app.post(prefix + "/agents/{agent_id}/login")
    def login_start(agent_id: str, body: LoginInput):
        return login.start(agent_id)

    @app.post(prefix + "/agents/{agent_id}/login/code")
    def login_code(agent_id: str, body: LoginCode):
        return login.submit(agent_id, body.id, body.code)

    @app.delete(prefix + "/agents/{agent_id}/login/{job_id}")
    def login_cancel(agent_id: str, job_id: str):
        return login.cancel(agent_id, job_id)

    @app.get(prefix + "/projects")
    def projects():
        return [
            {"id": path.name, "beads": (path / ".beads").is_dir()}
            for path in sorted(settings.projects.iterdir())
            if path.is_dir() and not path.name.startswith(".") and not path.is_symlink()
        ]

    @app.get(prefix + "/agents")
    def agents():
        return [
            {
                "id": agent.id,
                "command": agent.command,
                "model": agent.model,
                "live_verified": False,
                "transport": "acp",
                "priority": agent.priority,
                "capabilities": agent.capabilities,
                "enabled": agent.enabled,
            }
            for agent in service.agents.values()
        ]

    @app.post(prefix + "/agents/{agent_id}/probe")
    def probe(agent_id: str):
        return Routing(service).probe(agent_id)

    @app.get(prefix + "/projects/{project}/tasks")
    def tasks(project: str):
        return Beads(settings.project(project)).tasks()

    @app.get(prefix + "/projects/{project}/tasks/{task_id}")
    def task(project: str, task_id: str):
        return Beads(settings.project(project)).show(task_id)

    @app.post(prefix + "/projects/{project}/initialize")
    def initialize(project: str):
        return Beads.initialize(settings.project(project))

    @app.post(prefix + "/projects/{project}/tasks", status_code=201)
    def create_task(project: str, body: TaskInput):
        return Beads(settings.project(project)).create(**body.model_dump())

    @app.patch(prefix + "/projects/{project}/tasks/{task_id}")
    def update_task(project: str, task_id: str, body: TaskUpdate):
        return Beads(settings.project(project)).update(
            task_id, **body.model_dump(exclude_none=True)
        )

    @app.post(prefix + "/projects/{project}/tasks/{task_id}/dependencies")
    def dependency(project: str, task_id: str, body: DependencyInput):
        return Beads(settings.project(project)).dependency(task_id, body.depends_on)

    @app.get(prefix + "/projects/{project}/attempts")
    def attempts(project: str, task_id: str | None = None):
        settings.project(project)
        return service.ledger.list(project, task_id)

    @app.post(prefix + "/projects/{project}/attempts", status_code=201)
    def start(project: str, body: StartInput):
        fingerprint = hashlib.sha256(
            json.dumps(
                [project, body.model_dump(exclude={"request_key"})],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        if body.request_key:
            existing = service.ledger.request(body.request_key, fingerprint)
            if existing:
                return existing
        if body.agent_id == "auto":
            result = Routing(service).start(
                project,
                body.task_id,
                body.capability,
                body.source_id,
                body.request_key,
                fingerprint,
            )
            if result["attempt"] is None:
                raise RuntimeError(
                    "Keine verfügbare ACP-Route; Agenten und Modelle prüfen"
                )
            return result["attempt"]
        return service.start(
            project,
            body.task_id,
            body.agent_id,
            body.source_id,
            request_key=body.request_key,
            request_fingerprint=fingerprint,
        )

    @app.get(prefix + "/attempts/{attempt_id}")
    def refresh(attempt_id: str):
        return service.refresh(attempt_id)

    @app.post(prefix + "/attempts/{attempt_id}/cancel")
    def cancel(attempt_id: str):
        return service.cancel(attempt_id)

    @app.post(prefix + "/attempts/{attempt_id}/resume")
    def resume(attempt_id: str):
        return service.resume(attempt_id)

    @app.post(prefix + "/projects/{project}/backups", status_code=201)
    def backup_project(project: str):
        return backup(settings.project(project), settings.state)

    @app.post(prefix + "/projects/{project}/consensus", status_code=201)
    def start_consensus(project: str, body: ConsensusInput):
        return Consensus(service).start(project, body.task_id, body.agents)

    @app.get(prefix + "/projects/{project}/consensus")
    def consensus(project: str, task_id: str):
        settings.project(project)
        return Consensus(service).list(project, task_id)

    @app.post(prefix + "/consensus/{group_id}/cancel")
    def cancel_consensus(group_id: str):
        return Consensus(service).cancel(group_id)

    @app.post(prefix + "/projects/{project}/tasks/{task_id}/schedule", status_code=201)
    def schedule(project: str, task_id: str, body: ScheduleInput):
        Beads(settings.project(project)).show(task_id)
        if body.agent_id != "auto" and body.agent_id not in service.agents:
            raise ValueError("ACP-Agent ist nicht freigegeben")
        return Automation(settings).create(
            project, task_id, body.agent_id, body.cron, body.timezone
        )

    return app
