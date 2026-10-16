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
- `F29.handoff`: Beendeten Attempt an den ausgewählten ACP-Agenten übergeben.
- `F29.checkpoint`: Git-Diff, Werkzeugbelege und strukturierten Checkpoint lesen.
- `F29.mobile`: Bei 390 px alle Aktionen ohne horizontalen Seiten-Scroll erreichen.

- `F29.routing`: Automatische Route und übersprungene Anbieter anzeigen.
- `F29.consensus`: Zwei bis vier unabhängige Worktrees starten und Unterschiede vergleichen.
- `F29.schedule`: Native OpenHands-Automation anlegen und verwalten.
- `F29.backup`: Native Beads-Sicherung samt Wiederherstellungsprüfung auslösen.

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
