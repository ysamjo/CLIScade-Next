import subprocess

import pytest
from helpers import FakeBeads, FakeOpenHands

from cliscade_next.agents import Agent
from cliscade_next.config import Settings
from cliscade_next.orchestrator import Orchestrator


@pytest.fixture
def system(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(project),
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
    settings = Settings(tmp_path, tmp_path / "state", "http://localhost:8000", "key")
    runner = FakeOpenHands()
    service = Orchestrator(
        settings,
        runner=runner,
        beads_factory=FakeBeads,
        agents={"one": Agent("one", ("one",)), "two": Agent("two", ("two",))},
        settle_seconds=0,
    )
    return service, runner, settings
