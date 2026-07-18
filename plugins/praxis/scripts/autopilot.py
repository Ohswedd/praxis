#!/usr/bin/env python3
"""
praxis auto-pilot toggle.

Auto-pilot = zero questions to the user. praxis does its own QA and resolves
every design/approach decision by choosing the best-practice that fits, recording
each decision in the report's "Decisions taken autonomously" section. Safety is
unchanged: destructive/secret guards still block, the quality/task gate still runs.

Usage:
    autopilot.py on       # enable for this repo
    autopilot.py off      # disable for this repo
    autopilot.py status

You can also enable it globally by exporting PRAXIS_AUTOPILOT=on in your shell.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


def main() -> int:
    root = common.project_dir({})
    flag = common.state_dir(root) / "autopilot"
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "on":
        flag.write_text("on\n", encoding="utf-8")
        print("praxis: auto-pilot ON — I will not ask; I decide by best-practice "
              "and log every decision in the report.")
    elif cmd == "off":
        try:
            flag.unlink()
        except FileNotFoundError:
            pass
        print("praxis: auto-pilot OFF — I will stop to ask at genuine decision points.")
    else:
        on = common.autopilot_on(root)
        env = os.environ.get("PRAXIS_AUTOPILOT", "")
        print(f"praxis auto-pilot: {'ON' if on else 'OFF'}"
              + (f" (via env PRAXIS_AUTOPILOT={env})" if env else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
