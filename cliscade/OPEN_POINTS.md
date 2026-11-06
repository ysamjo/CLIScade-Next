# Offene Punkte vor vollständiger V1-Freigabe

Der durchgängige Slice, Konsens, native Zeitpläne und der private Docker-Stack
sind implementiert und mit kontrollierten ACP-Prozessen geprüft. Vollständige
Anbieterfreigabe und sämtliche Betriebsarten werden damit nicht behauptet.

1. **Anbieter und Anmeldung auf dem NAS:** Claude Code und Kiro bestanden lokale
   authentifizierte Datei-E2Es. Für NAS-Container fehlen eingerichtete Logins.
   Version 0.6.1 ergänzt eine native Kontoanmeldung für vier CLIs und enthält
   Kiros offizielle Linux-CLI. Kontofreigabe und authentifizierte NAS-Datei-E2Es
   stehen noch aus. Keine lokalen Logins still übertragen. Stand 0.14.0:
   openhands (OmniRoute, openai/c1) und opencode (opencode/big-pickle) sind
   live belegt; codex=ACPAuthRequired, kiro=ACPInitError, claude-code,
   antigravity und codebuddy haben Modellisten, aber keinen belegten Lauf.
2. **Codex und OpenCode:** Codex lehnt das vorhandene Konto-/Modellpaar ab;
   OpenCode erzeugte im Datei-E2E keine angeforderte Datei. Modell/Provider-
   Konfiguration prüfen und beide Datei-E2Es erneut bestehen lassen. Claude-
   Server-Test scheiterte am Gateway-Rate-Limit; ebenfalls erneut prüfen.
   (Opencode hat inzwischen zwei belegte Läufe; der letzte Datei-E2E-Nachweis
   fehlt weiter.)
3. **Weitere ACP-Agenten:** Cline, Cursor, Copilot, Junie, Kilo, Qoder und Vibe
   haben offizielle Registry-Einträge, sind aber nicht als Produktadapter
   freigegeben. Vor Freigabe Capability-, Permission-, Abbruch-, Secret- und
   Datei-E2Es prüfen. Keine Headless-/PTY-Ersatzadapter ergänzen.
4. **Isolation und Plattformen:** Per-Conversation-Docker-Discovery ist upstream
   HTTP 501. Der Stack isoliert den Agent Server im Container; seit 0.13.0
   protokolliert die Isolation-Watch jeden Schreibzugriff außerhalb des
   Worktrees (Git-Zustand aller registrierten Projekte vor/nach dem Lauf,
   Bruch macht den Lauf unbelegt, Anzeige im Versuchsblock). Strengere
   Isolation — Container je Lauf — bleibt der nächste Schritt. arm64 ist
   geprüft, nicht ausgeführt: Agent-Server-Dockerfile schaltet pro Architektur
   (arm64-Checksums für kiro-cli und agy), `openhands/agent-server:1.55.1-python`
   führt amd64 und arm64, node/python-Basis sowie @beads/bd (cpu: x64, arm64)
   sind mehrarchitekturfähig. Ein arm64-Build/-Lauf auf echter Hardware oder
   buildx+qemu steht aus. Direkter Mac-Tailnet-Zugriff war nicht verfügbar.
5. **Betrieb und Upstream-Basis:** Geerbte Cloud-Onboarding-Testfehler und 40
   npm-Audit-Funde (2 kritisch) separat bearbeiten. Backup: native Beads-Sicherung
   mit Wiederherstellungsprüfung im Wegwerfprojekt existiert (Test + live
   `restore_verified: true`); Retention, externe Kopie, vollständiger
   Server-Restore und expliziter Import alter CLIScade-SQLite-Aufgaben fehlen.
   Verlassene Beads-Behauptungen werden seit 0.14.0 eingesammelt (Reaper alle
   10 Minuten; Force-Pfad mit Parallelitätsannahme). Der HUMAN-Check auf PR #1
   verwendet bis zur Übernahme weiterhin den alten vertrauenswürdigen
   main-Validator; keine menschliche Bestätigung fingieren.
