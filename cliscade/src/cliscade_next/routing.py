"""Prioritäten und sicherer Fallback vor der ersten Prompt-Übermittlung."""

import json
import time
from dataclasses import asdict

from filelock import FileLock

from cliscade_next.orchestrator import Orchestrator


class Routing:
    def __init__(self, service: Orchestrator):
        self.service = service
        self.path = service.settings.state / "agent-probes.json"

    def probe(self, agent_id):
        if agent_id not in self.service.agents:
            raise ValueError("ACP-Agent ist nicht freigegeben")
        agent = self.service.agents[agent_id]
        result = self.service.runner.probe(agent)
        record = {**asdict(agent), "discovery": result, "checked_at": time.time()}
        self.service.settings.state.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.path) + ".lock", timeout=30):
            data = json.loads(self.path.read_text()) if self.path.exists() else {}
            data[agent_id] = record
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(data))
            temp.replace(self.path)
        return record

    def start(self, project_name, task_id, capability="coding", source_id=None):
        skipped = []
        for agent in sorted(
            self.service.agents.values(), key=lambda item: (item.priority, item.id)
        ):
            if not agent.enabled or capability not in agent.capabilities:
                skipped.append({"agent": agent.id, "reason": "disabled_or_capability"})
                continue
            try:
                discovery = self.probe(agent.id)["discovery"]
            except Exception:
                skipped.append({"agent": agent.id, "reason": "discovery_unavailable"})
                continue
            if discovery.get("error"):
                skipped.append(
                    {"agent": agent.id, "reason": discovery["error"]["code"]}
                )
                continue
            models = {
                model["model_id"] for model in discovery.get("available_models", [])
            }
            effective_model = agent.model or discovery.get("current_model_id")
            if effective_model and models and effective_model not in models:
                skipped.append(
                    {"agent": agent.id, "reason": "configured_model_unavailable"}
                )
                continue
            attempt = self.service.start(
                project_name, task_id, agent.id, source_id=source_id
            )
            attempt = self.service.ledger.update(attempt["id"], route_trace=skipped)
            return {
                "attempt": attempt,
                "skipped": skipped,
                "fallback": bool(skipped),
                "replayed_after_prompt": False,
            }
        return {
            "attempt": None,
            "skipped": skipped,
            "fallback": bool(skipped),
            "replayed_after_prompt": False,
        }
