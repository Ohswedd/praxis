#!/usr/bin/env python3
"""
praxis task-state helper.

Gives Claude a clean, deterministic way to record where a task is, which the
Stop-gate reads to drive the completion loop (praxis's built-in replacement for
manually running /goal). No prompt keyword matching is involved: the model
records state explicitly, the hook enforces it mechanically.

Usage:
    task_state.py open "<title>" --criteria "c1" "c2" ... [--max N]
    task_state.py resume          # back to in_progress after a user answer
    task_state.py waiting         # a genuine decision point — allow stopping to ask
    task_state.py done            # all criteria met + audit green — close the loop
    task_state.py clear           # abandon the task
    task_state.py status          # print current state (JSON)

State lives at .claude/.praxis/task.json.
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

NAME = "task.json"


def load(root):
    return common.read_state(root, NAME)


def save(root, data):
    data["updated"] = time.time()
    common.write_state(root, NAME, data)


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: task_state.py open|resume|waiting|done|clear|status ...")
        return 1
    root = common.project_dir({})
    cmd = args[0]

    if cmd == "open":
        if len(args) < 2:
            print("usage: task_state.py open \"<title>\" [--criteria c1 c2] [--max N]")
            return 1
        title = args[1]
        criteria, max_iter = [], 25
        if "--criteria" in args:
            i = args.index("--criteria") + 1
            while i < len(args) and not args[i].startswith("--"):
                criteria.append(args[i]); i += 1
        if "--max" in args:
            try:
                # At least one turn: a cap of 0 is reached before any work
                # happens, which would silently disable the loop it configures.
                max_iter = max(1, int(args[args.index("--max") + 1]))
            except Exception:
                pass
        save(root, {
            "open": True,
            "title": title,
            "criteria": criteria,
            "status": "in_progress",
            "iterations": 0,
            "max_iterations": max_iter,
            "session": "",
        })
        print(f"praxis: task opened — '{title}' (cap {max_iter} turns).")
        return 0

    data = load(root)
    if not data:
        print("praxis: no task state.")
        return 0

    if cmd == "resume":
        data["status"] = "in_progress"; save(root, data); print("praxis: task resumed.")
    elif cmd == "waiting":
        data["status"] = "waiting_for_user"; save(root, data)
        print("praxis: task set to waiting_for_user (you may stop to ask).")
    elif cmd == "done":
        data["open"] = False; data["status"] = "done"; save(root, data)
        print("praxis: task closed — done.")
    elif cmd == "clear":
        data["open"] = False; data["status"] = "cleared"; save(root, data)
        print("praxis: task cleared.")
    elif cmd == "status":
        print(json.dumps(data, indent=2))
    else:
        print(f"praxis: unknown command '{cmd}'.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
