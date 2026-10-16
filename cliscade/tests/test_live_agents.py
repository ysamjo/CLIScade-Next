"""Opt-in Inferenztest mit vorhandener Anmeldung, ausschließlich Wegwerfdateien."""

import os

import pytest
from openhands.sdk import Conversation
from openhands.sdk.agent import ACPAgent

from cliscade_next.agents import registry


@pytest.mark.parametrize(
    "provider", ["kiro", "codex", "claude-code", "opencode", "antigravity", "codebuddy"]
)
def test_authenticated_acp_provider_writes_requested_file(tmp_path, provider):
    enabled = os.environ.get("CLISCADE_LIVE_AGENTS", "").split(",")
    if provider not in enabled:
        pytest.skip("Authentifizierter Anbieter-Test nicht angefordert")
    agent = ACPAgent(
        acp_command=list(registry()[provider].command),
        acp_startup_timeout=45,
        acp_auth_method="oauth-personal" if provider == "antigravity" else None,
        acp_prompt_timeout=90,
    )
    conversation = Conversation(
        agent=agent,
        workspace=str(tmp_path),
        persistence_dir=str(tmp_path / "session"),
        visualizer=None,
        max_iteration_per_run=5,
    )
    try:
        conversation.send_message(
            "Schreibe ausschließlich die Datei acp-proof.txt im aktuellen "
            f"Arbeitsverzeichnis mit genau dem Text ACP_OK_{provider}. "
            "Keine weiteren Änderungen und keine weiteren Aufgaben."
        )
        conversation.run()
        assert (tmp_path / "acp-proof.txt").read_text().strip() == f"ACP_OK_{provider}"
    finally:
        conversation.close()
        agent.close()
