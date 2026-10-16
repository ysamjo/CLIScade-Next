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
