# F29 — CLIScade Beads-Aufgaben

Route `/tasks`, erreichbar über die Seitenleiste **Projekte & Aufgaben**.
Source: `src/routes/cliscade-tasks.tsx`, `src/api/cliscade-service.ts`,
`src/utils/beads-task-tree.ts`, `src/components/features/cliscade`, `cliscade/src/cliscade_next/api.py`.

## Sub-features

- `F29.project`: Projektliste des freigegebenen Projektverzeichnisses öffnen.
- `F29.tasks`: Hierarchie anhand kanonischer Beads-Elternbeziehungen anzeigen.
- `F29.create`: Titel, Beschreibung, Abnahme, Priorität und optionale Elternaufgabe speichern; nach Reload wiederfinden.
- `F29.edit`: Aufgabe bearbeiten, eine Abhängigkeit hinzufügen und Status ändern.
- `F29.attempts`: Mehrere Ausführungen mit Agent, Status und Session-Link sehen.
- `F29.handoff`: Beendeten Attempt an den ausgewählten ACP-Agenten oder nativen OpenHands-Agenten übergeben.
- `F29.model`: Dynamische Modelle je Agent auswählen, im Attempt sehen und bei Resume erhalten.
- `F29.openhands`: Beads-Task über den nativen SDK-Harness und das OmniRoute-Profil ausführen.
- `F29.checkpoint`: Git-Diff, Werkzeugbelege und strukturierten Checkpoint lesen.
- `F29.mobile`: Bei 390 px alle Aktionen ohne horizontalen Seiten-Scroll erreichen.

- `F29.routing`: Automatische Route und übersprungene Anbieter anzeigen.
- `F29.consensus`: Zwei bis vier unabhängige Worktrees starten und Unterschiede vergleichen.
- `F29.schedule`: Native OpenHands-Automation anlegen und verwalten.
- `F29.backup`: Native Beads-Sicherung samt Wiederherstellungsprüfung auslösen.

- `F29.login`: Native CLI-Konten per Anbieterlink/Gerätecode anmelden, Status prüfen und eigenen Login abbrechen.

## How to get to it (user POV)

Seitenleiste → Projekte & Aufgaben oder direkte Route `/tasks`.

## Driving it with control-openhands

Preconditions: echter Agent Server, CLIScade-Dienst und ein Beads-Testprojekt.

Für dieses Projekt gilt die Benutzervorgabe Ego Lite. Bestehenden TaskSpace
wiederverwenden; keine zusätzlichen Browserinstanzen über control-openhands.
Die normalen `control-openhands map`-Befehle bleiben für Abdeckung nutzbar.

Voraussetzungen: echter Agent Server, laufender CLIScade-Dienst, Vite-Proxy für
`/cliscade`, ein mit `bd init` eingerichtetes Wegwerfprojekt. Im Browser
`/tasks?project=<projekt>` öffnen, Formular ausfüllen und speichern. Seite neu
laden; angelegte Aufgabe auswählen. Nur mit explizit verfügbarem Anbieterlogin
Ausführung starten. Protokoll-Fixture und Anbieter-Inferenz getrennt belegen.
Desktop- und Smartphone-Screenshots sowie sichtbare Fehler dokumentieren.

## Gotchas

Unitäre Regression: `npx vitest run __tests__/routes/cliscade-tasks.test.tsx`.

Login-Regression: `npx vitest run __tests__/routes/cliscade-login.test.tsx __tests__/root.test.tsx`.

0.7.0: `F29.login` umfasst Antigravity als erste Auswahl (Google OAuth Personal,
localhost-Rückleitung) und CodeBuddy (internationales Portal, native Abfrage des
Anmeldestatus). Bei Kiro/OpenCode Google wählen, soweit angeboten. Das geprüfte CodeBuddy-CLI-Portal
zeigt E-Mail/OneID/SSO, keinen Google-Button; Google dort nicht bestätigt.
Ein Login-Start ist kein Nachweis einer persönlichen Freigabe oder Inferenz.
`deploy/verify-login.py` prüft alle sechs nativen Starts und den gezielten Abbruch.

0.7.1: Während pending ohne URL zeigt F29.login die Vorbereitung des Links an.
Erst mit vorhandener URL folgt die Aufforderung zum Öffnen. Regression:
`cliscade-login.test.tsx` prüft verspätete Links mit echtem Query-Polling.

Canvas 0.7.2: F29.login zeigt den vollständigen nativen Anmeldelink readonly.
„Link kopieren“ schreibt exakt diese URL und meldet Erfolg erst danach. Bei
gesperrter/fehlender Clipboard-API wird das Feld zum manuellen Kopieren markiert.
Agentenwechsel entfernt URL und Kopiermeldung. Tests: `cliscade-login.test.tsx`.

0.10.0: Im Beads-Task Agent `openhands` wählen. Der Katalog wird automatisch
geladen; „Agentenstandard“ verwendet `openai/c1`. Ein explizit gewähltes Modell
wird vor Start geprüft und im Attempt gespeichert. Agentenwechsel setzt die
Auswahl zurück. Quelle: `agents.py`, `ledger.py`, `orchestrator.py`; Regression:
`test_native_harness.py`, `test_task_models.py`, `cliscade-tasks.test.tsx`.
