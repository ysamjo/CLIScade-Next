"""Prüft echte native Login-Starts ohne Kontofreigabe oder Modellaufruf."""

import json
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from cliscade_next.login import PROVIDERS, LoginService


def main():
    report = []
    with tempfile.TemporaryDirectory(prefix="cliscade-login-check-") as temporary:
        service = LoginService(Path(temporary))
        try:
            for provider, spec in PROVIDERS.items():
                service.close()
                service = LoginService(Path(temporary) / provider)
                status = service.status(provider)
                if not status["available"]:
                    raise RuntimeError(f"Login-CLI fehlt: {provider}")
                service.start(provider)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    state = service.current(provider)
                    if state["state"] != "pending" or (
                        state.get("url")
                        and (spec["mode"] != "device" or state.get("user_code"))
                    ):
                        break
                    time.sleep(0.25)
                ready = state["state"] == "pending" and bool(state.get("url"))
                ready = ready and (
                    spec["mode"] != "device" or bool(state.get("user_code"))
                )
                expected_host = {
                    "codex": "auth.openai.com",
                    "claude-code": "claude.com",
                    "opencode": "opencode.ai",
                    "kiro": "app.kiro.dev",
                }[provider]
                ready = (
                    ready and urlsplit(state.get("url") or "").hostname == expected_host
                )
                report.append(
                    {
                        "provider": provider,
                        "native_cli_available": True,
                        "challenge_received": ready,
                        "provider_host": urlsplit(state.get("url") or "").hostname,
                        "inference_verified": False,
                        "account_authorized": False,
                    }
                )
                service.cancel(provider, state["id"])
                report[-1]["cancelled"] = (
                    service.current(provider)["state"] == "cancelled"
                    and service.jobs[provider]["process"].poll() is not None
                )
        finally:
            service.close()
    print(json.dumps(report, indent=2))
    if not all(item["challenge_received"] and item["cancelled"] for item in report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
