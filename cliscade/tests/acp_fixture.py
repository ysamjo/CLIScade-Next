"""Kontrollierter ACP-Prozess für Protokolltests, kein Anbieteradapter."""

import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def send(message):
    print(json.dumps({"jsonrpc": "2.0", **message}), flush=True)


def update(session_id, value):
    send(
        {
            "method": "session/update",
            "params": {
                "sessionId": session_id,
                "update": value,
            },
        }
    )


def main():
    workspace = None
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method, params = request["method"], request.get("params", {})
        result = {}
        if method == "initialize":
            result = {
                "protocolVersion": 1,
                "agentInfo": {"name": "cliscade-protocol-fixture", "version": "1"},
                "agentCapabilities": {"loadSession": True},
            }
        elif method in ("session/new", "session/load"):
            workspace = Path(params["cwd"])
            result = {"sessionId": params.get("sessionId", str(uuid4()))}
        elif method == "session/prompt":
            session_id = params["sessionId"]
            prompt = "\n".join(block.get("text", "") for block in params["prompt"])
            (workspace / f"acp-{session_id}.txt").write_text(prompt)
            command = [sys.executable, "-c", "print('ACP-Prüfung')"]
            update(
                session_id,
                {
                    "sessionUpdate": "tool_call",
                    "toolCallId": "check",
                    "title": "Protokollprüfung",
                    "kind": "execute",
                    "status": "in_progress",
                    "rawInput": {"command": "python -c print(ACP-Prüfung)"},
                },
            )
            check = subprocess.run(command, capture_output=True, text=True, check=False)
            update(
                session_id,
                {
                    "sessionUpdate": "tool_call_update",
                    "toolCallId": "check",
                    "status": "completed",
                    "rawOutput": {
                        "exit_code": check.returncode,
                        "stdout": check.stdout,
                    },
                },
            )
            update(
                session_id,
                {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {
                        "type": "text",
                        "text": "Kontrollierter ACP-Lauf abgeschlossen.",
                    },
                },
            )
            result = {"stopReason": "end_turn"}
        elif method == "session/cancel":
            continue
        else:
            send(
                {
                    "id": request["id"],
                    "error": {"code": -32601, "message": "Method not found"},
                }
            )
            continue
        send({"id": request["id"], "result": result})


if __name__ == "__main__":
    main()
