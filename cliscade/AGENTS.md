# CLIScade Next integration

This package owns Beads project integration and orchestration policy. Agent
execution, ACP transport, conversation persistence and cancellation belong to
the existing OpenHands SDK/Agent Server and must be reused through its SDK.
Beads is the only task store. The local SQLite ledger stores attempts and
checkpoints, never a second editable copy of tasks or conversations.

Use feature branches and German documentation and commit messages. Run
`uv sync --frozen`, `uv run pytest`, and `uv run ruff check .` in this directory.
Provider statements are unverified. Checks require a paired tool result and
exit status; never promote an agent's prose to evidence. A submitted prompt is
an execution boundary: automatic fallback after that boundary is forbidden.

Parent OpenHands guidance applies to upstream Canvas code. CLIScade-specific
backend integrations live here as a separate installable service, not in Canvas
API adapters or a replacement Agent Server. No headless or PTY runner.

Konsensreservierungen und Dispatch müssen denselben dateibasierten Dispatch-Lock
beachten. Jeder Konsensversuch beginnt bei derselben Revision und eingefrorenen
Aufgabe/Projektwissen; Provider-Historien bleiben getrennt. Eine Patch-Gleichheit
ist kein Korrektheitsnachweis. Native Automationen verwenden ihre Run-ID als
Idempotenzschlüssel. Der Dispatch-Bundle enthält keine Zugangsdaten.

Beads-Backups werden erst nach nativer Wiederherstellung und vollständigem
Vergleich von Aufgaben und Memories als verifiziert bezeichnet. Das ist keine
vollständige Sicherung der OpenHands-Sessions. Deployment-Tests stehen in
`tests/test_deployment.py`; Docker-Builds laufen ausschließlich auf ZimaOS.
