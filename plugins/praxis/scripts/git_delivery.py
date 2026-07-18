#!/usr/bin/env python3
"""
praxis auto-merge toggle.

Controls whether praxis merges its own pull requests. With auto-merge on, the
`git-delivery` skill reviews and merges a PR once the audit is green. With it off
(the default), praxis opens the PR and hands it to a human to review and merge —
it never merges to the integration branch on its own.

Usage:
    git_delivery.py on        # enable auto-review-and-merge for this repo
    git_delivery.py off       # disable (PR only; human merges)
    git_delivery.py status

You can also enable it globally by exporting PRAXIS_AUTO_MERGE=on in your shell.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


def main() -> int:
    root = common.project_dir({})
    flag = common.state_dir(root) / "auto-merge"
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "on":
        flag.write_text("on\n", encoding="utf-8")
        print("praxis: auto-merge ON — I will review and merge my PRs once the "
              "audit is green.")
    elif cmd == "off":
        try:
            flag.unlink()
        except FileNotFoundError:
            pass
        if common.auto_merge_on(root):
            env = os.environ.get("PRAXIS_AUTO_MERGE", "")
            source = f"env PRAXIS_AUTO_MERGE={env}" if env else ".praxis.toml [git] auto_merge = true"
            print(f"praxis: cleared the auto-merge toggle, but it is still ON via {source}. "
                  "Change that source to disable it.")
        else:
            print("praxis: auto-merge OFF — I will open the PR and leave the merge to you.")
    else:
        on = common.auto_merge_on(root)
        env = os.environ.get("PRAXIS_AUTO_MERGE", "")
        print(f"praxis auto-merge: {'ON' if on else 'OFF'} "
              f"(base branch: {common.git_default_branch(root)})"
              + (f" (via env PRAXIS_AUTO_MERGE={env})" if env else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
