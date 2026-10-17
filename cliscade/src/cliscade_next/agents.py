"""ACP und nativer OpenHands-Harness über den offiziellen SDK-Client."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx
from openhands.sdk import LLM, OpenHandsAgentSettings, RemoteConversation
from openhands.sdk.agent import ACPAgent
from openhands.sdk.agent.acp_models import ACPModelDiscovery
from openhands.sdk.context import AgentContext
from openhands.sdk.secret import LookupSecret
from openhands.sdk.settings.acp_providers import ACP_PROVIDERS
from openhands.sdk.settings.model import ACPAgentSettings
from openhands.sdk.workspace import RemoteWorkspace

from cliscade_next.native_agents import ACP_ACCOUNT_COMMANDS


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
    agents["antigravity"] = Agent(
        "antigravity",
        ACP_ACCOUNT_COMMANDS["antigravity"],
        priority=1,
    )
    agents["codebuddy"] = Agent(
        "codebuddy", ACP_ACCOUNT_COMMANDS["codebuddy"], priority=2
    )
    agents["openhands"] = Agent("openhands", (), model="openai/c1", priority=50)
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
            model = policy.get("model", agents[key].model)
            priority = policy.get("priority", agents[key].priority)
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

    def native_profile(self, workspace):
        try:
            response = workspace.client.get(
                "/api/profiles/OmniRoute", headers={"X-Expose-Secrets": "plaintext"}
            )
            response.raise_for_status()
            llm = LLM.model_validate(response.json()["config"])
            url = urlsplit(llm.base_url or "")
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError("Ungültige Gateway-Adresse")
            return llm
        except (httpx.HTTPError, ValueError, KeyError):
            raise RuntimeError(
                "OpenHands benötigt das gespeicherte OmniRoute-Modellprofil."
            ) from None

    def native_discovery(self, workspace, agent):
        llm = self.native_profile(workspace)
        try:
            with httpx.Client(timeout=30, trust_env=False) as client:
                response = client.get(
                    f"{llm.base_url.rstrip('/')}/models",
                    headers={
                        "Authorization": f"Bearer {llm.api_key.get_secret_value()}"
                        if llm.api_key
                        else ""
                    },
                )
                response.raise_for_status()
                models = sorted(
                    {
                        "openai/" + item["id"]
                        for item in response.json()["data"]
                        if isinstance(item.get("id"), str) and item["id"]
                    }
                )
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise RuntimeError("OmniRoute-Modellkatalog nicht verfügbar.") from None
        return {
            "available_models": [{"model_id": model} for model in models],
            "current_model_id": agent.model or llm.model,
            "error": None,
        }

    def native_agent(self, workspace, agent):
        llm = self.native_profile(workspace)
        if agent.model:
            llm = llm.model_copy(update={"model": agent.model})
        return OpenHandsAgentSettings(
            llm=llm,
            agent_context=AgentContext(
                system_message_suffix=(
                    "Verbindliches Arbeitsverzeichnis für diesen Beads-Run: "
                    f"{workspace.working_dir}. Bearbeite ausschließlich diesen "
                    "Ausführungs-Worktree. Andere Projektpfade im Beads-Kontext "
                    "sind Herkunftsangaben, keine Arbeitsziele. Aufgabe und AGENTS.md "
                    "bestimmen, ob Commit/Push erlaubt sind. Bei ausdrücklichem "
                    "Verbot weder committen noch pushen."
                )
            ),
        ).create_agent()

    def save_account(self, provider, home):
        if provider != "codex":
            return
        # The server's versioned credential store owns Codex token refresh.
        workspace = RemoteWorkspace(
            host=self.settings.agent_server,
            working_dir=str(self.settings.projects),
            api_key=self.settings.api_key,
        )
        try:
            response = workspace.client.put(
                "/api/settings/secrets",
                json={
                    "name": "CODEX_AUTH_JSON",
                    "value": (home / ".codex/auth.json").read_text(),
                },
            )
            response.raise_for_status()
        except Exception as error:
            raise RuntimeError(
                "Kontoanmeldung konnte nicht im Agent Server gespeichert werden"
            ) from error
        finally:
            workspace.client.close()

    def secrets(self, workspace, agent):
        home = os.environ.get("CLISCADE_LOGIN_HOME")
        if home and (Path(home) / ".cliscade-accounts" / agent.id).is_file():
            return {}
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
            if agent.id == "openhands":
                return self.native_discovery(workspace, agent)
            settings = ACPAgentSettings(
                acp_server=agent.id if agent.id in ACP_PROVIDERS else "custom",
                acp_command=list(agent.command),
                acp_startup_timeout=45,
                acp_auth_method="oauth-personal" if agent.id == "antigravity" else None,
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
                    agent=self.native_agent(remote, agent)
                    if agent.id == "openhands"
                    else ACPAgent(
                        acp_command=list(agent.command),
                        acp_model=agent.model,
                        acp_auth_method="oauth-personal"
                        if agent.id == "antigravity"
                        else None,
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
        events = [event.model_dump(mode="json") for event in state.events]
        info = state.refresh_from_server()
        return {
            "status": info["execution_status"],
            "events": events,
        }

    def cancel(self):
        self.conversation.interrupt()

    def close(self):
        self.conversation.close()
        self.workspace.client.close()
