import shutil
import subprocess

import pytest

from cliscade_next.backup import backup
from cliscade_next.beads import Beads


@pytest.mark.skipif(not shutil.which("bd"), reason="Native Beads-CLI fehlt")
def test_native_backup_restores_canonical_tasks_and_memories(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    Beads.initialize(project)
    task = Beads(project).create(
        "Sicherung prüfen", acceptance="Wiederherstellung passt"
    )
    result = backup(project, tmp_path / "state")
    assert result["restore_verified"] is True
    assert result["tasks"] == 1
    assert len(result["sha256"]) == 64
    assert Beads(project).show(task["id"])["title"] == "Sicherung prüfen"
