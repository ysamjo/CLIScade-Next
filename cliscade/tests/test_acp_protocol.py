import sys
from pathlib import Path

from openhands.sdk import Conversation
from openhands.sdk.agent import ACPAgent

from cliscade_next.orchestrator import evidence


def test_official_sdk_executes_stdio_acp_and_preserves_real_tool_receipt(tmp_path):
    agent = ACPAgent(
        acp_command=[sys.executable, str(Path(__file__).with_name("acp_fixture.py"))]
    )
    try:
        conversation = Conversation(
            agent=agent,
            workspace=str(tmp_path),
            persistence_dir=str(tmp_path / "state"),
            visualizer=None,
        )
        conversation.send_message("Kontrollierte Protokollprüfung")
        conversation.run()
        events = [event.model_dump(mode="json") for event in conversation.state.events]
        checks, claims = evidence(events)
        assert checks[0]["exit_code"] == 0
        assert checks[0]["independently_reproduced"] is False
        assert claims
        assert list(tmp_path.glob("acp-*.txt"))
    finally:
        agent.close()
