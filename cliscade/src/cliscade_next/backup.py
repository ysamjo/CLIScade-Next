"""Native Beads-Sicherung mit Wiederherstellungsprüfung in einem Wegwerfprojekt."""

import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from uuid import uuid4

from filelock import FileLock


def command(project, *args, parse=False):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("BEADS_", "BD_"))
    }
    env["BEADS_DIR"] = str(project / ".beads")
    result = subprocess.run(
        ["bd", *args, "--sandbox"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Native Beads-Sicherung fehlgeschlagen; bd doctor prüfen")
    return json.loads(result.stdout) if parse else result.stdout


def contents(project):
    return {
        "tasks": sorted(
            command(
                project,
                "list",
                "--all",
                "--limit",
                "0",
                "--json",
                "--readonly",
                parse=True,
            ),
            key=lambda item: item["id"],
        ),
        "memories": command(project, "memories", "--json", "--readonly", parse=True),
    }


def backup(project: Path, state: Path):
    if not (project / ".beads").is_dir() or (project / ".beads").is_symlink():
        raise ValueError("Beads ist im Projekt nicht eingerichtet")
    identity = str(uuid4())
    target = state / "backups" / identity
    target.mkdir(parents=True, mode=0o700)
    native = target / "native"
    with FileLock(str(project / ".beads/cliscade.lock"), timeout=30):
        command(project, "backup", "init", str(native))
        command(project, "backup", "sync")
        expected = contents(project)
        with tempfile.TemporaryDirectory(prefix="cliscade-restore-") as directory:
            restored = Path(directory)
            command(
                restored,
                "init",
                "--non-interactive",
                "--prefix",
                "restore",
                "--skip-agents",
                "--skip-hooks",
            )
            command(restored, "backup", "restore", str(native), "--force")
            if contents(restored) != expected:
                raise RuntimeError(
                    "Wiederherstellungsprüfung der Beads-Sicherung fehlgeschlagen"
                )
        archive = target / "beads.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(native, arcname="native")
        archive.chmod(0o600)
        with archive.open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
        receipt = {
            "id": identity,
            "sha256": checksum,
            "tasks": len(expected["tasks"]),
            "restore_verified": True,
        }
        (target / "receipt.json").write_text(json.dumps(receipt))
    return receipt
