"""Versionierter Anbieterwechsel mit Herkunft und getrennten Vertrauensstufen."""

import hashlib
import json
import re
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
    runtime_errors: list[dict] = Field(default_factory=list)
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
        prefix = prefix.rstrip() + (
            " Ergänze abschließend einen <cliscade-report> mit JSON: "
            '{"schema_version":1,"decisions":["..."],"open_steps":["..."]}'
            "</cliscade-report>. Aussagen darin gelten als ungeprüft.\n"
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


class AgentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    decisions: list[str] = Field(default_factory=list, max_length=30)
    open_steps: list[str] = Field(default_factory=list, max_length=30)


def report_from_claims(claims):
    for claim in reversed(claims):
        message = claim.get("message")
        if not isinstance(message, str):
            continue
        matches = re.findall(r"<cliscade-report>(.*?)</cliscade-report>", message, re.S)
        for value in reversed(matches):
            if len(value) > 16000:
                continue
            try:
                return AgentReport.model_validate_json(value)
            except ValueError:
                continue
    return None


def git(project: Path, *args):
    return subprocess.run(
        ["git", *args],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout


def snapshot(project: Path, base_revision=None):
    base_revision = base_revision or git(project, "rev-parse", "HEAD").strip()
    diff = git(
        project,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--binary",
        base_revision,
        "--",
        ".",
        ":(exclude).beads",
    )
    untracked = []
    complete = True
    names = list(
        filter(
            None,
            git(
                project,
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                ".",
                ":(exclude).beads",
            ).split("\0"),
        )
    )
    for name in names[:256]:
        file = project / name
        if file.is_symlink():
            value = str(file.readlink()).encode()
        elif file.is_file() and file.stat().st_size <= 16 * 1024 * 1024:
            value = file.read_bytes()
        else:
            complete = False
            untracked.append({"path": name, "omitted": True})
            continue
        untracked.append(
            {
                "path": name,
                "kind": "symlink" if file.is_symlink() else "file",
                "executable": bool(file.lstat().st_mode & 0o100),
                "sha256": hashlib.sha256(value).hexdigest(),
            }
        )
    return {
        "revision": git(project, "rev-parse", "HEAD").strip(),
        "base_revision": base_revision,
        "status": git(project, "status", "--porcelain"),
        "diff": diff[:32000],
        "diff_truncated": len(diff) > 32000,
        "captured_at": datetime.now(UTC).isoformat(),
        "untracked": untracked,
        "untracked_complete": complete and len(names) <= 256,
    }


def load_rules(project: Path, workspace: Path, base_revision=None):
    files = [project.parent / "AGENTS.md", project / "AGENTS.md"]
    if workspace != project:
        files.append(workspace / "AGENTS.md")
    changed = git(
        workspace, "diff", "--name-only", base_revision or "HEAD", "-z"
    ).split("\0")
    changed += git(workspace, "ls-files", "--others", "--exclude-standard", "-z").split(
        "\0"
    )
    for name in filter(None, changed):
        directory = (workspace / name).parent
        while directory.is_relative_to(workspace) and directory != workspace:
            file = directory / "AGENTS.md"
            if not file.is_symlink() and file not in files:
                files.append(file)
            directory = directory.parent
    rules = []
    seen = set()
    for file in files:
        if file.is_file():
            text = file.read_text()
            if text not in seen:
                rules.append({"path": str(file), "text": text})
                seen.add(text)
    return rules
