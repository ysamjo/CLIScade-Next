"""GitHub-Auswahl und persistente Workspace-Vorgabe für Canvas."""

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import httpx
from filelock import FileLock
from openhands.sdk.workspace import RemoteWorkspace

from cliscade_next.projects import Projects


class RepositoryWorkspaces:
    def __init__(self, settings):
        self.settings = settings
        settings.state.mkdir(parents=True, exist_ok=True)
        self.path = settings.state / "repository-workspaces.json"
        self.lock = FileLock(str(self.path) + ".lock")

    def workspace(self):
        return RemoteWorkspace(
            host=self.settings.agent_server,
            working_dir=str(self.settings.projects),
            api_key=self.settings.api_key,
        )

    def preference(self):
        with self.lock:
            return json.loads(self.path.read_text()) if self.path.exists() else {}

    def catalog(self):
        workspace = self.workspace()
        try:
            response = workspace.client.get("/api/settings/secrets")
            response.raise_for_status()
            names = {item["name"] for item in response.json()["secrets"]}
            if "github_token" not in names:
                source = next(
                    (
                        name
                        for name in (
                            "GITHUB_PERSONAL_ACCESS_TOKEN",
                            "GITHUB_TOKEN",
                            "GH_TOKEN",
                            "github",
                        )
                        if name in names
                    ),
                    None,
                )
                if source is None:
                    raise ValueError("GitHub-PAT in den OpenHands-Secrets hinterlegen.")
                token = workspace.client.get(f"/api/settings/secrets/{source}")
                token.raise_for_status()
                saved = workspace.client.put(
                    "/api/settings/secrets",
                    json={
                        "name": "github_token",
                        "value": token.text,
                        "description": "GitHub-Zugang für Repository-Workspaces",
                    },
                )
                saved.raise_for_status()
            response = workspace.client.get(
                "/api/git/repositories/search",
                params={"provider": "github", "limit": 30},
            )
            response.raise_for_status()
            page = response.json()
            if page.get("missing_token"):
                raise ValueError(
                    "GitHub-PAT ist für die Repository-Auswahl nicht verfügbar."
                )
            prefs = self.preference()
            repos = page["items"]
            recent = prefs.get("recent", [])
            by_name = {repo["full_name"]: repo for repo in repos}
            ordered = [by_name.pop(name) for name in recent if name in by_name]
            ordered.extend(by_name.values())
            return {
                "repositories": ordered,
                "selected": prefs.get("selected"),
                "recent": recent,
            }
        except httpx.HTTPError:
            raise RuntimeError(
                "GitHub-Repository-Auswahl nicht verfügbar; PAT-Berechtigung prüfen."
            ) from None
        finally:
            workspace.client.close()

    def prepare(self, name):
        if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", name) or name.split("/")[
            1
        ] in (".", ".."):
            raise ValueError("GitHub-Repository im Format owner/repo wählen.")
        repo = next(
            (
                item
                for item in self.catalog()["repositories"]
                if item["full_name"] == name
            ),
            None,
        )
        if repo is None:
            raise ValueError(
                "Repository ist in der GitHub-Auswahl nicht mehr verfügbar."
            )
        projects = Projects(self.settings)
        existing = projects.get(name)
        if existing and Path(existing["root"]).is_dir():
            prepared = projects.refresh(name)
            self._remember(name)
            return prepared
        self.settings.projects.mkdir(parents=True, exist_ok=True)
        target = projects.root(name)
        if target.exists():
            raise RuntimeError(
                "Projektverzeichnis existiert ohne Eintrag; vor dem Klonen prüfen"
            )
        staging = self.settings.projects / ".imports" / uuid4().hex
        staging.mkdir(parents=True, mode=0o700)
        workspace = self.workspace()
        try:
            result = workspace.clone_repos(
                [{"url": f"https://github.com/{name}", "ref": repo["main_branch"]}],
                target_dir=staging,
            )
            if result.failed_repos or result.success_count != 1:
                raise RuntimeError(
                    "GitHub-Repository konnte nicht geklont werden; "
                    "PAT-Berechtigung prüfen."
                )
            clone = Path(next(iter(result.repo_mappings.values())).local_path)
            # Der SDK-Klonpfad speichert die authentifizierte URL als origin.
            # Nur die credential-freie URL darf den Workspace verlassen.
            clean_url = f"https://github.com/{name}"
            subprocess.run(
                ["git", "-C", str(clone), "remote", "set-url", "origin", clean_url],
                check=True,
                capture_output=True,
            )
            helper_code = (
                "import os,sys,urllib.request; "
                "sys.argv[-1]=='get' or sys.exit(0); "
                "fields=dict(line.strip().split('=',1) "
                "for line in sys.stdin if '=' in line); "
                "fields.get('host')=='github.com' or sys.exit(0); "
                "req=urllib.request.Request("
                "'http://127.0.0.1:8000/api/settings/secrets/github_token',"
                "headers={'X-Session-API-Key':os.environ['SESSION_API_KEY']}); "
                "token=urllib.request.urlopen(req,timeout=15).read().decode(); "
                "print('username=x-access-token\\npassword='+token+'\\n')"
            )
            helper = "!python -c " + shlex.quote(helper_code)
            subprocess.run(
                ["git", "-C", str(clone), "config", "credential.helper", helper],
                check=True,
                capture_output=True,
            )
            clone.rename(target)
        finally:
            workspace.client.close()
            shutil.rmtree(staging, ignore_errors=True)
        record = projects.register(name, target, repo["main_branch"])
        beads = True
        beads_error = None
        try:
            projects.ensure_beads(name)
        except Exception:
            beads = False
            beads_error = "Beads-Einrichtung fehlgeschlagen; bd doctor prüfen"
        self._remember(name)
        return {
            "path": str(target),
            "project": record,
            "repository": repo,
            "reused": False,
            "beads": beads,
            "beads_error": beads_error,
        }

    def _remember(self, name):
        with self.lock:
            prefs = json.loads(self.path.read_text()) if self.path.exists() else {}
            recent = [name] + [item for item in prefs.get("recent", []) if item != name]
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps({"selected": name, "recent": recent[:10]}))
            temp.replace(self.path)
