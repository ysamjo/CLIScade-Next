"""Eine verlassene Behauptung darf einen Lauf nicht für immer blockieren."""

from pathlib import Path

import pytest

from cliscade_next.beads import Beads


class FlakyBeads(Beads):
    """Beads mit festem Aufrufplan, echte bd-Befehle laufen nicht."""

    def __init__(self, plan, project_path=None):
        self.plan = list(plan)
        self.calls = []
        self.project = project_path or Path("/projekt")
        self.directory = self.project / ".beads"

    def call(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        action = self.plan.pop(0) if self.plan else {"ok": True}
        if isinstance(action, Exception):
            raise action
        return action


def _held():
    return RuntimeError(
        "Beads-Zugriff fehlgeschlagen; bd doctor prüfen — "
        'cannot reassign cn-1: held by "opencode" (in_progress)'
    )


def test_stale_claim_is_reclaimed_then_overridden():
    beads = FlakyBeads([_held(), {"reclaimed": 0}, {"ok": True}])
    result = beads.assign("cn-1", "agent-b", allow_stale_claim=True)
    assert result == {"ok": True}
    reclaim = [call for call in beads.calls if call[0][0] == "reclaim"]
    assert reclaim, "vor dem Erzwingen wird der Reaper bemüht"
    assert "--any-replica" in reclaim[0][0]
    assert beads.calls[-1][0][-1] == "--force"


def test_live_claim_without_permission_blocks():
    beads = FlakyBeads([_held()])
    with pytest.raises(RuntimeError, match="held by"):
        beads.assign("cn-1", "agent-b")
    assert len(beads.calls) == 1, "ohne Erlaubnis kein Überschreiben"


def test_claim_error_names_the_holder():
    beads = FlakyBeads([_held()])
    with pytest.raises(RuntimeError) as err:
        beads.assign("cn-1", "agent-b")
    assert "opencode" in str(err.value)


def test_reclaim_falls_back_without_any_replica():
    beads = FlakyBeads(
        [
            RuntimeError(
                "Beads-Zugriff fehlgeschlagen; bd doctor prüfen — "
                "unknown flag: --any-replica"
            ),
            {"reclaimed": 1},
        ]
    )
    beads.reclaim()
    assert all("--any-replica" not in call[0] for call in beads.calls[1:])
