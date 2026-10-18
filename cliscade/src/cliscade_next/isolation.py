"""Erkennt Schreibzugriffe außerhalb des Arbeitsbaums eines Runs.

Ein Worktree ist keine Dateisystemgrenze: der Agent läuft als Prozess mit Zugriff
auf das ganze Projektverzeichnis, und ein falscher Pfad im Prompt hat im Lauf
`cn-wba` genau das getan — im Quellprojekt committet. Diese Prüfung verhindert
das nicht, sie macht es sichtbar. Vor dem Start wird der Git-Zustand jedes
registrierten Projekts festgehalten, nach dem Lauf verglichen. Weicht ein fremdes
Projekt ab, gilt der Lauf als nicht belegt.

Grenze: erkannt werden nur Änderungen, die Git sieht (HEAD oder Status) in
Verzeichnissen, die als Projekt registriert sind. Schreibzugriffe außerhalb von
`/projects`, ignoriert Dateien und nicht versionierte Fremdverzeichnisse bleiben
unsichtbar. Echte Isolation braucht einen Container je Lauf.
"""

import subprocess
from pathlib import Path

SKIP_PREFIX = "."


def _git(root, *args):
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout


def repo_state(root):
    """HEAD und sichtbarer Status eines Projektverzeichnisses, ohne Beads-Daten."""
    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return None
    status = _git(root, "status", "--porcelain", "--", ".", ":(exclude).beads")
    return {
        "head": head.strip(),
        "status": sorted(line for line in (status or "").splitlines() if line.strip()),
    }


def snapshot(projects_root):
    """Zustand aller Projektverzeichnisse unterhalb des Projekt-Roots."""
    root = Path(projects_root)
    if not root.is_dir():
        return {}
    states = {}
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.is_symlink() or path.name.startswith(SKIP_PREFIX):
            continue
        state = repo_state(path)
        if state is not None:
            states[path.name] = state
    return states


def violations(before, after):
    """Projekte, deren Git-Zustand sich während des Laufs geändert hat."""
    changed = []
    for name, state in after.items():
        old = before.get(name)
        if old is None:
            continue
        if old.get("head") != state.get("head") or old.get("status") != state.get(
            "status"
        ):
            changed.append(name)
    return sorted(changed)


def check(before, after):
    """Vergleichsergebnis als Checkpoint-Eintrag."""
    changed = violations(before or {}, after or {})
    return {
        "ok": not changed,
        "changed_projects": changed,
        "scope": "git HEAD and status of registered projects",
    }
