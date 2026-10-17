"""Begrenzten nativen Beads-/OpenHands-Test vorbereiten und unabhängig prüfen.

Im Integrationscontainer ausführen. prepare startet keine Inferenz; den Task
anschließend in /tasks mit openhands und openai/c1 starten. verify prüft den
angegebenen Attempt, ohne neue Ausführung oder Änderungen an GitHub auszulösen.
"""

import argparse
import json
import subprocess
from pathlib import Path

import httpx

from cliscade_next.beads import Beads
from cliscade_next.config import Settings

PROJECT = "task-harness-proof-v010"
FILENAME = "native-task-proof.txt"
EXPECTED = b"TASK_HARNESS_OK"


def prepare(settings):
    root = settings.projects / PROJECT
    if root.exists() and not (root / ".git").exists():
        raise ValueError("Vorhandenes Verzeichnis ist kein Test-Repository")
    root.mkdir(exist_ok=True)
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "AGENTS.md").write_text(
            "# Begrenzter Test\nNur die in der Aufgabe genannte Datei ändern. "
            "Kein Commit, Push, PR und keine Zugriffe auf andere Projekte.\n"
        )
        subprocess.run(["git", "-C", str(root), "add", "AGENTS.md"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=CLIScade Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "Lege Testregeln an",
            ],
            check=True,
        )
    Beads.initialize(root)
    return Beads(root).create(
        "Prüfe nativen OpenHands-Task-Harness",
        description=(
            f"Erstelle ausschließlich {FILENAME} mit exakt TASK_HARNESS_OK "
            "ohne Zeilenumbruch. Prüfe den Dateiinhalt mit python3 und einem "
            "assert auf die exakten Bytes. Keine anderen Dateien ändern. "
            "Kein Commit, Push oder Pull Request."
        ),
        acceptance="Datei enthält exakt TASK_HARNESS_OK; Werkzeugprüfung mit Exit 0.",
    )


def verify(settings, attempt_id):
    with httpx.Client(
        base_url="http://127.0.0.1:18002/cliscade/v1",
        headers={"X-Session-API-Key": settings.api_key},
        timeout=60,
    ) as client:
        response = client.get(f"/attempts/{attempt_id}")
        response.raise_for_status()
        attempt = response.json()
    assert attempt["project"] == PROJECT
    assert attempt["agent"] == "openhands"
    assert attempt["model"] == "openai/c1"
    assert attempt["status"] == "completed", attempt["status"]
    assert attempt["error"] is None, attempt["error"]
    path = Path(attempt["workspace"]) / FILENAME
    assert path.read_bytes() == EXPECTED, "Exakter Dateiinhalt nicht erfüllt"
    assert not (settings.projects / PROJECT / FILENAME).exists(), (
        "Agent hat außerhalb des Ausführungs-Worktrees geschrieben"
    )
    source = settings.projects / PROJECT
    source_status = subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "status",
            "--porcelain",
            "--",
            ".",
            ":(exclude).beads",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert not source_status.strip(), "Quellprojekt enthält Dateiänderungen"
    source_revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert source_revision == attempt["base_revision"], "Quellrevision verändert"
    assert attempt["checkpoint"]["git"]["working_directory"] == attempt["workspace"]
    assert attempt["checkpoint"]["git"]["revision"] == attempt["base_revision"], (
        "Agent hat entgegen der Testregel committet"
    )
    checks = attempt["checkpoint"]["verified_checks"]
    assert any(check["exit_code"] == 0 for check in checks), "Werkzeugbeleg fehlt"
    return {
        "project": PROJECT,
        "task_id": attempt["task_id"],
        "attempt_id": attempt["id"],
        "session_id": attempt["session_id"],
        "model": attempt["model"],
        "status": attempt["status"],
        "exact_file_verified": True,
        "tool_receipts": len(checks),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "verify"])
    parser.add_argument("--attempt")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.mode == "prepare":
        task = prepare(settings)
        result = {"project": PROJECT, "task_id": task["id"]}
    else:
        if not args.attempt:
            parser.error("verify benötigt --attempt")
        result = verify(settings, args.attempt)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
