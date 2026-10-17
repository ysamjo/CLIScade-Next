# Repository Notes

## General

- This repository is the OpenHands Agent Canvas React/TypeScript frontend.

## i18n workflow
- After editing `src/i18n/translation.json`, run `npm run make-i18n` to
  regenerate `src/i18n/declaration.ts` (gitignored, auto-generated) and
  `scripts/check-translation-completeness.cjs` to confirm full locale coverage.
- Removing an i18n key: delete the whole locale block from translation.json,
  then `make-i18n`, then remove any test-mock entries (tests inline a
  `translations` map in the `useTranslation` vi.mock).

## Commit messages
- The persistent shell can garble long multi-line `commit -m` bodies (echo
  loop corrupts the stored message). Use `git commit -F <file>` with a
  written temp file instead of `-m` for any non-trivial message.

- Primary verification commands are `npm run lint`, `npm test`, `npm run build`, and `npm run build:lib`.
- Direct dependencies and dev dependencies are exact-pinned. Use the committed `package-lock.json` with `npm ci`, and update `package.json` and `package-lock.json` together through npm.
- Public skills come from `@openhands/extensions`; project-specific contributor guidance lives under `.agents/skills/`.
- Default working-directory behavior must reuse `DEFAULT_WORKING_DIR` from `src/api/agent-server-config.ts` rather than hardcoding `/workspace/project`.
- All pull requests must comply with [`.agents/skills/custom-codereview-guide.md`](.agents/skills/custom-codereview-guide.md), in addition to the general contribution requirements and CI checks.

## Repository Ownership

Before adding code, confirm that the change belongs in this repository.

