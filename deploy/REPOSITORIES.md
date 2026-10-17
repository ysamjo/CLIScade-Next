# Repository-Workspaces — 0.9.0

Die NAS-Version zeigt unter „New Chat“ die GitHub-Repository-Auswahl als Standard.
Der Katalog verwendet die vorhandene Agent-Server-GitHub-API (nach letztem Push
sortiert, bis zu 30 Einträge). Erfolgreich verwendete Repositories stehen zuerst;
die letzte Auswahl und bis zu zehn verwendete Namen werden auf dem Server unter
`state/cliscade/repository-workspaces.json` gespeichert. Ein unbekanntes oder nicht
mehr zugängliches Repository wird nicht blind geöffnet.

Das vorhandene PAT darf `GITHUB_PERSONAL_ACCESS_TOKEN`, `GITHUB_TOKEN`, `GH_TOKEN`
oder `github` heißen. Fehlt `github_token`, normalisiert der Dienst es einmalig
unter diesem vom SDK erwarteten Namen. Das ursprüngliche Secret bleibt erhalten;
für spätere Rotation `github_token` aktualisieren. Kein Token gelangt in den
Browser oder in die Auswahlantwort.

Beim Absenden wird über `RemoteWorkspace.clone_repos` ein eigener Checkout unter
`/projects` erstellt. Der SDK-Klonpfad schreibt eine authentifizierte Remote-URL;
der Integrationsdienst ersetzt sie vor der Freigabe durch die reine HTTPS-URL.
Ein Git-Credential-Helper liest das Secret bei Bedarf vom lokalen Agent Server,
begrenzt auf github.com. Eine falsche Repository-ID, fehlendes PAT oder ein
fehlgeschlagener Klon startet keinen leeren Ersatz-Chat. Der Prompt bleibt erhalten.
Als Übergang entsteht pro Chat ein eigener Klon; das braucht mehr Speicher als ein Cache,
vermeidet aber das Zurücksetzen oder Wiederholen bereits geänderter Arbeitsstände.

Canvas startet anschließend den nativen OpenHands-Worktree mit Feature-Branch
`openhands/<conversation-id>`. Sein Root ist `/workspace/worktrees` und liegt im
persistenten Sessions-Volume. Der Coding-Kontext verlangt Repository-Regeln, Tests
und bei Codeänderungen Commit, Push und Pull Request. Das ist eine Agentenanweisung;
API-Berechtigungen, Tests und tatsächliche Veröffentlichung müssen weiterhin am
Ergebnis geprüft werden. Der ausgewählte Modell-/ACP-Agent wird dadurch nicht ersetzt.

„Open Workspace“ erlaubt weiterhin die bewusste Auswahl eines lokalen Ordners.
Andere Backend-Hosts, Cloud- und isolierte Docker-Backends behalten ihren bisherigen Startablauf; das
Feature ist im CLIScade-Canvas-Build über `VITE_CLISCADE_REPOSITORIES=true` aktiviert.
Automationen bleiben von der verpflichtenden Repository-Auswahl ausgenommen.

## Aktualisieren

Canvas und Integrationsdienst als 0.9.0 auf dem NAS bauen. Der Agent Server braucht
kein neues Image, aber wegen `OH_CONVERSATION_WORKTREE_ROOT` einmalig eine neue
Container-Konfiguration. Vorher aktive Runs und Login-Vorgänge prüfen. Bestehende
Container-Worktrees unter `/tmp` werden nicht automatisch migriert; unveröffentlichte
Arbeit dort vor einem Austausch sichern. Neue Repository-Chats nutzen das Volume.
`deploy/runtime.env` und `deploy/omniroute.env` sind vom Build-Kontext ausgeschlossen.

Tests: Backend `test_repositories.py`, `test_deployment.py`; Frontend
`home-chat-launcher.test.tsx` einschließlich fehlgeschlagener Vorbereitung.

## Abgrenzung zum gemeinsamen Projekt-Workspace

Dieser Schritt verbindet GitHub mit dem bisherigen Canvas-Chatstart. Er erzeugt
noch keine stabile Projekt-ID und keine gemeinsame Beads-Aufgabenliste für das
Repository. `/tasks` bleibt ein separater Pfad. Die nächste Migration muss einen
kanonischen Projekt-Root je Repository bereitstellen und bestehende Klone samt
unveröffentlichten Änderungen erhalten. Neue Runs sollen Worktrees dieses
Projekts verwenden; Beads bleibt projektweit kanonisch.

Live-Prüfung: privates Repository geklont, persistenter OpenHands-Worktree und
Feature-Branch angelegt, credential-freies origin und authentifiziertes
`git ls-remote` bestätigt. Der OpenHands-/c1-Agent erzeugte die Testdatei,
aber der geforderte abschließende Zeilenumbruch fehlt. Kein Commit/Push für
diesen begrenzten Test; keine Behauptung eines bestandenen exakten Datei-E2E.
