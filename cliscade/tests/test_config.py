from pathlib import Path

import pytest

from cliscade_next.config import Settings


def test_project_must_be_inside_configured_root(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    settings = Settings(tmp_path, tmp_path / "state", "http://localhost:8000", "key")
    assert settings.project("project") == project
    with pytest.raises(ValueError):
        settings.project("../outside")
    with pytest.raises(ValueError):
        settings.project(str(Path.home()))


def test_project_symlink_cannot_escape_root(tmp_path):
    (tmp_path / "escape").symlink_to(Path.home(), target_is_directory=True)
    settings = Settings(tmp_path, tmp_path / "state", "http://localhost:8000", "key")
    with pytest.raises(ValueError):
        settings.project("escape")
