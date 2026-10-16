import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_zimaos_compose_keeps_daemon_and_credentials_private():
    source = (ROOT / "deploy/docker-compose.yml").read_text()
    compose = yaml.safe_load(source)
    assert "$" not in source and "docker.sock" not in source
    for service in compose["services"].values():
        assert "image" in service and "build" not in service
    assert compose["services"]["canvas"]["ports"] == ["127.0.0.1:8740:8000"]
    assert compose["x-casaos"]["port_map"] == "8740"
    assert all(
        "ports" not in compose["services"][name]
        for name in ("cliscade", "automation", "agent-server")
    )


def test_secret_initialization_is_private_and_never_overwrites(tmp_path):
    script = tmp_path / "init-secrets.py"
    script.write_bytes((ROOT / "deploy/init-secrets.py").read_bytes())
    subprocess.run([sys.executable, str(script)], check=True, capture_output=True)
    target = tmp_path / "runtime.env"
    initial = target.read_bytes()
    assert os.stat(target).st_mode & 0o777 == 0o600
    result = subprocess.run([sys.executable, str(script)], capture_output=True)
    assert result.returncode != 0
    assert target.read_bytes() == initial
