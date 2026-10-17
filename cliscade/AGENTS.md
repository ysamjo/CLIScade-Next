# CLIScade-Next-Integration

Dieses Paket besitzt Beads-Projektzugriff und Orchestrierungsregeln. Ausführung,
ACP-Transport, Conversation-Persistenz und Abbruch gehören dem vorhandenen
OpenHands SDK/Agent Server und werden über dessen SDK wiederverwendet.
Beads ist die einzige Aufgabenquelle. Das SQLite-Ledger speichert Attempts und
Checkpoints, keine zweite bearbeitbare Kopie von Aufgaben oder Conversations.

Feature-Branches und deutsche Dokumentation/Commit-Messages verwenden.
In diesem Verzeichnis `uv sync --frozen`, `uv run pytest` und
`uv run ruff check .` ausführen. Für Deployment-Code aus dem Repository-Root:
`uv run --project cliscade ruff check --config cliscade/pyproject.toml cliscade deploy`.

Agentenaussagen bleiben ungeprüft. Werkzeugbelege benötigen zusammengehörigen
Start/Ergebnis und Exit-Code; Agentenprosa ist kein Nachweis. Nach möglichem
Promptversand ist automatischer Fallback verboten.

Übergeordnete OpenHands-Regeln gelten für Canvas-Code. Die fachliche Integration
liegt hier als eigener Dienst, weder als Ersatz-Agent-Server noch in Canvas-
API-Adaptern. Keine Headless- oder PTY-Runner ergänzen.

Konsensreservierungen und Dispatch müssen denselben dateibasierten Dispatch-Lock
beachten. Jeder Konsensversuch beginnt bei derselben Revision und eingefrorenen
Aufgabe/Projektwissen; Provider-Historien bleiben getrennt. Eine Patch-Gleichheit
ist kein Korrektheitsnachweis. Native Automationen verwenden ihre Run-ID als
Idempotenzschlüssel. Der Dispatch-Bundle enthält keine Zugangsdaten.

Beads-Backups werden erst nach nativer Wiederherstellung und vollständigem
Vergleich von Aufgaben und Memories als verifiziert bezeichnet. Das ist keine
vollständige Sicherung der OpenHands-Sessions. Deployment-Tests stehen in
`tests/test_deployment.py`; Docker-Builds laufen ausschließlich auf ZimaOS.

Der Git-Vergleich muss sich auf die persistierte Ausgangsrevision beziehen,
nicht nur auf das aktuelle HEAD des Agenten. Selbst erstellte Commits dürfen
Änderungen weder im Handoff noch im Konsens verbergen. Binärpatches sowie Typ
und Ausführbarkeit unversionierter Dateien gehören zum Vergleich.

CLI-Kontoanmeldung: `login.py` darf ausschließlich die fest hinterlegten nativen
Auth-Befehle starten, ohne Shell, PTY oder Agentenprompts. Keine Roh-Ausgaben,
Tokens oder eingegebenen Anmeldecodes ausliefern oder loggen. Nur erlaubte
Anbieter-URLs und Gerätecodes verlassen den Dienst. Login-Home und ACP-Home
müssen dasselbe persistente Verzeichnis verwenden. Codex-Kontoanmeldung wird
über die vorhandene OpenHands-Secrets-API gespeichert; deren versionierte
Credential-Bindung muss beim ACP-Start erhalten bleiben. Login-Abbruch darf
keine Agenten-Ausführungen unterbrechen. Alle Kindprozesse beim Dienstende
beenden; offene Login-Vorgänge dürfen nach Neustart neu begonnen werden.

Kiro-Kontowahl verwendet das normale native Portal, keinen erzwungenen AWS-
Gerätefluss. Der Browser-Helfer übergibt nur `app.kiro.dev`-URLs privat an den
Login-Vorgang. Rückleitungen nur an dessen localhost-Ziel mit passendem State
weitergeben; keine Redirects oder Proxy-Umgebungsvariablen verwenden. OpenCode
meldet sein eigenes Console-Konto an; OpenAI-Credentials sind kein Nachweis dafür.

Antigravity/CodeBuddy: `acp_login.py` verwendet ausschließlich den offiziellen
ACP-Client für Initialize, Authenticate und den lesenden nativen Kontostatus.
Keine Sessions, Prompts oder Tools in diesem Auth-Helfer. CodeBuddy vor einer
Anmeldung auf vorhandene Credentials prüfen, da Authenticate eine bestehende
Anmeldung sonst abmeldet. Antigravity verwendet ausschließlich `oauth-personal`.
Google ist der bevorzugte Portal-Login; keine erfundenen OAuth-Parameter oder
API-Key-Pflicht einführen. SDK-Fork und Agent-Server-Runtime gemeinsam pinnen.

Der Auth-Helfer darf das OpenHands-Ausführungs-SDK nicht importieren. Native ACP-Kontokommandos liegen gemeinsam in `native_agents.py`; tatsächliche Agentenausführung bleibt im SDK. Ohne vorhandenen Link zeigt die UI Vorbereitung statt einer Aufforderung zum Öffnen.

8-GB-NAS: Keinen zweiten vollständigen Test-Stack gleichzeitig mit dem Canvas-Build starten. Ein solcher Test verursachte Speicherdruck und SSH-Aussetzer; nur eigene Testcontainer stoppen, keine fremden NAS-Dienste.

Repository-Workspaces: SDK-Klonpfad wiederverwenden, nur GitHub-Katalogeinträge
zulassen, pro Start einen eigenen Checkout. Stage-Verzeichnisse auch bei Fehlern
entfernen und PAT aus origin entfernen, bevor der Pfad an Canvas zurückgeht.
`github_token` ist nach der Normalisierung der kanonische GitHub-Schlüssel.

Nativer Task-Harness: `openhands` startet `OpenHandsAgentSettings.create_agent()`
über das vorhandene RemoteConversation-API. Das gespeicherte OmniRoute-Profil
wird nur serverseitig mit Secrets gelesen; Discovery liefert ausschließlich
Modell-IDs. Modellwahl am Attempt speichern, bei Resume wiederverwenden und
vor Start gegen den Anbieter-Katalog prüfen. Kein leerer ACP-Befehl als Runner.

Native Session-Anbindung benötigt `openhands-tools` derselben SDK-Revision im
Integrationsdienst: RemoteConversation.attach importiert die gespeicherten
Werkzeugmodule zur Ereignis-Deserialisierung. Diese Abhängigkeit nicht durch
handgeschriebene Ereignismodelle ersetzen. Während dispatch.lock gehalten wird,
ist ein Attempt ohne Session noch in Vorbereitung; Polling darf ihn nicht als
abgebrochen markieren.

Der Ausführungs-Worktree steht im Checkpoint unter git.working_directory und
explizit im Handoff-Prolog; beim nativen Harness zusätzlich im Systemkontext.
Beads-Kontext enthält Herkunftspfade des kanonischen Projekts und darf diese
nicht als Schreibziel vermitteln. Dies ist Kontextführung, keine Dateisystem-
Sandbox: Worktrees allein sperren Zugriffe auf andere Projektpfade nicht.
