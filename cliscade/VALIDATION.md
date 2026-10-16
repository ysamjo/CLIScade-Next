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

## Meilenstein 5 – Konsens, Automationen und Deployment

- `uv run pytest`: 25 bestanden, 6 opt-in Prüfungen übersprungen. Darunter ein
  echtes natives Beads-Backup mit vollständigem Aufgaben-/Memory-Vergleich nach
  Wiederherstellung, Idempotenz, unabhängige Worktrees und sichere Compose-Grenzen.
- `ruff check` für Integration und Deployment, Canvas-Typecheck, Produktionsbuild,
  vollständiger Canvas-Lint und drei gezielte UI-/Transporttests bestanden.
  Vorhandene Lint-Warnungen und die oben dokumentierten Vollsuite-Fehler bleiben.
- Erneuter echter SDK-/Agent-Server-/Beads-Test einschließlich zweier separater
  Konsens-Worktrees und Werkzeugbelegen bestanden (105 Sekunden). Kontrollierte
  ACP-Protokoll-Fixtures, keine behauptete kommerzielle Anbieter-Inferenz.
- ZimaOS amd64: beide eigenen Images gebaut; offizielle Agent-Server- und
  Automation-Images gestartet. Alle vier Dienste anschließend tatsächlich neu
  gestartet. Die erste gespeicherte Conversation blieb erreichbar; Aufgabe und
  Attempt-Ledger blieben erhalten; Handoff an eine zweite ACP-Conversation im
  bisherigen Worktree mit Prüfbelegen bestanden.
- Native Automation: Bundle-Upload, Erstellung, manuelle native Zustellung,
  Überspringen einer geschlossenen Aufgabe und SDK-Abschlusscallback HTTP 200
  tatsächlich ausgeführt; nativer Status `COMPLETED`, auch nach Neustart.
  Der Testzeitplan wurde anschließend auf `INACTIVE` gesetzt.
- Beim realen Test behoben: Timeout auf erlaubte 1.800 Sekunden begrenzt,
  separate interne Automation-Authentifizierung eingerichtet, Dispatch über
  gepinnte PEP-723-/uv-Umgebung statt System-Python ohne SDK gestartet.
- Canvas vom tatsächlichen NAS-Container über einen eigenen SSH-Testtunnel in
  Ego Lite geprüft. Neue Konsens-/Zeitplan-/Backup-Bedienelemente bei 1440 und
  390 Pixeln; kein horizontaler Seiten-Scroll. Die Beads-Sicherung zusätzlich
  im laufenden lokalen Canvas angeklickt und mit Wiederherstellungsbeleg bestätigt.
- Tailscale Serve: zusätzliche HTTPS-Route 9443 auf Loopback 8740. Bestehende
  Routen 443/8443 unverändert; für 9443 kein `AllowFunnel`-Eintrag. TLS-Aufruf
  auf ZimaOS mit überprüftem Zertifikat und Auflösung auf die eigene Tailnet-IP:
  HTTP 200. Direkter Tailnet-Zugriff des Macs war nicht erreichbar; Browser-
  Prüfung erfolgte über den temporären SSH-Tunnel, nicht als behaupteter Mac-
  Tailscale-E2E.

Lokale Rohbelege: isolierter Agent-Server-Lauf `20261016-032345-bef1-cliscade-next`,
`CLISCADE.milestone5/consensus.json`; NAS `state/deployment-proof.json`, native
Automation-Historie und `restart.log`. Schlüssel und vollständige private
Sessions werden nicht in GitHub hochgeladen. Screenshots liegen als private
PR-Artefakte unter `.pr/screenshots/`.

### Korrektur 0.5.1: committed Lösungen vergleichen

Drei neue Regressionen zeigten den Fehler vor der Korrektur: unterschiedliche
committete Text-/Binärdateien sowie Symlink gegenüber normaler Datei wurden
fälschlich als gleicher Patch behandelt. Nach der Korrektur bestehen alle drei.
Das Ledger speichert die Ausgangsrevision je Attempt; Git-Diffs einschließlich
Binärpatches und Regeln für geänderte Unterverzeichnisse beziehen sich darauf.
Handoff und Resume erhalten die Ausgangsrevision. Eine zusätzliche Regression
prüft committete Änderungen im Handoff; eine weitere die verlustfreie Erweiterung
eines vorhandenen Ledgers. Alte Konsens-Checkpoints ohne passende Ausgangsrevision
werden nicht nachträglich als Patch-Übereinstimmung ausgegeben.

Auch 0.5.1 wurde auf ZimaOS gebaut und erneut durch den vollständigen Container-
Neustart/Handoff-Test geprüft. Die neue Attempt-Ausgangsrevision blieb erhalten;
die native Automation war nach dem Neustart `COMPLETED` und anschließend
`INACTIVE`. TLS blieb mit überprüftem Zertifikat HTTP 200.

### CLI-Kontoanmeldung 0.6.0

- 32 Python-Tests bestanden, 6 explizite Anbieter-/Server-E2Es ohne Zugangsdaten übersprungen.
- 46 fokussierte Frontend-Tests bestanden: native Login-Challenges, Claude-Code-Weitergabe, Abbruch, frischer `/tasks`-Einstieg, Aufgaben/Handoff und ausgeblendete API-Key-Checkliste.
- Typecheck, Produktionsbuild und Lint bestanden; Lint meldet weiterhin 692 geerbte Warnungen.
- Auf ZimaOS wurden die drei eigenen Images gebaut. `deploy/verify-login.py` prüfte mit echten nativen CLIs für Codex, Claude Code, OpenCode und Kiro Anbieterlink/Gerätecode und Prozessabbruch. Keine persönlichen Konten autorisiert und keine Modell-Inferenz als bestanden ausgegeben.
- Native Konto-Persistenz und der Codex-Transfer in die offizielle OpenHands-Secrets-API sind mit kontrollierten Tests geprüft. Die persönliche Konto-Freigabe und authentifizierte NAS-Datei-E2Es bleiben Benutzer-/Anbieterschritte.
- OpenCodes `auth list` vor dem ersten Login blockierte im getesteten Image den Login-Start. Die Statusprüfung liest deshalb ausschließlich den dokumentierten OAuth-Store, ohne einen zweiten OpenCode-Prozess zu starten.
