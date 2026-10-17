# OpenHands-Harness über OmniRoute — Deployment 0.8.0

Der eingebaute OpenHands-Agent verwendet ein OpenAI-kompatibles Modellprofil.
OmniRoute ist dessen Modellgateway, kein zweiter Coding-Harness. Die Beads-Runs
und externen ACP-Agenten behalten ihre native CLI-Anmeldung und Registry.
Der Gateway muss nicht im Agent-Server-Container installiert sein: Docker-DNS
stellt ihn im gemeinsamen Compose-Netz als `http://omniroute:20128/v1` bereit.
Der Browser darf diese interne Adresse nicht direkt verwenden.

## ZimaOS

Zusätzlich zum bestehenden Stack (keine anderen Dienste neu starten):

```sh
cd /DATA/AppData/cliscade-next/source
mkdir -p /DATA/AppData/cliscade-next/omniroute
chown 1000:1000 /DATA/AppData/cliscade-next/omniroute
python3 deploy/init-omniroute.py
cd deploy
docker compose -f docker-compose.yml -f docker-compose.omniroute.yml config -q
docker compose -f docker-compose.yml -f docker-compose.omniroute.yml up -d --no-deps omniroute
```

Das offizielle Image 3.8.51 ist per Manifest-Digest fixiert (amd64/arm64).
SQLite, Anbieter-Konten und Einstellungen liegen unter `omniroute/`; die
Schlüssel in `deploy/omniroute.env` müssen ebenfalls gesichert werden.
Das Initialisierungsskript ersetzt niemals bestehende Dateien. Die Instanz
beginnt ohne übernommene Mac-Konten. Eine Migration benötigt eine ausdrückliche
Nutzerwahl sowie Datenbank-Snapshot und zugehörigen Verschlüsselungsschlüssel.
Eine laufende SQLite-Datenbank nicht mit einfachem `cp` kopieren.

Port 20128 bindet nur an NAS-Loopback. Für die Verwaltung einen freien privaten
Tailscale-Serve-Port auf `http://127.0.0.1:20128` legen, bestehende Routen erhalten,
kein Funnel. Auf dem aktuellen NAS ist dies Port 9444:
`https://zimaos.tail8d09ea.ts.net:9444`. Das zufällige Verwaltungskennwort steht lokal in `omniroute.env`
unter `INITIAL_PASSWORD`; nie in Chat, Logs oder Git übernehmen.

## Modellprofil

1. In OmniRoute einen Anbieter per Kontologin verbinden und ein für Toolaufrufe
   geeignetes Modell bzw. einen entsprechend konfigurierten Combo auswählen.
2. Einen Gateway-Schlüssel für OpenHands erzeugen. Das ist ein interner
   Zugriffsschlüssel zwischen den Diensten, kein erforderlicher Anbieter-API-Key.
3. `configure-omniroute.py` im Integrationscontainer ausführen. Der Schlüssel
   kommt ausschließlich über `OMNIROUTE_API_KEY`; `SESSION_API_KEY` ist dort bereits
   durch `runtime.env` gesetzt. Modell-ID exakt aus OmniRoute `/v1/models` übernehmen:

```sh
python /tmp/configure-omniroute.py --model <modell-oder-combo-id> --activate
```

Das Skript vorab nach `/tmp/configure-omniroute.py` im Integrationscontainer kopieren.
Secrets über privaten stdin/Environment-Kanal zuführen, niemals als CLI-Argument
oder über eingecheckte Compose-Werte. Das Skript prüft den Katalog vor Änderungen,
speichert das benannte Profil `OmniRoute` über die offizielle Agent-Server-API und
aktiviert auf Wunsch den eingebauten OpenHands-Agenten für neue Gespräche.
Ohne `--activate` bleibt die aktuelle Agentenauswahl erhalten. Ein bestehendes
Profil namens `OmniRoute` wird aktualisiert; andere Profile bleiben erhalten.
Laufende Conversations behalten ihre bisherige Konfiguration. Der Agent Server
verschlüsselt den Gateway-Schlüssel mit seinem bestehenden `OH_SECRET_KEY`.

Die Katalogprüfung beweist noch keine funktionierenden Toolaufrufe. Vor produktiver
Nutzung einen kleinen Datei-Test mit dem OpenHands-Agenten durchführen und Ergebnis,
Git-Diff und Gateway-Protokoll prüfen. Ohne Anbieterlogin nur Mock-Nachweise angeben.

Tests: `cliscade/.venv/bin/pytest -q cliscade/tests/test_omniroute.py cliscade/tests/test_deployment.py`.
