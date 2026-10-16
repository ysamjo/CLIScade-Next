# CLIScade Next auf ZimaOS

Stand 0.7.0. Vier Dienste verwenden den vorhandenen Canvas-Proxy, den offiziellen
OpenHands Agent Server 1.55.1 aus dem gepinnten CLIScade-SDK-Fork mit nativen Login-CLIs und die offizielle Automation 1.20.0. Beads 1.3.1
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
docker build -f deploy/Dockerfile.agent-server -t cliscade-next-agent-server:0.7.0 .
docker build -f deploy/Dockerfile.cliscade -t cliscade-next-service:0.7.0 .
docker build -f deploy/Dockerfile.canvas -t cliscade-next-canvas:0.7.0 .
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
| OpenCode | Eigenes OpenCode-Konto über `opencode console login --pure`; Gerätecode unter `opencode.ai/console/device` |
| Kiro | Natives Kiro-Portal (`app.kiro.dev`) mit Kontowahl; abschließende localhost-Rückleitungsadresse in CLIScade einfügen |

Bei Kiro nach Abschluss der Anmeldung die vollständige `http://localhost:…`-
Adresse aus der Browser-Adresszeile kopieren und im Feld **Vollständige Kiro-
Rückleitungsadresse** einfügen. Auf einem anderen Rechner darf diese Seite
unerreichbar sein: CLIScade übergibt die Adresse ausschließlich an den passenden
nativen Kiro-Listener im Server. Ziel, Port und OAuth-State müssen zum eigenen
Login gehören. Kein Callback-Port wird veröffentlicht. Das ist wegen des
localhost-Callbacks der CLI erforderlich; ein Gerätefluss würde in der geprüften
Version erneut AWS Builder ID auswählen.

OpenCode-Console-Konten liegen in der nativen `opencode.db`; ein älterer
OpenAI-Login in `auth.json` zählt nicht als OpenCode-Konto. Der Dienst liest
nur den booleschen Verbindungsstatus, niemals Tokens oder Kontodetails aus.

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

## Google-Anmeldung und neue ACP-Agenten in 0.7.0

Antigravity 1.4.0 verwendet den offiziellen Google-ACP-Server mit
`oauth-personal`. CodeBuddy 2.168.0 verwendet `codebuddy --acp` und die
internationale Anmeldung `external`. Im CodeBuddy-, Kiro- und OpenCode-Portal
Google auswählen. Die CLI speichert ihre Anmeldung im persistenten Home;
kein Google-API-Key und kein Kopieren lokaler Mac-Zugangsdaten sind erforderlich.
Andere Agenten behalten ihren jeweiligen Kontologin; Google ist nur nutzbar,
wenn der Anbieter es in seinem Portal anbietet.

Der SDK-Fork ist auf `099e727faeb869171564a4d09276f576a07c4400` gepinnt.
Er startet native ACP-Prozesse im zugewiesenen Workspace und unterstützt die
explizite Auswahl einer tatsächlich angebotenen ACP-Anmeldemethode. Das
Agent-Server-Image führt den Python-Entrypoint dieses Forks aus: Das eingefrorene
Upstream-Binary würde eine nachträglich installierte SDK-Korrektur ignorieren.
Die Google-Linux-Archive werden für amd64/arm64 anhand lokal berechneter,
fest eingetragener SHA-256-Werte geprüft; diese sind keine von Google
veröffentlichten Signaturen. Beide nativen Programme bleiben benachbart.

CodeBuddy hat lokal einen authentifizierten Datei-E2E bestanden. Antigravity
hat Handshake und Google-Login-Start bestanden; persönliche Kontofreigabe und
Inferenz auf dem NAS sind noch offen. Login-Starttests ersetzen keine Anmeldung.
