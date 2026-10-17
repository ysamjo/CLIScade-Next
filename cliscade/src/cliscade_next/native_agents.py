"""Native ACP-Kommandos ohne Import der OpenHands-Ausführungsumgebung."""

import sys

ACP_ACCOUNT_COMMANDS = {
    "antigravity": ("agy_acp_server.par",)
    + (("--uid=",) if sys.platform == "linux" else ()),
    "codebuddy": ("codebuddy", "--acp"),
}
