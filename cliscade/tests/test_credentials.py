from types import SimpleNamespace

import httpx

from cliscade_next.agents import Agent, OpenHands


def test_only_provider_secret_references_are_forwarded_without_reading_values():
    paths = []

    def handle(request):
        paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "secrets": [
                    {"name": "ANTHROPIC_API_KEY"},
                    {"name": "UNRELATED_DATABASE_PASSWORD"},
                ]
            },
        )

    with httpx.Client(
        base_url="http://server", transport=httpx.MockTransport(handle)
    ) as client:
        runner = OpenHands(
            SimpleNamespace(agent_server="http://server", api_key="test-key")
        )
        secrets = runner.secrets(
            SimpleNamespace(client=client), Agent("claude-code", ("acp",))
        )
        assert set(secrets) == {"ANTHROPIC_API_KEY"}
        assert (
            secrets["ANTHROPIC_API_KEY"].url
            == "http://server/api/settings/secrets/ANTHROPIC_API_KEY"
        )
        assert paths == ["/api/settings/secrets"]
