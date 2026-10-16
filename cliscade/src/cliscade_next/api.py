"""Authentifizierte Aufgaben-API; Ausführung bleibt im OpenHands Agent Server."""

import hmac
import sqlite3
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from cliscade_next.beads import Beads
from cliscade_next.config import Settings
from cliscade_next.orchestrator import Orchestrator


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
    agent_id: str = Field(min_length=1, max_length=100)
    source_id: str | None = None


class DependencyInput(BaseModel):
    depends_on: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{1,150}$")


def create_app(settings=None, orchestrator=None):
    settings = settings or Settings.from_env()
    service = orchestrator or Orchestrator(settings)

    def authenticate(x_session_api_key: Annotated[str, Header()] = ""):
        if not settings.api_key or not hmac.compare_digest(
            x_session_api_key, settings.api_key
        ):
            raise HTTPException(401, "Anmeldung erforderlich")

    app = FastAPI(title="CLIScade Next", dependencies=[Depends(authenticate)])
    prefix = "/cliscade/v1"

    @app.exception_handler(ValueError)
    def bad_request(request, error):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(RuntimeError)
    def unavailable(request, error):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.exception_handler(sqlite3.IntegrityError)
    def conflict(request, error):
        return JSONResponse(
            status_code=409, content={"detail": "Arbeitsverzeichnis belegt"}
        )

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
            }
            for agent in service.agents.values()
        ]

    @app.get(prefix + "/projects/{project}/tasks")
    def tasks(project: str):
        return Beads(settings.project(project)).tasks()

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
        return service.start(project, **body.model_dump())

    @app.get(prefix + "/attempts/{attempt_id}")
    def refresh(attempt_id: str):
        return service.refresh(attempt_id)

    @app.post(prefix + "/attempts/{attempt_id}/cancel")
    def cancel(attempt_id: str):
        return service.cancel(attempt_id)

    return app
