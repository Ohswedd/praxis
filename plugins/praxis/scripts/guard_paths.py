#!/usr/bin/env python3
"""
praxis PreToolUse guard.

Blocks two categories of action deterministically, and — crucially — keeps
working even under `--dangerously-skip-permissions`, because PreToolUse hooks
run before the permission-mode check:

  1. Access to sensitive files (.env, private keys, credentials, .ssh/ ...).
     Note: a Read deny only blocks the Read tool; `cat .env` in Bash is caught
     by the Bash branch below.
  2. Catastrophic / irreversible shell commands (rm -rf on broad paths,
     disk wipes, forced pushes to protected branches, `curl | sh`, fork bombs,
     destructive SQL).

Exit 2 blocks the tool and feeds the reason back to Claude.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


# Commands that are effectively irreversible and should never run unattended.
DANGEROUS_COMMAND_PATTERNS = [
    (r"\brm\s+(-[a-zA-Z]*\s+)*-?[a-zA-Z]*[rf][a-zA-Z]*\b.*\s(/|~|\$HOME|\.\s*$|\*)",
     "Recursive/forced delete on a broad or root path"),
    (r"\brm\s+-rf?\s+/\b", "rm -rf on filesystem root"),
    (r"\brm\b.*(--recursive|--force).*\s(/|~|\$HOME)(\s|$)",
     "Recursive/forced delete on root or home (long-form flags)"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Fork bomb"),
    (r"\bmkfs\.", "Filesystem format"),
    (r"\bdd\b.*\bof=/dev/(sd|nvme|disk)", "Raw disk overwrite"),
    (r">\s*/dev/(sd|nvme|disk)", "Redirect over a raw disk device"),
    (r"\bgit\s+push\b.*\s(--force|-f)\b.*\b(main|master|release|prod\w*)\b",
     "Force-push to a protected branch"),
    (r"\bgit\s+push\b.*\s(--force|-f)\b(?!.*--force-with-lease)",
     "Force-push without --force-with-lease"),
    (r"\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f)", "Destructive git state reset"),
    (r"(curl|wget)\s+[^|]*\|\s*(sudo\s+)?(sh|bash|zsh)\b",
     "Piping a remote script straight into a shell"),
    (r"(?i)\bdrop\s+(table|database|schema)\b", "Destructive SQL (DROP)"),
    (r"(?i)\btruncate\s+table\b", "Destructive SQL (TRUNCATE)"),
    (r"\bchmod\s+-R\s+0?777\s+/", "World-writable recursive chmod on root path"),
    (r"(env|printenv|cat\s+[^|]*\.env[^|]*)\s*\|\s*(curl|wget|nc|ncat|telnet)\b",
     "Piping environment/secrets to the network (exfiltration)"),
    (r">>?\s*\S*\.ssh/authorized_keys", "Writing to an SSH authorized_keys file"),
    (r">\s*/etc/\S+", "Writing into /etc (system configuration)"),
    (r"\bgit\s+config\b.*credential\.helper\s+store", "Persisting credentials in plaintext"),
]

_DANGEROUS = [(re.compile(p), why) for p, why in DANGEROUS_COMMAND_PATTERNS]


def check_bash(command: str) -> None:
    if not command:
        common.allow()
    for rx, why in _DANGEROUS:
        if rx.search(command):
            common.block(
                f"[praxis] Blocked a high-risk command: {why}.\n"
                f"Command: {command.strip()[:400]}\n"
                "If this is genuinely intended, run it yourself in a terminal, "
                "or narrow the command. praxis will not run irreversible "
                "operations unattended."
            )
    # Catch reads of sensitive files via shell readers. The sensitive path may be
    # any argument (e.g. `grep SECRET .env` has it last), so scan all tokens of
    # each command segment whose first word is a known reader.
    readers = {"cat", "less", "more", "head", "tail", "xxd", "strings", "nl", "od",
               "grep", "egrep", "fgrep", "rg", "ag", "awk", "sed", "dotenv",
               "source", "."}
    for segment in re.split(r"[;|&]+|&&|\|\|", command):
        toks = segment.strip().split()
        if not toks:
            continue
        if toks[0] in readers:
            for t in toks[1:]:
                if common.is_sensitive_path(t):
                    common.block(
                        f"[praxis] Blocked shell access to a sensitive file: {t}.\n"
                        "Secrets should not enter the model context / shell environment. "
                        "Use a placeholder or a *.env.example instead."
                    )
    common.allow()


def check_file_tool(tool_input: dict) -> None:
    path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("notebook_path")
        or ""
    )
    if common.is_sensitive_path(path):
        common.block(
            f"[praxis] Blocked access to a sensitive file: {path}.\n"
            "Reading or editing secrets risks leaking them into context or git. "
            "Work against a redacted template (e.g. .env.example) instead."
        )
    common.allow()


def main() -> None:
    data = common.read_hook_input()
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool == "Bash":
        check_bash(tool_input.get("command", ""))
    elif tool in ("Read", "Edit", "Write", "MultiEdit"):
        check_file_tool(tool_input)
    common.allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Never break a session because the guard itself errored.
        common.allow()
