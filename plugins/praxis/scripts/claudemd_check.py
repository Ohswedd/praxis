#!/usr/bin/env python3
"""
praxis CLAUDE.md structural verifier (utility, not a hook).

Usage:
    python3 claudemd_check.py <old.md> <new.md>

Emits JSON describing potential *regressions* introduced by the proposed
rewrite so the claudemd-verifier subagent (which supplies the semantic
judgement) can decide whether the change is safe:

  * dropped headings          (a whole section disappeared)
  * removed fenced commands    (a build/test/run command vanished)
  * large net deletions        (proposed file is much shorter)

This is deliberately conservative structural signal only. The subagent layers
meaning on top (e.g. "the command was removed because the script was renamed").
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def headings(text: str):
    return [h.strip() for h in re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.MULTILINE)]


def fenced_commands(text: str):
    cmds = set()
    for block in re.findall(r"```[a-zA-Z0-9]*\n(.*?)```", text, flags=re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                cmds.add(line)
    # also inline `code` that looks like a command
    for inline in re.findall(r"`([^`]+)`", text):
        s = inline.strip()
        if re.match(r"^(npm|pnpm|yarn|make|go|cargo|pytest|python|pip|docker|"
                    r"mvn|gradle|bundle|rake|mix|dotnet|composer)\b", s):
            cmds.add(s)
    return cmds


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: claudemd_check.py <old.md> <new.md>"}))
        return 1
    old_p, new_p = Path(sys.argv[1]), Path(sys.argv[2])
    old = old_p.read_text(encoding="utf-8", errors="ignore") if old_p.exists() else ""
    new = new_p.read_text(encoding="utf-8", errors="ignore") if new_p.exists() else ""

    old_h, new_h = set(headings(old)), set(headings(new))
    old_c, new_c = fenced_commands(old), fenced_commands(new)

    dropped_headings = sorted(old_h - new_h)
    removed_commands = sorted(old_c - new_c)

    old_len, new_len = len(old.splitlines()), len(new.splitlines())
    shrink_ratio = (1 - new_len / old_len) if old_len else 0.0

    regressions = []
    if dropped_headings:
        regressions.append(f"{len(dropped_headings)} heading(s) removed")
    if removed_commands:
        regressions.append(f"{len(removed_commands)} command(s) removed")
    if shrink_ratio > 0.30 and old_len > 20:
        regressions.append(f"file shrank {shrink_ratio:.0%}")

    result = {
        "has_potential_regression": bool(regressions),
        "summary": regressions,
        "dropped_headings": dropped_headings,
        "removed_commands": removed_commands,
        "old_lines": old_len,
        "new_lines": new_len,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
