# Offene Punkte vor vollständiger V1-Freigabe

Der durchgängige Slice, Konsens, native Zeitpläne und der private Docker-Stack
sind implementiert und mit kontrollierten ACP-Prozessen geprüft. Vollständige
Anbieterfreigabe und sämtliche Betriebsarten werden damit nicht behauptet.

1. **Anbieter und Anmeldung auf dem NAS:** Claude Code und Kiro bestanden lokale
   authentifizierte Datei-E2Es. Für NAS-Container fehlen eingerichtete Logins.
   Das offizielle Agent-Server-Image benötigt für Kiro zusätzlich ein Image mit
   offizieller Linux-CLI. Keine lokalen Logins still übertragen.
2. **Codex und OpenCode:** Codex lehnt das vorhandene Konto-/Modellpaar ab;
   OpenCode erzeugte im Datei-E2E keine angeforderte Datei. Modell/Provider-
   Konfiguration prüfen und beide Datei-E2Es erneut bestehen lassen. Claude-
   Server-Test scheiterte am Gateway-Rate-Limit; ebenfalls erneut prüfen.
3. **Weitere ACP-Agenten:** Cline, Cursor, Copilot, Junie, Kilo, Qoder und Vibe
   haben offizielle Registry-Einträge, sind aber nicht als Produktadapter
   freigegeben. Vor Freigabe Capability-, Permission-, Abbruch-, Secret- und
   Datei-E2Es prüfen. Keine Headless-/PTY-Ersatzadapter ergänzen.
4. **Isolation und Plattformen:** Per-Conversation-Docker-Discovery ist upstream
   HTTP 501. Der getestete Stack isoliert den Agent Server im Container und
   Änderungen über Worktrees. Strengere Isolation sowie vollständiger arm64-
   Build/Lauf bleiben zu prüfen. Direkter Mac-Tailnet-Zugriff war nicht verfügbar.
5. **Betrieb und Upstream-Basis:** Geerbte Cloud-Onboarding-Testfehler und 40
   npm-Audit-Funde (2 kritisch) separat bearbeiten. Backup-Retention, externe
   Kopie, vollständiger Server-Restore und expliziter Import alter CLIScade-
   SQLite-Aufgaben fehlen. Der HUMAN-Check auf PR #1 verwendet bis zur Übernahme
   weiterhin den alten vertrauenswürdigen main-Validator; keine menschliche
   Bestätigung fingieren.
