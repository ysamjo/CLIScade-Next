# CLIScade Next auf ZimaOS

Stand 0.6.0. Vier Dienste verwenden den vorhandenen Canvas-Proxy, den offiziellen
OpenHands Agent Server 1.55.1 mit nativen Login-CLIs und die offizielle Automation 1.20.0. Beads 1.3.1
läuft ausschließlich im Integrationsdienst. Kein Docker-Socket wird eingebunden.

## Installation

Auf ZimaOS im ausgecheckten Feature-Branch:

```sh
mkdir -p /DATA/AppData/cliscade-next/projects \
  /DATA/AppData/cliscade-next/state/home \
  /DATA/AppData/cliscade-next/sessions/home \
  /DATA/AppData/cliscade-next/automation
chmod -R g+rwX /DATA/AppData/cliscade-next
# Die Container verwenden UID/GID 1000:1000. Die Verzeichnisse müssen für GID 1000 schreibbar sein.
docker build -f deploy/Dockerfile.agent-server -t cliscade-next-agent-server:0.6.0 .
docker build -f deploy/Dockerfile.cliscade -t cliscade-next-service:0.6.0 .
docker build -f deploy/Dockerfile.canvas -t cliscade-next-canvas:0.6.0 .
python3 deploy/init-secrets.py
cd deploy
docker compose config -q
docker compose up -d
```

`init-secrets.py` erstellt `runtime.env` mit Modus 0600 und überschreibt keine
bestehende Datei. Diese Datei niemals committen oder bei Updates neu erzeugen:
Agent-Server-Sessions und verschlüsselte Anbieter-Secrets benötigen dieselben Schlüssel.
Produktives Compose verwendet ausschließlich fertige Images, keine Builds und
keine Variablensubstitution. `x-casaos.port_map` ist eine Zeichenkette. Die App
wird durch Compose gestartet; eine Installation als CasaOS-Dashboard-Kachel ist
kein Bestandteil dieses Befehls.

Ein Git-Projekt nach `/DATA/AppData/cliscade-next/projects/<name>` klonen.
Canvas → Projekte & Aufgaben → Projekt wählen → Beads einrichten. Bestehendes
Beads wird verwendet, niemals neu initialisiert. Vor einer neuen Ausführung
Quelländerungen committen: der neue Worktree beginnt bei HEAD. Eine explizite
Übergabe verwendet den bisherigen Worktree einschließlich uncommitteter Änderungen.

## Privates HTTPS

Nur Canvas veröffentlicht einen Host-Port: `127.0.0.1:8740`. Im bestehenden
Tailscale-Container einen freien Serve-Port hinzufügen:

```sh
docker exec tailscale tailscale serve --bg --https=9443 http://127.0.0.1:8740
docker exec tailscale tailscale serve status --json
```

Dann `https://<tailscale-hostname>:9443/tasks` im Tailnet öffnen. Keine
Funnel-Aktivierung. Bestehende Routen werden nicht zurückgesetzt. Im JSON
muss die neue Route unter `Web` stehen und darf unter `AllowFunnel` keinen
wahren Eintrag besitzen. Tailnet-ACLs bestimmen den Zugang; jeder zugelassene
Browser erhält den lokalen Session-Key über den vorhandenen Canvas-Mechanismus.

## Anbieter einrichten

Canvas direkt unter `/tasks` öffnen → **Agenten-Konto anmelden** → CLI wählen →
**Konto anmelden**. Kein Anbieter-API-Key ist erforderlich. Die OpenHands-
LLM-Profileinrichtung wird für diese lokale Aufgabenroute übersprungen; die
Backend-Authentifizierung und Cloud-Anmeldung bleiben erhalten.

| Agent | Anmeldung in CLIScade |
|---|---|
| Codex | ChatGPT-Gerätecode; Anbieterlink öffnen und angezeigten Code bestätigen |
| Claude Code | Claude-Konto im Anbieterlink anmelden; den dort angezeigten einmaligen Anmeldecode in CLIScade einfügen |
| OpenCode | ChatGPT Pro/Plus-Gerätelogin für den OpenAI-Provider; weitere OpenCode-Provider sind hier noch nicht angebunden |
| Kiro | Nativer Device Flow mit `--license free`; Unternehmens-Identity-Center ist hier noch nicht angebunden |

Der Login verwendet ausschließlich feste native Authentifizierungsbefehle,
keine frei wählbaren Befehle, Agentenprompts oder PTYs. Agentenausführung,
ACP-Protokoll und Sessions bleiben vollständig im OpenHands SDK/Agent Server.
Der SDK-ChatGPT-Login für LLM-Profile wird nicht zweckentfremdet: dessen
Credential Store ist vom nativen Codex-ACP-Login getrennt.

Das gemeinsame Verzeichnis `sessions/home` wird im Integrationsdienst und im
Agent Server als `/workspace/home` eingebunden. Die CLIs speichern dort ihre
eigenen Kontoanmeldungen. Codex-`auth.json` wird nach erfolgreicher Anmeldung
zusätzlich über die bestehende OpenHands-Secrets-API als `CODEX_AUTH_JSON`
verschlüsselt gespeichert; deren versionierte Bindung übernimmt Token-Refresh
für ACP. Die erfolgreiche Kontowahl hat Vorrang vor älteren Anbieter-API-Keys.
Eine Anmeldung auf dem Mac wird nicht kopiert. Server-Backups enthalten sensible
Konto-Zugangsdaten und müssen privat bleiben.

