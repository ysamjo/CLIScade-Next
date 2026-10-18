import subprocess
from pathlib import Path

import pytest

from cliscade_next.config import Settings
from cliscade_next.projects import Projects, link_beads


def git_repository(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=Test",
            "commit",
            "--allow-empty",
            "-qm",
            "Start",
        ],
        check=True,
    )


@pytest.fixture
def projects(tmp_path):
    settings = Settings(
        tmp_path / "projects", tmp_path / "state", "http://server", "session-key"
    )
    settings.projects.mkdir()
    return Projects(settings)


def test_project_id_is_derived_from_the_repository_and_stays_stable(projects):
    assert projects.project_id("owner/repo") == "owner--repo"
    assert projects.root("owner/repo") == projects.settings.projects / "owner--repo"
    with pytest.raises(ValueError):
        projects.project_id("repo-without-owner")


def test_registering_the_same_repository_twice_keeps_one_project(projects):
    root = projects.root("owner/repo")
    root.mkdir()
    first = projects.register("owner/repo", root)
    second = projects.register("owner/repo", root, default_branch="develop")
    assert first == second
    assert projects.get("owner/repo")["default_branch"] == "main"
    assert len(projects.records()) == 1


def test_list_shows_registered_and_existing_beads_projects_without_phantoms(projects):
    root = projects.root("owner/repo")
    (root / ".beads").mkdir(parents=True)
    projects.register("owner/repo", root)
    (projects.settings.projects / "smoke" / ".beads").mkdir(parents=True)
    (projects.settings.projects / "phantom").mkdir()
    listed = projects.list()
    assert [item["id"] for item in listed] == ["owner--repo", "smoke"]
    assert all(item["beads"] for item in listed)
    assert all(item["repository"] == "owner/repo" for item in listed[:1])


def test_worktree_reuses_the_canonical_beads_list_and_stays_clean(projects, tmp_path):
    root = projects.root("owner/repo")
    git_repository(root)
    (root / ".beads").mkdir()
    worktree = tmp_path / "worktree"
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            "-b",
            "cliscade/cn-1",
            "-q",
            str(worktree),
            "HEAD",
        ],
        check=True,
    )
    assert link_beads(root, worktree) is True
    link = Path(worktree) / ".beads"
    assert link.is_symlink()
    assert link.resolve() == (root / ".beads").resolve()
    status = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert status.strip() == ""
    assert link_beads(root, worktree) is False


def test_worktree_without_beads_project_gets_no_link(projects, tmp_path):
    root = projects.root("owner/repo")
    git_repository(root)
    worktree = tmp_path / "worktree"
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            "-b",
            "cliscade/cn-2",
            "-q",
            str(worktree),
            "HEAD",
        ],
        check=True,
    )
    assert link_beads(root, worktree) is False
    assert not (Path(worktree) / ".beads").exists()


def test_refresh_reuses_the_existing_root_instead_of_cloning_again(projects):
    root = projects.root("owner/repo")
    git_repository(root)
    projects.register("owner/repo", root)
    prepared = projects.refresh("owner/repo")
    assert prepared["path"] == str(root)
    assert prepared["reused"] is True
    assert prepared["dirty"] is False
    assert prepared["head"]
