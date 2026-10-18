"""Kontrollierte Beads-/OpenHands-Dienste für Orchestrierungstests."""


class FakeBeads:
    def __init__(self, project):
        self.project = project

    def show(self, task_id):
        return {"id": task_id, "title": "Rechne", "acceptance_criteria": "Tests grün"}

    def context(self):
        return {"memories": {"rule": "Deutsche UI"}, "workflow": "bd ready"}

    def ensure_startable(self, task_id):
        return self.show(task_id)

    def update(self, task_id, **fields):
        return self.show(task_id) | fields

    def assign(self, task_id, agent_id, previous=None, allow_stale_claim=False):
        return self.show(task_id) | {"assignee": agent_id}


class FakeSession:
    def __init__(self, session_id, state):
        self.id, self.value = session_id, state

    def submit(self, prompt):
        self.value["prompt"] = prompt
        if self.value.get("fail_submit"):
            raise RuntimeError("Verbindung unterbrochen")
        self.value["status"] = "running"

    def state(self):
        return self.value

    def cancel(self):
        self.value["status"] = "paused"

    def close(self):
        pass


class FakeOpenHands:
    def __init__(self):
        self.sessions = {}
        self.fail_submit = False

    def attach(self, agent, workspace, session_id=None):
        session_id = session_id or str(len(self.sessions) + 1)
        state = self.sessions.setdefault(
            session_id,
            {
                "status": "idle",
                "events": [],
                "fail_submit": self.fail_submit,
            },
        )
        return FakeSession(session_id, state)