Browser schließen beendet den Login nicht. **Abbrechen** stoppt nur den eigenen
Anmeldeprozess; nach spätestens 15 Minuten läuft er ab. Ein Serverneustart
verwirft offene Login-Vorgänge, abgeschlossene Kontoanmeldungen bleiben erhalten.
Ein bestätigter Login-Status beweist noch keine erfolgreiche Modell-Inferenz.
Nach Anmeldung **Anbieter prüfen** und eine Datei-Aufgabe im Wegwerfprojekt testen.

Native Login-Programme: Codex 0.163.0, Claude Code 2.1.301, OpenCode 1.18.23,
Kiro 2.31.1. Der Kiro-Download wird für amd64 und arm64 gegen feste offizielle
SHA-256-Prüfsummen geprüft. Linux/amd64 wird auf ZimaOS gebaut und geprüft;
arm64 ist vorbereitet, aber nicht live gebaut. Die CLI-Pakete behalten ihre
jeweiligen Lizenzen/Nutzungsbedingungen, insbesondere Claude Code und Kiro;
dieses Repository enthält ihre Installationsanweisungen, keine um-lizenzierten
Kopien. Details zur Ausführung: [Agentenmatrix](../cliscade/AGENTS_SUPPORTED.md).

## Persistenz und Wiederanlauf

| Hostverzeichnis | Inhalt |
|---|---|
| `projects` | Git-Projekte, native `.beads`-Daten, separate `.cliscade-worktrees` |
| `state` | Attempt-/Checkpoint-Ledger, Request-IDs, Konsenszuordnung, geprüfte Beads-Backups |
| `sessions` | Offizielle OpenHands-Conversations, Auth-/Secret-Persistenz, CLI-Home |
| `automation` | Native Automation-Datenbank, Bundles und Ausführungsdaten |

Agenten laufen im Agent Server unabhängig vom Browser. Nach einem Service-
Neustart werden vorhandene Sessions mit `attach` geladen; Prompts werden nicht
wiederholt. Ein vor dem Versand persistierter Marker verhindert automatisches
Replay bei unklarem Transportzustand. Worktrees werden nicht automatisch gelöscht.

**Beads sichern und Wiederherstellung prüfen** erstellt ein natives Dolt-Backup
und verifiziert Aufgaben und Memories in einem Wegwerfprojekt. Der SHA-256-Beleg
liegt unter `state/cliscade/backups/<id>/receipt.json` (Containerpfad unter
`/data/cliscade/backups`). Dies ersetzt keine vollständige Serversicherung:
für eine konsistente Gesamtsicherung die vier eigenen Compose-Dienste stoppen,
alle vier Hostverzeichnisse und `runtime.env` extern sichern und danach starten.
Eine Wiederherstellung zuerst in einer separaten Installation prüfen.
Automatische Backup-Retention und NAS-zu-NAS-Kopie sind noch offen.

## Konsens und Scheduling

Konsens startet zwei bis vier unterschiedliche ACP-Agenten auf derselben
Git-Revision mit derselben anfänglichen Aufgabe und demselben Projektwissen.
Jeder hat einen eigenen Worktree. Unterschiede, Werkzeugbelege und Aussagen
werden angezeigt. Gleiche Patch-Hashes beweisen keine Korrektheit; es gibt keinen
automatischen Merge. Unklare Starts stoppen weitere Starts sichtbar.

Zeitpläne werden als native OpenHands-Automationen gespeichert. Der feste
Dispatch-Code verwendet ein mitgeliefertes PEP-723-/uv-Lockfile mit OpenHands
SDK 1.55.1 und httpx 0.28.1 und ruft nur die Aufgaben-API auf; Agenten startet weiterhin OpenHands
über ACP. Die native Automation-Run-ID ist der Idempotenzschlüssel. Geschlossene
Aufgaben werden übersprungen. Wiederholte Zustellung startet keinen zweiten
Attempt. Zeitpläne über die vorhandene Canvas-Automationsansicht pausieren oder
löschen. Es gibt keinen zusätzlichen CLIScade-Cron-Daemon.

## Grenzen

- amd64 ist das ZimaOS-Testziel. Die offiziellen OpenHands-Manifeste enthalten
  auch arm64; ein vollständiger arm64-Stack wurde nicht ausgeführt.
- Der Agent Server läuft selbst in einem Docker-Container, seine Conversations
  verwenden den vorhandenen In-Process-Modus. Git-Worktrees trennen Änderungen;
  sie sind keine Sicherheitsgrenze zwischen Agenten desselben Containers.
- Der Upstream-Discovery-Endpunkt unterstützt per-Conversation-Docker derzeit
  nicht (HTTP 501). Diese Betriebsart ist hier nicht als vollständig getestet
  ausgewiesen. Kein Host-Docker-Socket wird zur Umgehung freigegeben.
- Kein öffentliches HTTPS, kein Funnel und keine Übertragung lokaler Logins.

## Reproduzierbare Docker-Prüfung

`verify-stack.py prepare` und nach `docker compose restart` der Modus `recover`
werden im CLIScade-Container ausgeführt. Die Protokoll-Fixture aus
`cliscade/tests/acp_fixture.py` muss vorher unter
`projects/.cliscade-verification/acp_fixture.py` liegen. Das Skript verändert nur
`cliscade-smoke`, einen separaten `state/smoke-ledger` und seine eigenen nativen
Testautomationen. Es belegt echten ACP-Transport, Beads-Sicherung, Persistenz,
Handoff und nativen Scheduler-Abschluss; es simuliert ausdrücklich Anbieter.

Der erste Start lädt die gepinnte uv-Skriptumgebung in den persistenten
Agent-Server-Home-Cache. Ein System-Python ohne SDK genügt nicht. Die interne
Authentifizierung Automation → Agent Server benötigt
`AUTOMATION_AGENT_SERVER_API_KEY`; `AUTOMATION_LOCAL_API_KEY` authentifiziert
separat die Automations-API und deren Callbacks.
