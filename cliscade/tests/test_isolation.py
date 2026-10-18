"""Ein Worktree ist keine Dateisystemgrenze — die Prüfung macht das sichtbar."""

import subprocess
from pathlib import Path

from cliscade_next import isolation


def _repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    (path / "readme.md").write_text("start\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "start",
        ],
        cwd=path,
        check=True,
    )
    return path


def test_snapshot_ignores_hidden_and_non_repo_dirs(tmp_path):
    root = tmp_path / "projects"
    _repo(root / "alpha")
    (root / ".cliscade-worktrees").mkdir()
    (root / "plain").mkdir()
    states = isolation.snapshot(root)
    assert set(states) == {"alpha"}
    assert states["alpha"]["status"] == []


def test_unrelated_change_is_a_violation(tmp_path):
    root = tmp_path / "projects"
    alpha = _repo(root / "alpha")
    beta = _repo(root / "beta")
    before = isolation.snapshot(root)
    (beta / "leak.txt").write_text("fremd\n")
    result = isolation.check(before, isolation.snapshot(root))
    assert result["ok"] is False
    assert result["changed_projects"] == ["beta"]
    assert alpha.name == "alpha"


def test_change_inside_worktree_only_is_clean(tmp_path):
    root = tmp_path / "projects"
    project = _repo(root / "alpha")
    worktree = root / ".cliscade-worktrees" / "run1"
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "cliscade/x", str(worktree), "HEAD"],
        cwd=project,
        check=True,
    )
    before = isolation.snapshot(root)
    (worktree / "result.txt").write_text("ok\n")
    result = isolation.check(before, isolation.snapshot(root))
    assert result["ok"] is True
    assert result["changed_projects"] == []


def test_new_project_is_not_a_violation(tmp_path):
    root = tmp_path / "projects"
    _repo(root / "alpha")
    before = isolation.snapshot(root)
    _repo(root / "gamma")
    result = isolation.check(before, isolation.snapshot(root))
    assert result["ok"] is True
