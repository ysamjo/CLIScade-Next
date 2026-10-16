# ACP-Agenten: Implementierung und Prüfstand

Prüfstand: 16. Oktober 2026. Produktintegration, ACP-Handshake und authentifizierte Arbeit sind getrennte Nachweise. Die Startbefehle der ersten drei Agenten kommen aus der gepinnten OpenHands-SDK-Registry.

| Agent | Startkommando | Nachweis |
|---|---|---|
| Claude Code | `npx -y --prefer-offline @agentclientprotocol/claude-agent-acp@0.63.0` | Authentifizierter lokaler Datei-E2E bestanden |
| Codex | `npx -y --prefer-offline @agentclientprotocol/codex-acp@1.10.0` | Handshake bestanden; Datei-E2E gescheitert: lokales Modell gpt-6.1-sol wird mit ChatGPT-Anmeldung abgewiesen |
| OpenCode | `npx -y --prefer-offline opencode-ai@1.18.23 acp` | ACP antwortet; Datei-E2E erzeugte keine angeforderte Datei. Nicht vollständig unterstützt |
| Kiro | `kiro-cli acp` | Kiro 2.31.1: Handshake, neun gemeldete Modelle und authentifizierter Datei-E2E bestanden |

Die lokalen Datei-E2Es sind keine Behauptung über vorhandene Logins im späteren NAS-Container. Dort müssen Anbieter über die bestehenden OpenHands-Secrets beziehungsweise die jeweilige CLI-Anmeldung konfiguriert und erneut geprüft werden.

## Weitere Implementierungen

Die offizielle ACP-Registry führt die folgenden Implementierungen. Ein Registry-Eintrag beweist keine funktionierende CLIScade-Integration. Diese Agenten sind in V1 derzeit nicht freigegeben; keine Terminal-/Headless-Ersatzadapter.

| Agent | Registry-Version | Distribution | Produktstatus |
|---|---|---|---|
| Cline | 3.0.71 | `npx --yes cline@3.0.71 --acp` | Nicht live verifiziert, nicht freigegeben |
| Cursor | 2026.10.14 | `Binary; Plattformliste im Katalog` | Nicht live verifiziert, nicht freigegeben |
| Copilot | 1.554.0 | `npx --yes @github/copilot-language-server@1.554.0 --acp` | Nicht live verifiziert, nicht freigegeben |
| Junie | 3659.4.0 | `Binary; Plattformliste im Katalog` | Nicht live verifiziert, nicht freigegeben |
| Kilo | 7.8.12 | `npx --yes @kilocode/cli@7.8.12 acp` | Nicht live verifiziert, nicht freigegeben |
| Qoder CLI | 0.2.14 | `npx --yes @qoder-ai/qodercli@0.2.14 --acp` | Nicht live verifiziert, nicht freigegeben |
| Mistral Vibe | 2.26.1 | `Binary; Plattformliste im Katalog` | Nicht live verifiziert, nicht freigegeben |
| Gemini CLI | 0.64.0 | `npx --yes @google/gemini-cli@0.64.0 --acp` | Nicht live verifiziert, nicht freigegeben |
| pi ACP | 0.0.34 | `npx --yes pi-acp@0.0.34 ` | Nicht live verifiziert, nicht freigegeben |
| Codebuddy Code | 2.168.0 | `npx --yes @tencent-ai/codebuddy-code@2.168.0 --acp` | Nicht live verifiziert, nicht freigegeben |
| Google Antigravity | 1.4.0 | `Binary; Plattformliste im Katalog` | Nicht live verifiziert, nicht freigegeben |
| Grok Build | 1.0.60 | `npx --yes @xai-official/grok@1.0.60 agent stdio` | Nicht live verifiziert, nicht freigegeben |

Quellen und Plattformartefakte: `agent-catalog.json`; die Herkunftsrevision steht in `upstream.json`. Kiro: https://kiro.dev/docs/cli/acp/.

## Routing konfigurieren

`CLISCADE_AGENT_CONFIG` zeigt auf eine lokale JSON-Datei. Beispiel:

```json
{"claude-code":{"priority":10,"enabled":true,"capabilities":["coding","review","analysis"]},"codex":{"priority":20},"kiro":{"priority":30},"opencode":{"priority":40}}
```

Optional `model` auf eine tatsächlich nutzbare, gemeldete Modell-ID setzen. Ein gemeldetes Modell ist noch kein Inferenznachweis. Keine API-Schlüssel in dieser Datei.

Automatik fragt `/api/acp/models` des OpenHands Agent Servers ab. Fehler oder unpassende Modelle überspringen den Kandidaten vor dem Prompt. Nach einer Start-/Versandunsicherheit endet die Kaskade sichtbar. Die übersprungenen Kandidaten stehen dauerhaft im Attempt-Ledger.

Aktuelle Upstream-Grenze: `/api/acp/models` liefert bei `conversation_runtime=docker` HTTP 501. Automatische Vorabprüfung ist daher nur für den getesteten In-Process-Agent-Server verfügbar (auch wenn dieser selbst in einem abgeschotteten Docker-Container läuft). Per-Conversation-Docker-Sandboxes und deren Discovery müssen separat geprüft/erweitert werden; diese Lücke wird nicht als implementiert ausgegeben.
