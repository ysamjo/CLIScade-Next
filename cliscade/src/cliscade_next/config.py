"""Explizite Projektgrenzen und gemeinsame Mount-Pfade."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    projects: Path
    state: Path
    agent_server: str
    api_key: str = field(repr=False)

    def __post_init__(self):
        object.__setattr__(self, "projects", self.projects.resolve())
        object.__setattr__(self, "state", self.state.resolve())

    @classmethod
    def from_env(cls):
        return cls(
            Path(os.environ.get("CLISCADE_PROJECTS", "/projects")),
            Path(os.environ.get("CLISCADE_STATE", "/data/cliscade")),
            os.environ.get("CLISCADE_AGENT_SERVER", "http://127.0.0.1:8000"),
            os.environ["CLISCADE_API_KEY"],
        )

    def project(self, name: str) -> Path:
        root = self.projects.resolve()
        project = (root / name).resolve()
        if Path(name).is_absolute() or not project.is_relative_to(root):
            raise ValueError("Projekt liegt außerhalb des freigegebenen Verzeichnisses")
        if project == root or not project.is_dir():
            raise ValueError("Projektverzeichnis fehlt")
        return project
