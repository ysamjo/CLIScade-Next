"""ACP-Integration ausschließlich über den offiziellen OpenHands-Client."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from openhands.sdk import RemoteConversation
from openhands.sdk.agent import ACPAgent
from openhands.sdk.agent.acp_models import ACPModelDiscovery
from openhands.sdk.secret import LookupSecret
from openhands.sdk.settings.acp_providers import ACP_PROVIDERS
from openhands.sdk.settings.model import ACPAgentSettings
from openhands.sdk.workspace import RemoteWorkspace


@dataclass(frozen=True)
class Agent:
    id: str
    command: tuple[str, ...]
    model: str | None = None
    priority: int = 10
    capabilities: tuple[str, ...] = ("coding", "review")
    enabled: bool = True


def registry():
    agents = {
        key: Agent(key, tuple(ACP_PROVIDERS[key].default_command))
        for key in ("codex", "claude-code", "opencode")
    }
    agents["kiro"] = Agent("kiro", ("kiro-cli", "acp"))
    config = os.environ.get("CLISCADE_AGENT_CONFIG")
    if config:
        policies = json.loads(Path(config).read_text())
        for key, policy in policies.items():
            if key not in agents or policy.keys() - {
                "model",
                "priority",
                "capabilities",
                "enabled",
            }:
                raise ValueError("Unbekannte ACP-Route oder ungültige Registry-Felder")
            model = policy.get("model")
            priority = policy.get("priority", 10)
            enabled = policy.get("enabled", True)
            capabilities = policy.get("capabilities", ["coding", "review"])
            if (
                model is not None
                and not isinstance(model, str)
                or type(priority) is not int
                or type(enabled) is not bool
                or not isinstance(capabilities, list)
                or any(
                    value not in ("coding", "review", "analysis")
                    for value in capabilities
                )
            ):
                raise ValueError("Ungültige ACP-Routenkonfiguration")
            agents[key] = Agent(
                key, agents[key].command, model, priority, tuple(capabilities), enabled
            )
    return agents


class OpenHands:
    def __init__(self, settings):
        self.settings = settings

    def secrets(self, workspace, agent):
        provider = ACP_PROVIDERS.get(agent.id)
        if provider is None:
            return {}
        allowed = {provider.api_key_env_var, provider.base_url_env_var}
        allowed.update(spec.secret_name for spec in provider.file_secrets)
        response = workspace.client.get("/api/settings/secrets")
        response.raise_for_status()
        return {
            secret["name"]: LookupSecret(
                url=f"{self.settings.agent_server.rstrip('/')}/api/settings/secrets/"
                f"{quote(secret['name'], safe='')}",
                headers={"X-Session-API-Key": self.settings.api_key},
            )
            for secret in response.json()["secrets"]
            if secret["name"] in allowed
        }

    def probe(self, agent: Agent):
        workspace = RemoteWorkspace(
            host=self.settings.agent_server,
            working_dir=str(self.settings.projects),
            api_key=self.settings.api_key,
        )
        try:
            settings = ACPAgentSettings(
                acp_server=agent.id if agent.id in ACP_PROVIDERS else "custom",
                acp_command=list(agent.command),
                acp_startup_timeout=45,
            )
            response = workspace.client.post(
                "/api/acp/models",
                json={
                    "agent_settings": settings.model_dump(mode="json"),
                    "secrets": {
                        name: secret.model_dump(mode="json")
                        for name, secret in self.secrets(workspace, agent).items()
                    },
                },
                timeout=180,
            )
            response.raise_for_status()
            return ACPModelDiscovery.model_validate(response.json()).model_dump(
                mode="json"
            )
        finally:
            workspace.client.close()

    def attach(self, agent: Agent, workspace: Path, session_id=None):
        remote = RemoteWorkspace(
            host=self.settings.agent_server,
            working_dir=str(workspace),
            api_key=self.settings.api_key,
        )
        try:
            conversation = (
                RemoteConversation.attach(
                    workspace=remote,
                    conversation_id=UUID(session_id),
                    visualizer=None,
                )
                if session_id
                else RemoteConversation(
                    agent=ACPAgent(
                        acp_command=list(agent.command),
                        acp_model=agent.model,
                        acp_server=agent.id if agent.id in ACP_PROVIDERS else None,
                        acp_file_secrets=list(ACP_PROVIDERS[agent.id].file_secrets)
                        if agent.id in ACP_PROVIDERS
                        else [],
                    ),
                    workspace=remote,
                    visualizer=None,
                    delete_on_close=False,
                    secrets=self.secrets(remote, agent),
                    tags={"cliscade": "v1", "agent": agent.id},
                )
            )
        except BaseException:
            remote.client.close()
            raise
        return Session(conversation, remote)


class Session:
    def __init__(self, conversation, workspace):
        self.conversation = conversation
        self.workspace = workspace
        self.id = str(conversation.id)

    def submit(self, prompt):
        self.conversation.send_message(prompt)
        self.conversation.run(blocking=False)

    def state(self):
        state = self.conversation.state
        return {
            "status": str(state.execution_status.value),
            "events": [event.model_dump(mode="json") for event in state.events],
        }

    def cancel(self):
        self.conversation.interrupt()

    def close(self):
        self.conversation.close()
        self.workspace.client.close()
