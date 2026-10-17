import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from cliscade_next.config import Settings
from cliscade_next.repositories import RepositoryWorkspaces


@pytest.fixture
def repositories(tmp_path, monkeypatch):
    settings = Settings(
        tmp_path / "projects", tmp_path / "state", "http://server", "session-key"
    )
    calls = []
    clones = []
    repos = [
        {
            "id": "1",
            "full_name": "owner/recent",
            "main_branch": "main",
            "git_provider": "github",
        },
        {
            "id": "2",
            "full_name": "owner/other",
            "main_branch": "main",
            "git_provider": "github",
        },
    ]

    def handler(request):
        calls.append(request)
        if request.url.path == "/api/settings/secrets":
            if request.method == "GET":
                return httpx.Response(
                    200, json={"secrets": [{"name": "GITHUB_PERSONAL_ACCESS_TOKEN"}]}
                )
            return httpx.Response(200, json={})
        if request.url.path.endswith("/GITHUB_PERSONAL_ACCESS_TOKEN"):
            return httpx.Response(200, text="private-token")
        return httpx.Response(200, json={"items": repos})

    class Workspace:
        def __init__(self):
            self.client = httpx.Client(
                base_url="http://server", transport=httpx.MockTransport(handler)
            )

        def clone_repos(self, sources, target_dir):
            clones.append(sources)
            path = Path(target_dir) / "repo"
            path.mkdir()
            subprocess.run(["git", "init", "-q", str(path)], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(path),
                    "remote",
                    "add",
                    "origin",
                    "https://private-token@github.com/owner/recent",
                ],
                check=True,
            )
            return SimpleNamespace(
                success_count=1,
                failed_repos=[],
                repo_mappings={"repo": SimpleNamespace(local_path=str(path))},
            )

    service = RepositoryWorkspaces(settings)
    monkeypatch.setattr(service, "workspace", Workspace)
    return service, calls, clones


def test_catalog_uses_pat_alias_without_exposing_value_and_remembers_workspace(
    repositories,
):
    service, calls, clones = repositories
    catalog = service.catalog()
    assert "private-token" not in json.dumps(catalog)
    alias = next(request for request in calls if request.method == "PUT")
    assert json.loads(alias.content)["name"] == "github_token"
    assert json.loads(alias.content)["value"] == "private-token"
    first = service.prepare("owner/other")
    second = service.prepare("owner/other")
    assert first["path"] != second["path"]
    assert service.catalog()["repositories"][0]["full_name"] == "owner/other"
    assert service.preference() == {
        "selected": "owner/other",
        "recent": ["owner/other"],
    }
    assert clones[0] == [{"url": "https://github.com/owner/other", "ref": "main"}]
    config = (Path(first["path"]) / ".git/config").read_text()
    assert "private-token" not in config
    assert "https://github.com/owner/other" in config
    assert "credential" in config and "github_token" in config


@pytest.mark.parametrize(
    "name",
    [
        "../../private",
        "file:///tmp/repo",
        "owner/..",
        "-x/repo;cmd",
        "owner/not-authorized",
    ],
)
def test_unavailable_or_invalid_repositories_are_not_cloned(repositories, name):
    service, _, clones = repositories
    with pytest.raises(ValueError):
        service.prepare(name)
    assert clones == []
    assert not service.path.exists()


def test_git_helper_does_not_request_github_credentials_for_another_host(repositories):
    service, _, _ = repositories
    prepared = service.prepare("owner/recent")
    import os

    result = subprocess.run(
        ["git", "-C", prepared["path"], "credential", "fill"],
        input="protocol=https\nhost=untrusted.example\n\n",
        text=True,
        capture_output=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    assert result.returncode != 0
    assert "private-token" not in result.stdout + result.stderr
