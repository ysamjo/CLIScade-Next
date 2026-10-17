"""OpenHands-LLM-Profil über offizielle APIs an ein OmniRoute-Modell binden."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


def request_json(method, url, token, body=None, header="Authorization"):
    headers = {header: f"Bearer {token}" if header == "Authorization" else token}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def configure(gateway, server, model, gateway_key, session_key, activate=False):
    for url in (gateway, server):
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Eine gültige HTTP(S)-Adresse ist erforderlich.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Zugangsdaten gehören nicht in die Server-Adresse.")
    if not gateway_key or not session_key:
        raise ValueError("OMNIROUTE_API_KEY und SESSION_API_KEY fehlen.")
    gateway, server = gateway.rstrip("/"), server.rstrip("/")
    models = request_json("GET", f"{gateway}/models", gateway_key)
    if model not in {item["id"] for item in models["data"]}:
        raise ValueError("Das gewählte Modell wird von OmniRoute nicht angeboten.")
    llm = {
        "model": f"openai/{model}",
        "base_url": gateway,
        "api_key": gateway_key,
        "native_tool_calling": True,
    }
    profile = "OmniRoute"
    request_json(
        "POST",
        f"{server}/api/profiles/{quote(profile)}",
        session_key,
        {"llm": llm, "include_secrets": True},
        "X-Session-API-Key",
    )
    if activate:
        request_json(
            "PATCH",
            f"{server}/api/settings",
            session_key,
            {
                "agent_settings_diff": {"agent_kind": "openhands", "llm": llm},
                "active_profile": profile,
                "active_agent_profile_id": None,
            },
            "X-Session-API-Key",
        )
    return {"profile": profile, "model": model, "activated": activate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway", default="http://omniroute:20128/v1")
    parser.add_argument("--server", default="http://agent-server:8000")
    parser.add_argument("--model", required=True, help="Exakte ID aus /v1/models")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    try:
        result = configure(
            args.gateway,
            args.server,
            args.model,
            os.environ.get("OMNIROUTE_API_KEY", ""),
            os.environ.get("SESSION_API_KEY", ""),
            args.activate,
        )
    except HTTPError as error:
        print(f"Konfiguration fehlgeschlagen: HTTP {error.code}.", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ValueError, KeyError):
        print(
            "Konfiguration fehlgeschlagen: Zugang, Modell und Erreichbarkeit prüfen.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
