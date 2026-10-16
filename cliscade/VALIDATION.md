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

Die produktive Version 0.6.0 wurde auf ZimaOS per Compose gestartet. Ego Lite
prüfte alle vier Login-Abläufe über einen eigenen SSH-Tunnel, einschließlich
Claude-Anmeldecode-Feld, Gerätecodes, Abbruch und Wiederaufnahme eines laufenden
OpenCode-Logins nach Browser-Reload (Anbieter erneut ausgewählt). Die Ansicht
hat bei 390, 768 und 1440 Pixeln keinen horizontalen Überlauf. Ein erneuter
Integrationsdienst-Neustart erhält Beads-Projekte und den vorhandenen
Agent-Server-Kontext (HTTP 200). Alle Testanmeldungen wurden abgebrochen;
es sind keine persönlichen Konten verbunden. Private HTTPS-Route: HTTP 200
vom NAS; die bestehende ZimaOS-Link-Kachel bleibt unverändert.

### Korrekte Kontenportale 0.6.1

Die Startbelege aus 0.6.0 prüften nur, ob irgendein Anbieterlink erschien. Sie
bestätigten deshalb fälschlich die gewünschte Kontowahl: OpenCode war auf OpenAI
festgelegt, Kiro auf AWS Builder ID. Diese Einschränkung ist korrigiert.

- 35 Python-Tests bestanden, 6 opt-in E2Es übersprungen; darunter Kiro-Portal-Übergabe, kontrollierter Callback-Abschluss und persistenter Status sowie Ablehnung fremder Hosts, Ports und OAuth-States.
- 47 fokussierte Canvas-Tests bestanden, Typecheck, Lint und Übersetzungsvollständigkeit bestanden (692 geerbte Warnungen).
- Alle drei eigenen Images 0.6.1 auf ZimaOS gebaut; der Canvas-Produktionsbuild bestand. Die Kiro-Binärdateien werden unter ihren ursprünglichen Namen kopiert; `xdg-utils` ermöglicht den nativen Portalstart im Integrationscontainer.
- `deploy/verify-login.py` verifiziert nun ausdrücklich die erwarteten Hosts: Codex `auth.openai.com`, Claude `claude.com`, OpenCode `opencode.ai`, Kiro `app.kiro.dev`. Alle vier nativen Starts und gezielten Prozessabbrüche bestanden.
- Der OpenCode-Status verwendet das aktive eigene Console-Konto in der nativen Datenbank; alte OpenAI-OAuth-Dateien gelten nicht als OpenCode-Konto.

Keine persönlichen Konten autorisiert. Ein vollständiger echter Kiro-OAuth-Abschluss
mit manuell übernommener localhost-Rückleitung und authentifizierte NAS-Inferenz
bleiben vom Benutzerlogin abhängig; der Callback ist mit einem nativen
Listener-Test geprüft. Ego Lite bestätigte im echten Kiro-Portal Google, GitHub, Builder ID und
Your organization. Das echte OpenCode-Console-Portal zeigte Google, GitHub
und E-Mail. Oberfläche bei 390 und 768 Pixel ohne horizontalen Überlauf
geprüft; eigene Login-Vorgänge abgebrochen und alle eigenen Browserseiten
geschlossen. Private HTTPS-Route, Beads und gespeicherte Session lieferten
nach dem Compose-Update HTTP 200.

