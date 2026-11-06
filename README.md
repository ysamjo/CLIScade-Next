# CLIScade Next

Ein gemeinsamer Entwicklungs-Workspace mit GitHub-Repositories als Projekten,
Beads als Aufgabenquelle und wechselbaren Coding-Agenten. OpenHands liefert
Canvas, Agent Server, Sessions und ACP-Transport. Der eigene OpenHands-Agent
verwendet OmniRoute; externe CLIs behalten ihren eigenen Harness und Kontologin.

**Stand 18. Oktober 2026, Version 0.11.0: Die Bausteine laufen, der gemeinsame
Projekt-/Task-Ablauf ist noch nicht vollständig verbunden.** Die frühere Aussage
„fünf Meilensteine implementiert“ bezeichnet die technischen Teilfunktionen,
nicht die vollständige Erfüllung der V1-Abnahmekriterien.

[Privates Repository](https://github.com/ysamjo/CLIScade-Next) ·
[Installation](deploy/README.md) · [Architektur](CLISCADE_NEXT.md) ·
[Testnachweise](cliscade/VALIDATION.md) · [Agenten-Prüfstand](cliscade/AGENTS_SUPPORTED.md)

## Verbindliches Zielbild

```text
Gemeinsamer Workspace mit GitHub-Zugang
└── Projekt = ein GitHub-Repository mit stabiler Identität
    ├── eine kanonische Beads-Aufgabenliste und Projektwissen
    └── Task mit Abnahmekriterien und Verlauf
        ├── Ausführungsweg: autorisierte ACP-CLI oder OpenHands über OmniRoute
        ├── Modell: passend zum gewählten Agenten und Konto
        └── Runs → Sessions → Prüfbelege → Checkpoints → Kontextübergabe
```

Ein Task kann von Codex analysiert, von Claude Code implementiert und von
OpenCode geprüft werden. Der nächste Agent bekommt Aufgabe, Regeln,
Projektwissen, Entscheidungen, Git-Stand, Prüfergebnisse und offene Schritte.
Gemeinsam sind Projekt und Aufgabenwissen; parallele Änderungen laufen in
getrennten Worktrees. Anbieterinterne Gesprächshistorien werden nicht als
übertragbar behandelt.

## Was vorhanden ist und was fehlt

| Bereich | Vorhanden / geprüft | Noch offen |
|---|---|---|
| GitHub und Workspace | PAT serverseitig; unter „New Chat“ Auswahl aus bis zu 30 Repositories, letzte Auswahl und zehn zuletzt verwendete Namen persistent; privater Git-Zugriff und Feature-Branch live geprüft. Ein Repository wird genau einmal geklont: Projekt-ID und Projektverzeichnis bleiben stabil, ein zweiter Aufruf verwendet denselben Root und überschreibt keinen Arbeitsstand | Ein Repository-Klon und eine Beads-Liste sind noch nicht für jedes bestehende Projekt migriert; Altdaten aus der Zeit mit Zufallssuffix bleiben als Beads-lose Verzeichnisse liegen |
| Beads und Task-Verlauf | `/tasks`: Projekte, Aufgaben, Status, Prioritäten, Abhängigkeiten, ACP-Runs, Sessions, Checkpoints und Handoff; Backend-/Protokolltests und kontrollierte ACP-E2Es | GitHub-Auswahl und Task-Projekte sind getrennt. OpenHands lässt sich jetzt als Task-Run starten; freie New-Chat-Conversations werden nicht nachträglich Tasks zugeordnet |
| Agenten und Modelle | Sechs ACP-Agenten plus nativer OpenHands-Harness; native Anmeldung, Capability-/Modellerkennung; dynamische Modellwahl pro Start und Handoff. `live_verified` und die belegten Modelle stammen aus dem Ledger: abgeschlossener Lauf ohne Fehler und mit Spur (Kommando mit Exit-Code oder Änderung im Arbeitsbaum), nicht aus einer Konfigurationsangabe | Task-Auswahl filtert noch nicht zuverlässig auf autorisierte, nutzbare Konten. Auf dem NAS gemessen: `codex` verweigert mit `ACPAuthRequired`, `kiro` startet nicht (`Connection closed`), `opencode` und `openhands` sind belegt. Der Modellkatalog des Gateways umfasst über 4000 Einträge; gefiltert wird im Feld, nicht serverseitig |
| OpenHands und OmniRoute | Profil `OmniRoute`, Modell `openai/c1`; nativer Beads-Task mit exaktem Datei-/Werkzeugnachweis und persistiertem Run geprüft | OpenHands ist als Ausführungsweg im Beads-Task-Runner mit gemeinsamem Verlauf verfügbar. `c1` ist eine Gateway-Kombination; nicht jeder enthaltene Anbieter ist damit einzeln verifiziert |
| Orchestrierung und Betrieb | Strukturierter Handoff, Routing, vorsichtiger Fallback, unabhängiger Konsens und native Automation implementiert; NAS-Compose, persistente Volumes und private Tailscale-Serve-Routen vorhanden. Zeitpläne sind gesperrt, bis `CLISCADE_ALLOW_UNATTENDED=1` gesetzt ist. Gemischter Wechsel live belegt: `opencode` → `openhands` → `opencode` auf einem Worktree, Datei und Entscheidungen bleiben erhalten, Quellprojekt unberührt, nach Dienstneustart unverändert lesbar | Offen: Neustart des Agent Servers mitten in einer Session, weitere Anbieterkonten, vollständiger Restore, strengere Sandbox-Betriebsarten. Worktrees bleiben keine Dateisystemgrenze |

Die neue Repository-Auswahl ist ein Übergangsschritt, keine fertige gemeinsame
Projektverwaltung. Siehe [genaues Workspace-Verhalten](deploy/REPOSITORIES.md).
Der jüngste gemischte Lauf auf dem NAS legte die angeforderte Datei mit exaktem
Inhalt inklusive abschließendem Zeilenumbruch an, änderte nichts außerhalb des
Worktrees und ließ das Quellprojekt sauber. Der frühere Befund (fehlender
Zeilenumbruch) ist damit überholt; die Prüfung bleibt Teil jedes Abnahmelaufs.

## Nächste Umsetzung, in dieser Reihenfolge

1. **Ein Repository = ein Projekt:** erledigt in 0.11.0. Projekt-ID und
   Projektverzeichnis entstehen einmal aus `owner/repo`, ein zweiter Aufruf
   verwendet denselben Root, und der Worktree erhält einen Verweis auf die
   kanonische Beads-Liste statt einer zweiten Datenbank. Offen bleibt die
   Migration der Altdaten aus der Zeit mit Zufallssuffix.
2. **Task-Einstieg vereinheitlichen:** OpenHands/OmniRoute ist neben ACP im
   vorhandenen Attempt-/Checkpoint-Modell verfügbar. Start, Abbruch, Wiederaufnahme
   und Handoff verwenden denselben Verlauf. Der New-Chat-Einstieg muss noch in
   diesen Ablauf überführt werden.
3. **Agent und Modell auswählen:** Installation, Anmeldung, Discovery und echte
   Ausführung als getrennte Zustände darstellen. `live_verified` und die belegten
   Modelle kommen jetzt aus dem Ledger; Kontofilter und Freigabezustände fehlen noch.
4. **Gemeinsamen Ablauf beweisen:** in 0.12.0 für einen Pfad erledigt — privates
   Repository, Task, CLI `opencode`, Übergabe an `openhands`, Rückübergabe an
   `opencode`, ein Worktree, Datei und Entscheidungen erhalten, Quellprojekt
   unberührt, nach Dienstneustart lesbar. Offen: Neustart des Agent Servers mitten
   in der Session, ein zweiter CLI-Anbieter mit echtem Konto, ein Prüf-Agent als
   dritter Hop.
5. **V1 abschließen:** Konto-/Provider-E2Es, Konsens und Scheduler auf diesem
   gemeinsamen Pfad prüfen; Restore und Installation dokumentiert wiederholen.

## Grenzen des Konzepts

- **ACP stellt nicht die gesamte Konsole dar.** Modellwahl und Funktionen hängen
  von der tatsächlich angebotenen ACP-Schnittstelle des Agenten ab. Nicht
  angebotene Konsolenfunktionen werden als nicht verfügbar angezeigt; kein
  provisorischer Terminal-/Headless-Wrapper.
- **Anmeldung und Modelle gehören zum Anbieter.** Ein Google-Login ist nur möglich,
  wenn dessen CLI ihn unterstützt. Vorhandene Konten garantieren weder jedes
  Modell noch erfolgreiche Inferenz. Antigravity und CodeBuddy bleiben priorisiert;
  ihr konkreter Nachweis steht in der Agentenliste.
- **Die Harnesses konkurrieren nicht, wenn die Zuständigkeit eindeutig ist.** Bei
  ACP steuert die externe CLI ihre Werkzeuge und Modellaufrufe. Bei OpenHands
  übernimmt das OpenHands; OmniRoute vermittelt dessen Modellzugriff. Sie sind
  alternative Ausführungswege mit gemeinsamem Task-Kontext.
- **Handoff überträgt belegbaren Arbeitsstand.** Er überträgt keine verborgenen
  Gedankengänge oder identische Anbieter-Sessions. Fakten/Prüfbelege und ungeprüfte
  Agentenaussagen bleiben getrennt; nach möglichen Änderungen kein blindes Replay.
- **GitHub ist die Remote-Quelle.** Agenten arbeiten in lokalen Checkouts und
  Worktrees. Erst nach geprüftem Commit/Push/PR sind Änderungen auf GitHub;
  ein PAT allein veröffentlicht nichts. Worktrees isolieren Git-Änderungen,
  ersetzen aber keine Sicherheits-Sandbox.

## Lokale Ablage und Dokumentation

- Canvas/Integration: `/Users/family/Developer/CLIScade-Next`.
- SDK-/Agent-Server-Anpassungen: `/Users/family/Developer/CLIScade-Next-SDK`.
- Deployment und ZimaOS-Kachel: [deploy/README.md](deploy/README.md).
- OmniRoute und CLI-Auswahl: [deploy/OMNIROUTE.md](deploy/OMNIROUTE.md).
- Offene Betriebs-/Anbieterpunkte: [cliscade/OPEN_POINTS.md](cliscade/OPEN_POINTS.md).

Änderungen bleiben auf Feature-Branches mit Pull Requests. Das ursprüngliche
CLIScade-Repository und dessen ACP-Draft #4 werden nicht automatisch gemergt.

Gezielte CI-Prüfung ohne Browser oder Anbieterzugang:
`npx vitest run .agents/skills/verify-openhands/scripts/control-openhands.test.mjs`
prüft unter anderem Pause und Fortsetzen eigener Prozesse. Die Testprozesse
veröffentlichen ihre Lebenszeichen atomar; der Test wartet auf tatsächlichen
Fortschritt statt auf eine feste Start- oder Fortsetzungsdauer.
`cliscade/.venv/bin/python -m pytest cliscade/tests/test_deployment.py -q`
prüft die private Compose-Konfiguration einschließlich portfreiem Integrationsdienst.

Die folgende Dokumentation beschreibt die übernommene OpenHands-Basis.

---

<a name="readme-top"></a>

<div align="center">
  <img src="https://assets.openhands.dev/logo-whitebackground.png" alt="OpenHands logo" width="340">
  <h1 align="center" style="border-bottom: none">Agent Canvas</h1>
  <p align="center">
    <strong>The self-hosted developer control center for coding agents and automations.</strong>
  </p>
  <p align="center">
    Run OpenHands, Claude Code, Codex, Gemini, Pi, OpenCode, or any ACP-compatible agent across local, remote, and cloud backends.
  </p>
</div>
<div align="center">
  <a href="https://github.com/OpenHands/incubator-program"><img src="https://img.shields.io/badge/status-beta-blue?style=for-the-badge" alt="Project status beta"></a>
  <a href="https://github.com/OpenHands/OpenHands/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/OpenHands/OpenHands/ci.yml?branch=main&style=for-the-badge" alt="CI status"></a>
  <a href="https://www.npmjs.com/package/@openhands/agent-canvas"><img src="https://img.shields.io/npm/v/%40openhands%2Fagent-canvas?style=for-the-badge&logo=npm" alt="npm version"></a>
  <a href="https://docs.openhands.dev/openhands/usage/agent-canvas/backends"><img src="https://img.shields.io/badge/Documentation-000?logo=googledocs&logoColor=FFE165&style=for-the-badge" alt="Documentation"></a>
  <a href="https://go.openhands.dev/slack"><img src="https://img.shields.io/badge/Slack-Join%20the%20community-611f69?logo=slack&logoColor=white&style=for-the-badge" alt="Join us on Slack"></a>
</div>
<div align="center">
  <a href="#quickstart">Quickstart</a> |
  <a href="./docs/README.md">Docs</a> |
  <a href="./docs/SELF_HOSTING.md">Self-Hosting</a> |
  <a href="https://docs.openhands.dev/openhands/usage/agent-canvas/acp-agents">ACP Agents</a> |
  <a href="https://docs.openhands.dev/openhands/usage/agent-canvas/prebuilt-automations">Automations</a> |
  <a href="https://go.openhands.dev/slack">Slack</a>
</div>
<p align="center">
  <img src="https://assets.openhands.dev/screenshot/automation-preview.png" alt="Agent Canvas automation preview" width="100%">
</p>
<hr>

OpenHands Agent Canvas turns your coding agents into a self-hosted, always-on engineering team. It's a developer control center for starting conversations and automating everyday tasks — like generating reports that publish to Slack or automatically decomposing GitHub issues into tasks.

It runs locally on your machine by default, but can connect to multiple “agent backends”, e.g. running agents in Docker containers, on VMs, or within your company infrastructure. You can optionally choose to run agents on OpenHands Cloud or OpenHands Enterprise infrastructure.

Agent Canvas runs the open source OpenHands agent out-of-the-box, but can use third-party agents such as Claude Code, Codex, Gemini CLI, Pi, and OpenCode.

|                                                                                                                      |                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [**Self-host your way**](https://docs.openhands.dev/openhands/usage/agent-canvas/backend-setup/vm)                   | Run agents locally, in Docker, on VMs, or anywhere you can run an agent server backend                                                   |
| [**Switch between different backends**](https://docs.openhands.dev/openhands/usage/agent-canvas/backends)            | Switch between local, remote, and cloud agents without losing focus                                                                      |
| [**Create automations**](https://docs.openhands.dev/openhands/usage/agent-canvas/prebuilt-automations)               | Create automations and workflows that integrate with Slack, GitHub, Linear, and more. Run on a schedule or in response to webhook events |
| [**Integrate with the tools you use**](https://docs.openhands.dev/openhands/usage/agent-canvas/prebuilt-automations) | Connect your automations with third-party services like Slack, GitHub, Notion, and more to automate workflows                            |
| [**Bring your own model**](https://docs.openhands.dev/openhands/usage/settings/llm-settings#llm-profiles)            | Use with any LLM                                                                                                                         |
| [**Use with any agent**](https://docs.openhands.dev/openhands/usage/agent-canvas/acp-agents)                         | Use with OpenHands, Claude Code, Codex, Gemini, Pi, OpenCode, or any agent with Agent-Client Protocol (ACP).                             |

If you have questions or feedback, please open a GitHub issue or join the [#proj-agent-canvas channel in Slack](https://openhands.dev/joinslack).

## Quickstart

You can install OpenHands to run agents on any machine: on your laptop, on a dedicated computer like a Mac Mini,
or on a server in the cloud.

The most powerful way to run OpenHands is on a server in the cloud. This allows your agents to continue running
even when your laptop is shut, and makes it easier to trigger your agents through third-party services
like Slack, GitHub, and Datadog. See [SELF_HOSTING.md](docs/SELF_HOSTING.md) for details, especially with respect to security hardening.

Notably, you can run the backend in _multiple different environments_, and switch between
them from the same Agent Canvas frontend. E.g. you can share an Agent Server with your team for agents doing
code review and dependency updates, then have your personal agents running on your laptop.

### Option 1: Without a Sandbox

> [!WARNING]
> This runs the agent-server directly on the machine you're installing on — the agent will have full access to your filesystem!

**Prerequisites**: [Node.js](https://nodejs.org/) 24 or later, `uv`

```sh
npm install -g @openhands/agent-canvas
agent-canvas
```

The `agent-canvas` command starts the full local stack by default. You can also split it when you want to run pieces separately:

```sh
agent-canvas --frontend-only  # static frontend + ingress only
agent-canvas --backend-only   # agent server + automation backend + ingress only
```

### Option 2: With a Docker Sandbox

**Prerequisites**:

- Docker: Docker Desktop on macOS/Windows, or Docker Engine/Docker Desktop on Linux.
- A host directory for `PROJECTS_PATH` containing the project folders you want the agent to access. Create it before starting the container.

**macOS / Linux:**

```sh
export PROJECTS_PATH="$HOME/projects"  # directory containing your project folders
mkdir -p "$PROJECTS_PATH" "$HOME/.openhands"

docker run -it --rm \
  -p 127.0.0.1:8000:8000 \
  -e AGENT_CANVAS_ALLOW_LAN_SESSION_KEY=true \
  -v "$HOME/.openhands:/home/openhands/.openhands" \
  -v "${PROJECTS_PATH}:/projects" \
  ghcr.io/openhands/agent-canvas:1.27.1 # x-release-please-version
```

**Windows (PowerShell / Windows Terminal):** See [README.windows.md](./README.windows.md) for the equivalent commands.

The agent will be able to access any project under `PROJECTS_PATH`.

### Option 3: With Multiple Docker Sandboxes

Run each new conversation in its own Docker container, with its own Agent Server and tools. This is useful for running several agents concurrently. Canvas and the outer Agent Server run on your host and route conversation requests to the containers.

**Prerequisites**: Node.js 24 or later, `uv`, and a running Docker Desktop (macOS) or Docker Engine/Desktop (Linux). The user starting Canvas must be able to run `docker` commands.

**macOS / Linux:**

```sh
npm install -g @openhands/agent-canvas
OH_CONVERSATION_RUNTIME=docker agent-canvas
```

Open [http://localhost:8000](http://localhost:8000) and start a new conversation. Existing local conversations are not converted. Each container mounts its conversation's workspace and persisted state, so workspace files and conversation history survive container replacement. Conversations using the same host workspace still share those files; choose separate directories or worktrees to avoid conflicting edits.

This setting isolates conversation execution; it does not move the entire Canvas or automation service into a sandbox. For Windows, see [README.windows.md](./README.windows.md#option-3-with-multiple-docker-sandboxes-wsl-2).

### Option 4: From Source

> [!WARNING]
> This runs the agent-server directly on the machine you're installing on — the agent will have full access to your filesystem!

**Prerequisites**: [Node.js](https://nodejs.org/) 24 or later, `npm`, `uv` (for running the agent server via `uvx`)

```sh
git clone https://github.com/OpenHands/OpenHands.git
cd OpenHands
npm install
npm run dev
```

---

Access the UI at [http://localhost:8000](http://localhost:8000) for the npm/source launchers, or [http://localhost:8000/canvas](http://localhost:8000/canvas) for the Docker image. You can add additional backends directly from the UI.

Local (`npx` / `npm run dev`) listeners bind **loopback only** (`127.0.0.1`) so the auto-injected session key is not reachable from other machines on the network. To listen on all interfaces, pass `--host 0.0.0.0` (or set `OH_BIND_HOST`); the session key is then **not** injected and the UI uses the same API-key entry screen as `--public`.

Docker listens on all container interfaces so port publishing works, but does not inject its session key into HTML by default. The quickstart above explicitly enables injection while publishing the host port on `127.0.0.1` only. If you publish Docker on a LAN or public interface, omit `AGENT_CANVAS_ALLOW_LAN_SESSION_KEY` and enter the API key in the UI. Set `LOCAL_BACKEND_API_KEY` to a strong value, or retrieve the generated value with `docker exec <container> sh -c 'cat "$STATE_DIR/api-key.txt"'`. For internet-facing installs, follow [self-hosting](./docs/SELF_HOSTING.md).

# Architecture

Agent Canvas is powered by the [OpenHands Agent Server](https://github.com/OpenHands/software-agent-sdk/tree/main/openhands-agent-server/openhands/agent_server), a REST API for running multiple agents on a single machine. Each Agent Server runs on a single host/port; the Agent Canvas can connect to multiple Agent Servers and easily flip between them.

You can run an Agent Server anywhere:

- Directly on your laptop (be careful!)
- On a dedicated machine like a Mac Mini
- On a virtual machine in the cloud
- Inside OpenHands Cloud (our commercial offering)

The Agent Server is often paired with an [Automation Server](https://github.com/OpenHands/automation), which lets you set up agents that run on a schedule or in response to events.

<img width="1456" height="1258" alt="image" src="https://github.com/user-attachments/assets/cb6de6f5-ac30-4d04-a76a-b5c259f0c163" />

### Repository boundaries

Agent Canvas is part of a multi-repository OpenHands system. Changes should go to the repository that owns the behavior:

| Repository                                                                        | Responsibility                                                                                            |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| [`OpenHands/OpenHands`](https://github.com/OpenHands/OpenHands)                   | Agent Canvas frontend, user-facing control center, backend selection, and local-stack orchestration.      |
| [`OpenHands/software-agent-sdk`](https://github.com/OpenHands/software-agent-sdk) | Python SDK, Agent Server, agents, tools, conversations, workspaces, events, and the canonical server API. |
| [`OpenHands/typescript-client`](https://github.com/OpenHands/typescript-client)   | Browser-compatible TypeScript client for the Agent Server API.                                            |
| [`OpenHands/automation`](https://github.com/OpenHands/automation)                 | Automation definitions, scheduling, webhooks, run history, and dispatching.                               |

The Agent Server API is implemented by the SDK and consumed through the TypeScript client by Agent Canvas. The automation service decides when work runs and dispatches conversations to the Agent Server/SDK, which decides what runs. See [`AGENTS.md`](./AGENTS.md) for contributor-specific boundaries and the required custom code-review guide.

## More documentation

- [Documentation index](./docs/README.md)
- [Architecture overview](./docs/architecture.md)
- [Development guide](./docs/DEVELOPMENT.md)
- [Self-hosting guide](./docs/SELF_HOSTING.md)

CLIScade Next 0.5: [Private ZimaOS-Installation](deploy/README.md),
[Konsens und native Automationen](cliscade/README.md),
[Prüfnachweise und verbleibende Grenzen](cliscade/VALIDATION.md).
