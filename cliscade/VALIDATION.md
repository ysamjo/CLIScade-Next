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

## Meilenstein 3 und 4

- Canvas: Typecheck, vollständiger Lint und Produktionsbuild bestanden; der Lint
  enthält vorhandene Upstream-Style-Warnungen.
- Drei gezielte Frontend-/Transporttests bestanden; Feature-Map vollständig.
- Echte Ego-Lite-Captures bei 1440 und 390 Pixeln; kein horizontaler Seiten-Scroll.
  Beads-Aufgabe über die UI angelegt und nach Reload wiedergefunden.
- Vollsuite nicht grün: Die geerbten Cloud-Onboarding-Tests scheitern auch im
  separaten unveränderten Checkout `aa593c72103862d4f1851988ecacd30f514368dc`
  (22 bestanden, 2 fehlgeschlagen). Der vollständige lokale Lauf wurde nach
  diesen Fehlern beendet; er wird nicht als vollständiger Testnachweis ausgegeben.
- Kiro 2.31.1 und Claude Code: authentifizierte lokale ACP-Datei-E2Es bestanden.
- Codex: ACP-Handshake bestanden; Datei-E2E scheitert am lokal konfigurierten
  Modell `gpt-6.1-sol`, das der Anbieter für die ChatGPT-Anmeldung abweist.
- OpenCode: ACP antwortet, angeforderte Datei fehlt; keine vollständige Freigabe.
- Zusätzlicher Claude-Test über echten Agent Server und Secret-Lookups: Modell-
  Discovery und Start funktionieren, Inferenz endet mit HTTP 429, weil die
  Gateway-Credentials für `claude-opus-5` abkühlen. Kein automatisches Replay;
  dieser Server-Anbieter-E2E ist nicht bestanden.
- Vollständiger Agent-Server-Neustart mit derselben Persistenz und demselben
  Session-Key: authentifizierter Lesezugriff auf die gespeicherte erste
  Conversation, unverändertes Attempt-Ledger und Übergabe an eine zweite
  kontrollierte ACP-Session bestanden (65 Sekunden). Dies ist ein echter
  Prozess-Neustart, kein Mock und kein bloß neues Serviceobjekt.
