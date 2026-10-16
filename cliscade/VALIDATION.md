# Prüfstand 16. Oktober 2026

## Meilenstein 2

- `uv run ruff check .`: bestanden.
- `uv run pytest`: 8 bestanden, 1 opt-in Server-Test übersprungen.
- `tests/test_acp_protocol.py`: offizielles OpenHands SDK 1.55.1, echter
  stdio-ACP-Prozess, echtes Werkzeug-Kommando mit strukturiertem Exit-Code.
- `tests/test_agent_server_e2e.py`: separat gegen echten Agent Server 1.55.1
  (SDK-Revision in `upstream.json`), echtes Beads 1.3.1 mit eingebettetem Dolt,
  zwei unterschiedliche ACP-Conversations, persistiertes Attempt-Ledger und
  Übergabe von Git-Stand, Abnahmekriterien und Prüfbeleg. Bestanden in 51 Sekunden.
- Agent-Server-Doctor: HTTP-Health/Ready, Session-Key-Abweisung und -Annahme,
  WebSocket-Authentifizierung und OpenAPI bestanden.

Der Testagent ist ausdrücklich eine kontrollierte Protokoll-Fixture. Diese
Prüfungen sind kein authentifizierter Anbieter-E2E-Test. Ein Neustart des
CLIScade-Serviceobjekts wurde geprüft; ein vollständiger Agent-Server-Neustart
wird im folgenden Installations-/Wiederanlauf-Test separat nachgewiesen.

Die ursprünglichen Canvas-Abhängigkeiten melden beim unveränderten `npm ci`
40 Audit-Funde, darunter 2 kritisch. Sie wurden nicht still mit einem
umfangreichen `npm audit fix --force` verändert. Vor produktiver Freigabe
müssen die betroffenen Upstream-Pakete und erreichbaren Codepfade geprüft werden.