| Repository | Owns | Add code there when… |
|---|---|---|
| [`OpenHands/OpenHands`](https://github.com/OpenHands/OpenHands) | Agent Canvas UI, frontend state, backend selection, frontend service integration, and local-stack orchestration. | Changing UI, frontend state, or how Canvas consumes an existing API. |
| [`OpenHands/software-agent-sdk`](https://github.com/OpenHands/software-agent-sdk) | Python SDK, Agent Server, agents/tools, conversations, events, canonical REST/WebSocket API, and `clients/typescript/`. | Adding or changing backend behavior, endpoints, wire contracts, or typed client access. |
| [`OpenHands/extensions`](https://github.com/OpenHands/extensions) | Reusable public skills, automations, plugins, and integrations. | Adding or editing reusable extension content rather than Canvas behavior. |
| [`OpenHands/automation`](https://github.com/OpenHands/automation) | Automation definitions, scheduling, webhooks, run history, and dispatch. | Changing when automations run or their scheduling/webhook lifecycle. |

The normal dependency direction is Agent Server contract → TypeScript client → Agent Canvas. Do not reimplement Agent Server endpoints or contracts in Canvas.

## Shared Frontend Change Checklist

Before changing a shared adapter, conversation builder, setting, state selector, or presentation helper:

- Raise `compatibility.minimumAgentServer` in `config/defaults.json` when Canvas begins requiring a new Agent Server endpoint, field, schema, or behavior.
- Enumerate affected consumers across Local and Cloud backends, OpenHands and ACP agents, standard/planning/delegated conversations, and standalone and embedded Canvas. Test every path with distinct control or data flow without testing an irrelevant Cartesian product.
- Give durable frontend state one named owner and one obvious writer. Handle existing-state hydration or migration and all supported create, update, delete, default, and active-item transitions. Leave destructive transitions in a deterministic valid state or an explicit empty state handled by the UI.

## PR-Beschreibungen

Für `ysamjo/CLIScade-Next` schreibt der ausführende Autor die Abschnitte `Why`, `Summary` und `How to Test` mit konkreten Ergebnissen und Grenzen. UI-Änderungen benötigen weiterhin Bild- oder Videonachweise. Eine menschliche Prüfung darf nur als solche bezeichnet werden, wenn sie tatsächlich stattgefunden hat; eine separate `HUMAN:`-Pflicht und das Upstream-Label `ready-for-dev` gelten hier nicht.

Bei Beiträgen an OpenHands gilt weiterhin dessen eigene HUMAN-Regel. Vorhandene menschliche Aussagen werden nicht umgeschrieben oder als Agententext ausgegeben.

## Functionality-Specific Skills

Detailed contributor knowledge is split into skills so it loads only for relevant work. Invoke every applicable skill before changing that area; cross-cutting changes may require several skills.

| Skill | Use for |
|---|---|
| [`telemetry-analytics`](.agents/skills/telemetry-analytics/SKILL.md) | PostHog, telemetry consent/identity, typed tracking events, Cloud funnel observability, and onboarding instrumentation. |
| [`e2e-testing`](.agents/skills/e2e-testing/SKILL.md) | Live or mock-LLM Playwright suites, Docker E2E, E2E CI/reporting, artifacts, and failure diagnosis. |
| [`frontend-api-contracts`](.agents/skills/frontend-api-contracts/SKILL.md) | `src/api`, typed Agent Server calls, Cloud/runtime transport, compatibility, backends, settings, secrets, auth, and conversation contracts. |
| [`local-stack-runtime`](.agents/skills/local-stack-runtime/SKILL.md) | Dev launchers, runtime-services metadata, ingress, automation startup, process shutdown, centralized versions, and Docker. |
| [`desktop-electron`](.agents/skills/desktop-electron/SKILL.md) | Electron startup, branding, packaging, bundled Node/uv, universal macOS builds, and desktop CI. |
| [`frontend-development`](.agents/skills/frontend-development/SKILL.md) | React/UI work, i18n, named identifiers, MSW mock mode, lazy loading, bundle performance, and feature-specific UI invariants. |
| [`pr-design-doc`](.agents/skills/pr-design-doc/SKILL.md) | Writing the PR design document stored in the PR body. |
| [`release`](.agents/skills/release.md) | Cutting and verifying an `@openhands/agent-canvas` release. |
| [`verify-openhands`](.agents/skills/verify-openhands/SKILL.md) | Driving the real app like a user with `control-openhands`, the feature map of every user-facing behavior, and creating or maintaining that map. |

The detailed rules live in each skill's `references/guide.md`; do not copy them back into this file. Update the owning skill whenever an invariant changes.

## Testing Baseline

Create TDD tests for behavioral changes. Keep tests focused on user behavior and real code paths:

- Use Arrange, Act, Assert structure and clear test data.
- Avoid duplicate cases and duplicate assertions.
- Mock an underlying service rather than the hook that consumes it.
- Extend an existing test file when it is a natural home; create a new file only when necessary.
- Avoid brittle presentation-only assertions. Test functional CSS contracts directly when they are behavior.
- Do not mirror literal source, fixture, translation, or class-string definitions in tests. Assert consumer behavior or an actual build/runtime contract instead, and do not export internals solely to make them testable. Preserve coverage for routing, accessibility, async behavior, behavioral contracts, and functional CSS/build contracts.
- Use the minimum number of cases that fully cover the intended behavior and edge cases.

Use the `e2e-testing` skill for suite selection and E2E-specific requirements.

## Specifications and Releases

- Spec files live under `specs/`. Keep spec IDs stable and mark deprecated specs with strikethrough rather than renumbering them.
- Tag implementation code and tests with `// @spec BM-002 — Short title` comments immediately above the relevant block so coverage remains grep-able.
- Follow `.agents/skills/release.md` for release automation. Never hand-edit a release-please branch.

## DigitalOcean Managed Agents

Before changing `scripts/mars-*` / `scripts/tunnel-*`, `src/api/mars/`, the Managed Agents UI (`src/components/features/backends/managed-agents/`) or the MARS hooks, read `src/api/mars/AGENTS.md`.

CLIScade-Deployment: `deploy/README.md` beschreibt den privaten Compose-Stack.
Eigene Images auf ZimaOS bauen; das produktive Compose enthält ausschließlich
Images, keine Variablensubstitution und keinen Docker-Socket. Bestehende
Tailscale-Routen erhalten, ausschließlich eine private Serve-Route ergänzen.

CLIScade-Kontoanmeldung: Die lokale Route `/tasks` öffnet die eigene CLI-
Kontoanmeldung ohne LLM-Profil-Onboarding. Backend-Zugriffskontrollen und Cloud-
Onboarding bleiben erhalten. Auth-UX liegt in `agent-login.tsx`, Auth-Befehle
und Lebenszyklus im Integrationsdienst, Agentenausführung ausschließlich im SDK.

CLIScade 0.7.0: Antigravity und CodeBuddy sind native ACP-Agenten. Der gepinnte
SDK-Fork startet Agenten im Workspace und wählt angebotene Auth-Methoden. Das
Agent-Server-Image führt dessen Python-Entrypoint aus; eine SDK-Installation
neben dem eingefrorenen Upstream-Binary reicht nicht. Google ist der bevorzugte
Kontologin, ohne API-Key-Pflicht; persönliche Anmeldung und Inferenz separat belegen.

CLIScade Canvas 0.7.2: Native Anmeldelinks stehen vollständig in einem Readonly-Feld.
„Link kopieren“ bestätigt erst nach erfolgreichem Clipboard-Schreiben; bei fehlender
Berechtigung das Feld markieren und manuelles Kopieren anbieten. URLs weder loggen
noch dauerhaft im Browser speichern. Reine UI-Updates nur mit Canvas-Neustart deployen,
um laufende CLI-Anmeldungen im Integrationsdienst zu erhalten.

OmniRoute-Deployment 0.8.0: optionaler eigener Compose-Dienst, kein zusätzlicher
Harness im Agent Server. `deploy/OMNIROUTE.md` beschreibt Modellprofil und Aktivierung.
Zugangsdaten nie in Compose/Logs speichern. Bestehende CLI-Konten und ACP-Registry
nicht für den Modellgateway umkonfigurieren. Provider-Migration nur nach Nutzerwahl.

NAS-Konfiguration 0.8.1: OpenHands-Profil `OmniRoute` ist mit `openai/c1` aktiviert.
`c1` ist ein vom Nutzer gewählter Gateway-Combo. Anbieter-Einträge wurden mit
Nutzerfreigabe übernommen; Konten nicht erneut migrieren oder Mac-Client-Keys kopieren.
Andere CLIs werden pro Beads-Aufgabe über `ACP agent` gewählt; `CLI account`
ändert nur die Login-Auswahl. Prüfnachweise und Grenzen: `deploy/OMNIROUTE.md`.

CLIScade 0.9.0: `VITE_CLISCADE_REPOSITORIES=true` aktiviert den servergestützten
GitHub-Workspace-Picker für lokale Code-Chats. `repositories.py` nutzt die native
SDK-Repository-Suche und den SDK-Klonpfad. PAT-Alias nach `github_token` normalisieren,
Token niemals in URLs zurückgeben. Git-Remotes nach dem Klonen bereinigen; der
Credential-Helper löst das Secret nur für github.com zur Laufzeit auf. Fehlgeschlagene
Vorbereitung darf keinen Scratch-Chat starten. Auswahl und MRU liegen im Serverzustand.
OpenHands-Worktrees liegen persistent unter `/workspace/worktrees`.

## Verbindliche CLIScade-Projektgrenzen

Ziel: ein gemeinsamer GitHub-Workspace, ein Repository als stabiles Projekt und
eine kanonische Beads-Aufgabenliste je Projekt. Repository-Auswahl unter New Chat
ist derzeit ein Übergang mit Klon pro Chat, keine fertige Projektverwaltung.
OpenHands/OmniRoute kann über `/tasks` Beads-Attempts ausführen; freie New-Chat-Conversations bleiben getrennt.
Diese Grenzen bei Statusmeldungen und Änderungen ausdrücklich erhalten.

Ausführungsweg (ACP-CLI oder nativer OpenHands-Agent), Modell, Beads-Task,
Conversation, Attempt und Checkpoint bleiben getrennte Begriffe. Langfristig
referenzieren alle Runs dieselbe Projekt-ID und denselben Beads-Bestand;
Worktrees dürfen keine konkurrierenden Task-Datenbanken erzeugen. Installation,
Anmeldung, Discovery und erfolgreicher Anbieter-E2E sind getrennte Nachweise.

Task-Modelle: `openhands` ist der native SDK-Harness mit dem gespeicherten
Profil `OmniRoute`, Standard `openai/c1`; niemals als ACP-Prozess starten.
Explizite Modellwahl über Discovery prüfen, pro Attempt persistieren und bei
Resume aus dem Attempt lesen. Agentenwechsel darf die alte Modellwahl nicht
übernehmen. Keine globalen Profile/Registry-Einstellungen beim Task-Start ändern.
