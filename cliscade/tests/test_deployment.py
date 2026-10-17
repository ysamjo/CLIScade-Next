import os
import subprocess
import sys
from pathlib import Path

import pytest
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


@pytest.mark.parametrize(
    "name,target_name",
    [("init-secrets.py", "runtime.env"), ("init-omniroute.py", "omniroute.env")],
)
def test_secret_initialization_is_private_and_never_overwrites(
    tmp_path, name, target_name
):
    script = tmp_path / name
    script.write_bytes((ROOT / "deploy" / name).read_bytes())
    subprocess.run([sys.executable, str(script)], check=True, capture_output=True)
    target = tmp_path / target_name
    initial = target.read_bytes()
    assert os.stat(target).st_mode & 0o777 == 0o600
    result = subprocess.run([sys.executable, str(script)], capture_output=True)
    assert result.returncode != 0
    assert target.read_bytes() == initial


def test_omniroute_is_separate_private_service_with_persistent_state():
    source = (ROOT / "deploy/docker-compose.omniroute.yml").read_text()
    services = yaml.safe_load(source)["services"]
    assert set(services) == {"omniroute"}
    gateway = services["omniroute"]
    assert "@sha256:" in gateway["image"]
    assert "build" not in gateway
    assert gateway["ports"] == ["127.0.0.1:20128:20128"]
    assert gateway["environment"]["REQUIRE_API_KEY"] == "true"
    assert gateway["volumes"] == ["/DATA/AppData/cliscade-next/omniroute:/app/data"]
    assert "$" not in source and "docker.sock" not in source
