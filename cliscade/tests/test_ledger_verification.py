"""Belegprüfung: `completed` allein zählt nicht, Spuren im Arbeitsbaum schon."""

from cliscade_next.ledger import Ledger


def _finish(ledger, attempt, checkpoint, error=None):
    ledger.update(
        attempt["id"],
        status="completed",
        checkpoint=checkpoint,
        error=error,
    )


def test_verified_agents_counts_commands_and_worktree_changes(tmp_path):
    ledger = Ledger(tmp_path / "state")
    with_checks = ledger.create(
        "p", "t1", "openhands", tmp_path / "w1", model="openai/c1"
    )
    _finish(
        ledger,
        with_checks,
        {
            "git": {"status": ""},
            "verified_checks": [{"command": "ls", "exit_code": 0}],
        },
    )
    acp_change = ledger.create(
        "p", "t2", "opencode", tmp_path / "w2", model="opencode/big-pickle"
    )
    _finish(
        ledger, acp_change, {"git": {"status": "?? new.txt"}, "verified_checks": []}
    )
    silent = ledger.create("p", "t3", "codex", tmp_path / "w3")
    _finish(ledger, silent, {"git": {"status": ""}, "verified_checks": []})
    failed = ledger.create("p", "t4", "codex", tmp_path / "w4")
    _finish(
        ledger,
        failed,
        {"git": {"status": "?? x"}, "verified_checks": []},
        error="abort",
    )

    verified = ledger.verified_agents()

    assert set(verified) == {"openhands", "opencode"}
    assert verified["openhands"] == {"runs": 1, "models": ["openai/c1"]}
    assert verified["opencode"] == {"runs": 1, "models": ["opencode/big-pickle"]}


def test_verified_agents_skips_runs_that_touched_another_project(tmp_path):
    ledger = Ledger(tmp_path / "state")
    leaked = ledger.create("p", "t1", "opencode", tmp_path / "w1", model="m")
    _finish(
        ledger,
        leaked,
        {
            "git": {"status": "?? new.txt"},
            "verified_checks": [],
            "isolation": {"ok": False, "changed_projects": ["other"]},
        },
    )
    clean = ledger.create("p", "t2", "opencode", tmp_path / "w2", model="m")
    _finish(
        ledger,
        clean,
        {
            "git": {"status": "?? new.txt"},
            "verified_checks": [],
            "isolation": {"ok": True, "changed_projects": []},
        },
    )

    verified = ledger.verified_agents()

    assert verified["opencode"] == {"runs": 1, "models": ["m"]}
