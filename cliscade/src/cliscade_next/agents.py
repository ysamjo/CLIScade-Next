"""ACP-Integration ausschließlich über den offiziellen OpenHands-Client."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from openhands.sdk import RemoteConversation
from openhands.sdk.agent import ACPAgent
from openhands.sdk.settings.acp_providers import ACP_PROVIDERS
from openhands.sdk.workspace import RemoteWorkspace


@dataclass(frozen=True)
class Agent:
    id: str
    command: tuple[str, ...]
    model: str | None = None


def registry():
    agents = {
        key: Agent(key, tuple(ACP_PROVIDERS[key].default_command))
        for key in ("codex", "claude-code", "opencode")
    }
    agents["kiro"] = Agent("kiro", ("kiro-cli", "acp"))
    return agents


class OpenHands:
    def __init__(self, settings):
        self.settings = settings

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
                        acp_command=list(agent.command), acp_model=agent.model
                    ),
                    workspace=remote,
                    visualizer=None,
                    delete_on_close=False,
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