Quellvertrag OpenCode 1.18.23:
[Console-Anmeldung](https://github.com/anomalyco/opencode/blob/ef2880f379129aa048be9e9353e30aa168d42c17/packages/opencode/src/cli/cmd/account.ts),
[nativer Kontenspeicher](https://github.com/anomalyco/opencode/blob/ef2880f379129aa048be9e9353e30aa168d42c17/packages/core/src/account/sql.ts).
Kiro: [offizielle CLI-Anmeldung](https://kiro.dev/docs/cli/authentication/); der
Gerätefluss der tatsächlich gepinnten Linux-CLI 2.31.1 wählte beim Test AWS und
wird deshalb für die allgemeine Kontowahl nicht verwendet.

## 0.7.0: Antigravity, CodeBuddy und Google-Kontoanmeldung

- Backend: 41 bestanden, 8 opt-in Prüfungen übersprungen. Ruff bestanden.
- UI: 56 Tests in vier Dateien mit Node 24.19.0 bestanden (Login, Aufgaben,
  Root und Sidebar). Der Shell-Standard Node 22 führte zu Timeouts bei lazy
  geladenem Cloud-Onboarding; mit der geforderten Node-Version bestanden.
- Lint/Typecheck/Prettier bestanden; 692 vorhandene ESLint-Warnungen, keine Fehler.
  Übersetzungen vollständig, F29-Feature-Map gültig. Canvas-Docker-Build bestanden.
- SDK-Fork: 496 ACP-Tests, Ruff und TypeScript-Client-Build bestanden.
  Auth-Auswahl, echte Prozess-Arbeitsverzeichnisse und Discovery geprüft.
- CodeBuddy 2.168.0: lokaler authentifizierter Datei-E2E mit vorhandenem Konto
  bestanden. Der SDK-Fix setzt das Prozess-CWD, weil CodeBuddy session/new.cwd
  nicht übernimmt. Keine lokale Anmeldung auf das NAS kopiert.
- Alle sechs nativen CLI-Login-Starts im isolierten NAS-Container bestanden:
  Codex → auth.openai.com, Claude → claude.com, OpenCode → opencode.ai,
  Kiro → app.kiro.dev, Antigravity → accounts.google.com,
  CodeBuddy → www.codebuddy.ai. Eigene Login-Prozesse gezielt beendet.
- SDK-Fork im tatsächlichen Python-Agent-Server-Entrypoint geprüft:
  OpenAPI enthält acp_auth_method; /ready liefert 200. Das Upstream-Binary
  selbst verwendet diesen Python-SDK-Patch nicht.
- NAS: eigene Images 0.7.0 gebaut; alte Session weiterhin HTTP 200.
  Neues Beads-Smoke-Task cn-xp7, ACP-Session und verifiziertes Backup angelegt.

Persönliche Google-Freigabe für Antigravity und NAS-CodeBuddy-Inferenz sind
noch offen. Login-Link, Handshake und Mock-Tests ersetzen diese Nachweise nicht.

Nach vollständigem Neustart des Agent Servers und Integrationsdienstes:
Session `6cfabdfa-9f2c-4837-95a5-100dcfa1d663` wieder angebunden, Handoff an
zweite ACP-Session `6725566b-9cc0-492a-8cba-fca725cd32ae` abgeschlossen.
Aufgabe `cn-xp7`, derselbe Workspace, Git-Stand und verifizierte Prüfergebnisse
blieben erhalten. Native Automation meldet `COMPLETED`; danach deaktiviert.
Protokoll-Fixtures, keine Anbieter-Inferenz. Alle Health-Endpunkte HTTP 200.

Live-UI: Antigravity öffnet Google, CodeBuddy öffnet sein internationales Portal.
390 px Smartphone-Breite: kein horizontaler Überlauf; CodeBuddy verlangt keine
localhost-Rückleitung. Das echte CodeBuddy-Portal zeigt aktuell E-Mail, Tencent
OneID und Enterprise-SSO, keinen Google-Button. Google-Kontoanmeldung ist dort
nicht bestätigt; keine Ersatzanmeldung vorgenommen. Der frühere allgemeine
Google-Hinweis wurde nach dieser Live-Prüfung korrigiert.

Login-Polling prüft während laufender Anmeldung ausschließlich den vorhandenen
Prozess und dessen erfassten Anbieterlink. Es startet keinen konkurrierenden
nativen Statusprozess. Neuer API-Regressionstest zunächst rot, danach grün;
41 Backend-Tests bestanden, 8 opt-in Prüfungen übersprungen.
