"""Ein GitHub-Repository entspricht genau einem Projekt mit einer Beads-Liste."""

import json
from pathlib import Path

from filelock import FileLock

from cliscade_next.beads import Beads
from cliscade_next.context import git


class Projects:
    """Dauerhafte Zuordnung Repository -> Projektverzeichnis -> Beads-Bestand.

    Die Projekt-ID ist der Verzeichnisname und bleibt über alle Runs stabil.
    Sie entsteht einmal aus `owner/repo` und wird danach nie neu vergeben.
    """

    def __init__(self, settings):
        self.settings = settings
        settings.state.mkdir(parents=True, exist_ok=True)
        self.path = settings.state / "projects.json"
        self.lock = FileLock(str(self.path) + ".lock")

    @staticmethod
    def project_id(name):
        owner, _, repo = name.partition("/")
        if not owner or not repo:
            raise ValueError("GitHub-Repository im Format owner/repo wählen.")
        return f"{owner}--{repo}"

    def root(self, name):
        return self.settings.projects / self.project_id(name)

    def records(self):
        with self.lock:
            if not self.path.exists():
                return {}
            return json.loads(self.path.read_text()).get("projects", {})

    def get(self, name):
        return self.records().get(name)

    def register(self, name, root, default_branch="main"):
        """Projekt einmalig eintragen; ein vorhandener Eintrag bleibt bestehen."""
        project_id = self.project_id(name)
        with self.lock:
            data = json.loads(self.path.read_text()) if self.path.exists() else {}
            projects = data.setdefault("projects", {})
            record = projects.setdefault(
                name,
                {
                    "id": project_id,
                    "repository": name,
                    "root": str(root),
                    "default_branch": default_branch,
                },
            )
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(data, indent=2, sort_keys=True))
            temp.replace(self.path)
        return record

    def ensure_beads(self, name):
        """Genau eine Beads-Liste je Projekt; wiederholte Aufrufe sind folgenlos."""
        record = self.get(name)
        if record is None:
            raise ValueError("Projekt ist nicht eingetragen")
        root = Path(record["root"])
        if (root / ".beads").is_dir():
            return True
        Beads.initialize(root)
        return True

    def refresh(self, name):
        """Vorhandenes Projekt wiederverwenden, ohne Arbeitsstände zu überschreiben."""
        record = self.get(name)
        if record is None:
            raise ValueError("Projekt ist nicht eingetragen")
        root = Path(record["root"])
        if not root.is_dir():
            raise ValueError("Projektverzeichnis fehlt")
        fetch_error = None
        try:
            git(
                root,
                "-c",
                "credential.helper=",
                "fetch",
                "--prune",
                "--quiet",
                "origin",
            )
        except Exception:
            fetch_error = "Git-Aktualisierung fehlgeschlagen; lokaler Stand bleibt"
        try:
            head = git(root, "rev-parse", "HEAD").strip()
            branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
        except Exception:
            head, branch = None, None
        return {
            "path": str(root),
            "project": record,
            "head": head,
            "branch": branch,
            "dirty": bool(
                git(
                    root, "status", "--porcelain", "--", ".", ":(exclude).beads"
                ).strip()
            ),
            "reused": True,
            "fetch_error": fetch_error,
        }

    def list(self):
        """Registrierte Projekte plus bestehende Beads-Verzeichnisse."""
        entries = {}
        for record in self.records().values():
            root = Path(record["root"])
            if not root.is_dir():
                continue
            entries[record["id"]] = {
                "id": record["id"],
                "repository": record.get("repository"),
                "path": str(root),
                "beads": (root / ".beads").is_dir(),
            }
        for path in sorted(self.settings.projects.iterdir()):
            if (
                not path.is_dir()
                or path.is_symlink()
                or path.name.startswith(".")
                or path.name in entries
                or not (path / ".beads").is_dir()
            ):
                continue
            entries[path.name] = {
                "id": path.name,
                "repository": None,
                "path": str(path),
                "beads": True,
            }
        return [entries[key] for key in sorted(entries)]


def link_beads(project, workspace):
    """Beads bleibt kanonisch: der Worktree verweist, statt eine zweite DB anzulegen.

    Ohne diesen Verweis löst `bd` im Worktree kein Projekt auf und kann dort einen
    zweiten Aufgabenbestand anlegen. Der Verweis wird über `info/exclude` aus dem
    Git-Status gehalten, damit der Worktree sauber bleibt.
    """
    source = Path(project) / ".beads"
    link = Path(workspace) / ".beads"
    if not source.is_dir() or link.exists() or link.is_symlink():
        return False
    exclude = Path(git(workspace, "rev-parse", "--git-path", "info/exclude").strip())
    if not exclude.is_absolute():
        exclude = Path(workspace) / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text() if exclude.exists() else ""
    if ".beads" not in existing.split():
        exclude.write_text(existing.rstrip("\n") + "\n.beads\n")
    link.symlink_to(source, target_is_directory=True)
    return True
