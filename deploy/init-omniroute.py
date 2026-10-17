"""Neue OmniRoute-Instanz initialisieren, bestehende Schlüssel nie ersetzen."""

import os
import secrets
from pathlib import Path


path = Path(__file__).with_name("omniroute.env")
values = {
    name: secrets.token_hex(32)
    for name in (
        "JWT_SECRET",
        "API_KEY_SECRET",
        "STORAGE_ENCRYPTION_KEY",
        "INITIAL_PASSWORD",
    )
}
with open(path, "x", opener=lambda name, flags: os.open(name, flags, 0o600)) as output:
    output.write("".join(f"{name}={value}\n" for name, value in values.items()))
print("omniroute.env angelegt; keine vorhandenen Konten oder Schlüssel verändert.")
