# CLIScade Next

Privates eigenständiges Repository auf Basis von OpenHands Agent Canvas.
OpenHands-Upstream bleibt als Git-Remote erhalten. Änderungen werden über
Feature-Branches und Pull Requests geprüft; das bestehende CLIScade und dessen
ACP-Draft #4 werden nicht verändert oder gemergt.

## Architekturentscheidung

Canvas bleibt die Oberfläche. Der OpenHands Agent Server hält Conversations,
ACP-Prozesse und Ereignisse unabhängig vom Browser. Das Python-Paket `cliscade/`
ergänzt die fachliche Beads-Integration und Orchestrierung und verwendet den
offiziellen Python-SDK-Client. Es implementiert keinen eigenen ACP-Transport.
OpenHands Automation bleibt Eigentümer von Zeitplanung und Dispatch.

| Begriff | Eigentümer | Persistenz |
|---|---|---|
| Fachaufgabe, Abnahme, Priorität, Abhängigkeiten, Projektwissen | Beads | Projekt-`.beads/`, Dolt |
| Agent-Session und Werkzeugereignisse | OpenHands | Agent-Server-Persistenz |
| Run/Attempt | CLIScade | Ledger mit Beads-ID und Conversation-ID |
| Checkpoint | CLIScade | Versionierter Kontext und Git-Belege im Ledger |

Das Ledger ist keine Task-Datenbank. Task-Texte im Checkpoint sind unveränderliche
Momentaufnahmen; jede neue Ausführung liest die Aufgabe frisch aus Beads.
Anbieterwechsel erzeugt eine neue Conversation mit strukturiertem Kontext.
Anbieterinterne Historie wird nicht importiert.

## Migration

Aus CLIScade werden Regeln übernommen: Projekt-Locks, priorisierte Routen,
kein automatisches Replay nach Prompt-Übermittlung, 64.000-Zeichen-Kontextbudget,
ungeprüfte Agentenaussagen und native Beads-Backups. `services/context-service.js`,
`services/beads-adapter.js`, `services/beads-backup.js` und PR #4 sind Referenzen,
keine kopierten Server-Implementierungen. Bestehende CLIScade-SQLite-Aufgaben
werden nicht automatisch importiert oder als Beads-Aufgaben ausgegeben.

## Entwicklung

```sh
cd cliscade
uv sync --frozen
uv run pytest
uv run ruff check .
```

Node 24 oder neuer für Canvas; Python 3.13 oder neuer für die Integration.
Das vorhandene Canvas-README beschreibt dessen unveränderte Startbefehle.

## Meilensteine und Nachweisgrenzen

1. Repository, Herkunft, Entwicklungsumgebung und Projektgrenzen.
2. Durchgängiger Backend-Ablauf Beads → ACP → Attempt → Handoff.
3. Projektorientierte responsive Canvas-Oberfläche.
4. Capability-Erkennung, Routing und abgesicherter Fallback.
5. Unabhängiger Konsens, OpenHands Automation und ZimaOS/Tailscale.

Mock-Tests, Protokolltests und authentifizierte Anbieter-Tests werden getrennt
ausgewiesen. Ein vorhandenes Binary gilt nicht als erfolgreiche Integration.

## Herkunft und Lizenz

OpenHands Canvas, SDK und Automation verwenden in den untersuchten Revisionen
MIT; Beads ebenfalls MIT. Die originalen Lizenz- und Copyright-Hinweise bleiben
erhalten. Agenten und ACP-Adapter haben eigene Lizenz-, Installations- und
Authentifizierungsbedingungen und werden nicht durch diese Lizenz freigegeben.
ACP ist die Protokollspezifikation; der SDK-Transport wird wiederverwendet.
Beads ist inzwischen von `steveyegge/beads` nach `gastownhall/beads` umgezogen.
