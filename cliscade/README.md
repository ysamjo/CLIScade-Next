# CLIScade Next Integration

Die Integration verwendet `RemoteConversation`, `RemoteWorkspace` und `ACPAgent`
aus OpenHands SDK 1.55.1. ACP-JSON-RPC, Permissions, Sessions, Ereignisse und
Abbruch implementiert OpenHands. Der zusätzliche Dienst besitzt ausschließlich
Beads-Zugriff, Routing und ein Attempt-Ledger.

## Lokal starten

1. `uv sync --frozen` in diesem Verzeichnis ausführen.
2. Einen OpenHands Agent Server 1.55.1 mit persistentem Datenverzeichnis starten.
3. `CLISCADE_PROJECTS`, `CLISCADE_STATE`, `CLISCADE_AGENT_SERVER` und
   `CLISCADE_API_KEY` in einer lokalen, nicht eingecheckten Umgebung setzen.
   Der Schlüssel muss dem Session-Key des Agent Servers entsprechen.
4. `uv run uvicorn cliscade_next.api:create_app --factory --host 127.0.0.1 --port 18002`.
5. API-Schema: `/openapi.json`; alle Aufrufe benötigen `X-Session-API-Key`.

Projektverzeichnisse müssen im Agent Server unter exakt denselben absoluten
Pfaden erreichbar sein. Projekte werden ausdrücklich mit `bd init` eingerichtet;
der Dienst verändert beim Öffnen weder AGENTS.md noch vorhandene Beads-Daten.
Neue Ausführungen verwenden getrennte Git-Worktrees unter
`CLISCADE_PROJECTS/.cliscade-worktrees`. Nur der geprüfte manuelle Handoff einer
beendeten Ausführung übernimmt deren Workspace einschließlich uncommitteter
Dateien. Worktrees bleiben für Prüfung und Wiederherstellung erhalten.

## API-Ablauf

- `GET /cliscade/v1/projects` und `GET /cliscade/v1/agents`
- `POST /cliscade/v1/projects/{project}/tasks`: `title`, `description`, `acceptance`,
  `priority`, optional `parent`.
- `POST /cliscade/v1/projects/{project}/attempts`: `task_id`, `agent_id`.
- `GET /cliscade/v1/attempts/{id}` aktualisiert den Lauf aus der OpenHands-Session.
- Zweiter Start mit `source_id` übergibt den strukturierten Checkpoint an eine
  neue ACP-Session; Aufgaben-ID und Projekt müssen übereinstimmen.
- `POST /cliscade/v1/attempts/{id}/cancel` ruft OpenHands `interrupt()` auf.
- Aufgabe bearbeiten/abschließen: `PATCH .../tasks/{task_id}`; ein erfolgreiches
  Agentenende schließt die fachliche Beads-Aufgabe nicht automatisch.

Ein bestätigter Endzustand wird bei `finished` nach 30 Sekunden erneut geprüft,
weil OpenHands-Stop-Hooks eine zunächst fertige Conversation fortsetzen können.
Bei fehlender Verbindung bleibt der gespeicherte Stand erhalten. `uncertain`
und unterbrochene Vorbereitungen benötigen Prüfung; kein automatisches Replay.

## Vertrauensmodell

`Handoff.schema_version = 1` trennt Aufgabe/Abnahme, Regeln, Projektwissen,
Git-Stand, Werkzeugbelege, Agentenaussagen, Entscheidungen und offene Schritte.
Ein Werkzeugbeleg braucht Start und Ergebnis derselben Tool-ID sowie einen
strukturierten Exit-Code. Er bleibt als vom Werkzeug gemeldeter Beleg markiert,
keine unabhängige Reproduktion. Erfolgsaussagen im Agententext sind ungeprüft.
Das Kontextbudget beträgt 64.000 Zeichen; ausgelassene optionale Abschnitte
werden benannt. Pflichtkontext wird nicht still abgeschnitten.

## Tests

`uv run pytest` führt unitäre Sicherheits-/Persistenztests und einen echten
stdio-ACP-Protokolltest durch. Der ACP-Prozess ist eine kontrollierte Fixture,
kein kommerzieller Anbieter und kein produktiver Agentenadapter.

Der opt-in Test `tests/test_agent_server_e2e.py` benötigt `AGENT_SERVER_URL` und
`SESSION_API_KEY`, lokales `bd` und einen echten Agent Server. Er erstellt ein
Wegwerf-Gitprojekt mit echtem Beads und zwei echten, kontrollierten ACP-Prozessen.

Nicht nachgewiesen durch diese Tests: Authentifizierung und Inferenz bei
Claude Code, Codex, OpenCode oder Kiro; Docker-Sandbox-Laufzeit und Tailscale.
Die vier ACP-Kommandos sind integriert, Anbieter bleiben bis zum Live-Test
unverifiziert. OpenHands führt die Capability-Aushandlung beim Start durch.

## Automatische Route und Fortsetzung

`agent_id: "auto"` wählt nach Konfiguration und der vorhandenen OpenHands-
Modellerkennung. `/agents/{id}/probe` zeigt das Discovery-Ergebnis. Startbefehle,
Modellgrenzen und die getrennten Live-Nachweise stehen in `AGENTS_SUPPORTED.md`.
Die Registry akzeptiert nur bekannte ACP-Kommandos; API-Aufträge können keine
Executables einschleusen. Provider-Credentials bleiben im OpenHands-Secretstore:
CLIScade liest nur Namen und übergibt passende `LookupSecret`-Referenzen, keine
Secretwerte und keine fremden Projektschlüssel.

`POST /attempts/{id}/resume` setzt eine angehaltene oder fehlgeschlagene
OpenHands-Session ausdrücklich fort. Der neue Attempt bleibt mit derselben
Conversation und seinem Vorgänger verbunden. Eine geschlossene oder laut Beads
blockierte Aufgabe wird nicht gestartet. Neue Aufgaben lassen sich nach
expliziter Beads-Einrichtung über die Oberfläche anlegen; `bd init` erhält
`--skip-agents --skip-hooks --stealth` und überschreibt keine bestehende Datenbank.

Agenten können Entscheidungen und offene Schritte mit dem schema-validierten
`<cliscade-report>`-Block liefern (`report-v1.schema.json`). Der Block kann keine
Prüfbelege als verifiziert deklarieren. Anbieterfehler werden getrennt als
OpenHands-Laufzeitfehler im Checkpoint geführt.
