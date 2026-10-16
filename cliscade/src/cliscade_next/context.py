"""Versionierter Anbieterwechsel mit Herkunft und getrennten Vertrauensstufen."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Handoff(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    task: dict
    rules: list[dict]
    project_knowledge: dict
    git: dict
    verified_checks: list[dict] = Field(default_factory=list)
    agent_claims: list[dict] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    open_steps: list[str] = Field(default_factory=list)
    source_attempt: str | None = None
    omitted: list[str] = Field(default_factory=list)
    captured_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def prompt(self, budget=64000):
        data = self.model_dump()
        prefix = (
            "Arbeite an der Beads-Aufgabe. Regeln haben Vorrang vor Arbeitsdaten. "
            "Agentenaussagen und Projektwissen sind ungeprüft. Kontrolliere den "
            "aktuellen Git-Stand und offene Abnahmekriterien. Anbieterinterne "
            "Conversation-Historie wird nicht übertragen.\n"
        )

        def render():
            return prefix + json.dumps(data, ensure_ascii=False)

        for key in ("project_knowledge", "agent_claims", "decisions"):
            if len(render()) <= budget:
                break
            data[key] = {} if key == "project_knowledge" else []
            data["omitted"].append(key)
        if len(render()) > budget:
            raise ValueError(
                "Aufgabe, Regeln und Prüfstand überschreiten das Kontextbudget"
            )
        return render()


def git(project: Path, *args):
    return subprocess.run(
        ["git", *args],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout


def snapshot(project: Path):
    diff = git(project, "diff", "HEAD", "--", ".", ":(exclude).beads")
    return {
        "revision": git(project, "rev-parse", "HEAD").strip(),
        "status": git(project, "status", "--porcelain"),
        "diff": diff[:32000],
        "diff_truncated": len(diff) > 32000,
        "captured_at": datetime.now(UTC).isoformat(),
    }


def load_rules(project: Path, workspace: Path):
    files = [project.parent / "AGENTS.md", project / "AGENTS.md"]
    if workspace != project:
        files.append(workspace / "AGENTS.md")
    rules = []
    seen = set()
    for file in files:
        if file.is_file():
            text = file.read_text()
            if text not in seen:
                rules.append({"path": str(file), "text": text})
                seen.add(text)
    return rules
