"""Einmalige lokale Konfiguration erstellen; bestehende Schlüssel nie ersetzen."""

import base64
import os
import secrets
from pathlib import Path

path = Path(__file__).with_name("runtime.env")
key = secrets.token_urlsafe(48)
values = {
    "SESSION_API_KEY": key,
    "OH_SESSION_API_KEYS_0": key,
    "CLISCADE_API_KEY": key,
    "AUTOMATION_LOCAL_API_KEY": key,
    "AUTOMATION_AGENT_SERVER_API_KEY": key,
    "OPENHANDS_AUTOMATION_API_KEY": key,
    "OH_SECRET_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
}
with open(path, "x", opener=lambda name, flags: os.open(name, flags, 0o600)) as output:
    output.write("".join(f"{name}={value}\n" for name, value in values.items()))
print("runtime.env angelegt; bestehende Schlüssel werden nicht überschrieben.")
