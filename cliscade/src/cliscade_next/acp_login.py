"""Kontoanmeldung über ACP; keine Prompts, Tools oder Agenten-Ausführungen."""

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from acp import Client, spawn_agent_process
from acp.schema import CreateElicitationResponse

from cliscade_next.native_agents import ACP_ACCOUNT_COMMANDS

METHODS = {"antigravity": "oauth-personal", "codebuddy": "external"}


class LoginClient(Client):
    async def request_permission(self, **kwargs):
        raise ValueError("Werkzeugaufrufe sind bei der Kontoanmeldung nicht erlaubt")

    async def ext_method(self, method, params):
        raise ValueError("Unbekannte Anfrage während der Kontoanmeldung")

    async def create_elicitation(self, message, mode, **kwargs):
        return CreateElicitationResponse(action="decline")


async def account(agent_id, action):
    command = ACP_ACCOUNT_COMMANDS[agent_id]
    env = dict(os.environ)
    if action == "status" and agent_id == "antigravity":
        marker = Path.home() / ".cliscade-accounts" / agent_id
        if not marker.is_file():
            return False
        env["BROWSER"] = "/usr/bin/false"
    with tempfile.TemporaryDirectory(prefix="cliscade-auth-") as cwd:
        async with spawn_agent_process(
            LoginClient(),
            *command,
            env=env,
            cwd=cwd,
            transport_kwargs={"stderr": subprocess.DEVNULL},
        ) as (connection, process):
            response = await connection.initialize(protocol_version=1)
            methods = {method.id for method in response.auth_methods or []}
            method = METHODS[agent_id]
            if method not in methods:
                return False
            if agent_id == "codebuddy":
                info = await connection.ext_method("codebuddy.ai/getUserInfo", {})
                connected = bool((info.get("userInfo") or {}).get("userId"))
                if action == "status" or connected:
                    return connected
            await connection.authenticate(method_id=method)
            return True


def main():
    if (
        len(sys.argv) != 3
        or sys.argv[1] not in METHODS
        or sys.argv[2] not in ("login", "status")
    ):
        raise SystemExit(2)
    try:
        timeout = 12 if sys.argv[2] == "status" else 900
        connected = asyncio.run(
            asyncio.wait_for(account(sys.argv[1], sys.argv[2]), timeout)
        )
    except Exception:
        raise SystemExit(1) from None
    print("connected" if connected else "disconnected")
    raise SystemExit(0 if connected else 1)


if __name__ == "__main__":
    main()
