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
