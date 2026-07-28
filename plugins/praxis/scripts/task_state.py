#!/usr/bin/env python3
"""
praxis task-state helper.

Gives Claude a clean, deterministic way to record where a task is, which the
Stop-gate reads to drive the completion loop (praxis's built-in replacement for
manually running /goal). No prompt keyword matching is involved: the model
records state explicitly, the hook enforces it mechanically.

A task also carries the two things that make a large request traceable:

  * **subtasks**, so a big prompt becomes an ordered plan instead of one opaque
    unit of work whose progress nobody can see. The gate reports which one is in
    flight, and a task cannot close while any of them is unfinished.
  * **a delivery binding**, so one task maps to one branch and one pull request,
    and each subtask lands as its own commit inside it. Versioning then follows
    the work rather than being reconstructed afterwards from a pile of edits.

Usage:
    task_state.py open "<title>" --criteria "c1" "c2" \
        [--subtasks "s1" "s2" ...] [--max N] [--branch <name>]
    task_state.py plan "s1" "s2" ...   # (re)declare the subtasks of an open task
    task_state.py subtask start <n>
    task_state.py subtask done  <n> [--commit <sha>]
    task_state.py delivery [--branch <name>] [--pr <url>]
    task_state.py resume          # back to in_progress after a user answer
    task_state.py waiting         # a genuine decision point: allow stopping to ask
    task_state.py done            # all criteria met + audit green: close the loop
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

PENDING, IN_PROGRESS, DONE = "pending", "in_progress", "done"

#: Ceiling for --max. The task loop has no session-level release, so an
#: unbounded cap is a gate that never lets go.
MAX_ITERATIONS = 200


def load(root):
    return common.read_state(root, NAME)


def save(root, data):
    data["updated"] = time.time()
    common.write_state(root, NAME, data)


def collect(args, flag):
    """Values following `flag` up to the next `--option`."""
    out = []
    if flag in args:
        i = args.index(flag) + 1
        while i < len(args) and not args[i].startswith("--"):
            out.append(args[i])
            i += 1
    return out


def subtasks_of(data):
    subs = data.get("subtasks")
    return subs if isinstance(subs, list) else []


def unfinished(data):
    return [s for s in subtasks_of(data) if s.get("status") != DONE]


def render_plan(data) -> str:
    """The subtask list as the gate and `status` show it."""
    subs = subtasks_of(data)
    if not subs:
        return "  (no subtasks declared)"
    mark = {DONE: "x", IN_PROGRESS: ">", PENDING: " "}
    lines = []
    for i, s in enumerate(subs, 1):
        commit = f"  [{s['commit']}]" if s.get("commit") else ""
        lines.append(f"  [{mark.get(s.get('status'), ' ')}] {i}. {s.get('title','')}{commit}")
    return "\n".join(lines)


def _index(args, data):
    """The 1-based subtask number in `args`, validated against the plan.

    Positional only. Scanning argv for the first digit made `subtask done
    --commit 3` mark subtask 3, because a flag's value is a digit too.
    """
    nums = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg.startswith("--"):
            skip = "=" not in arg
            continue
        nums.append(arg)
        break
    nums = [a for a in nums if a.isdigit()]
    if not nums:
        raise SystemExit("praxis: which subtask? usage: task_state.py subtask "
                         "start|done <n>")
    n = int(nums[0])
    subs = subtasks_of(data)
    if not 1 <= n <= len(subs):
        raise SystemExit(f"praxis: subtask {n} does not exist "
                         f"(the plan has {len(subs)}).")
    return n - 1


def cmd_open(root, args) -> int:
    title = args[1]
    criteria = collect(args, "--criteria")
    subs = collect(args, "--subtasks")
    max_iter = 25
    if "--max" in args:
        try:
            # Bounded at both ends. A cap of 0 is reached before any work
            # happens, which silently disables the loop it configures; an
            # unbounded one produces a gate that holds a session essentially
            # forever, and the task loop has no session-level release.
            max_iter = min(MAX_ITERATIONS, max(1, int(args[args.index("--max") + 1])))
        except Exception:
            pass
    branch = (common.cli_opt(args, "--branch", "") or "").strip()

    save(root, {
        "open": True,
        "title": title,
        "criteria": criteria,
        "status": IN_PROGRESS,
        "iterations": 0,
        "max_iterations": max_iter,
        "session": "",
        "subtasks": [{"title": s, "status": PENDING, "commit": ""} for s in subs],
        "delivery": {
            "branch": branch or common.current_branch(root),
            "base": common.git_default_branch(root) if common.is_git_repo(root) else "",
            # The sha the task started from, so the first subtask can be checked
            # for a commit of its own like every other one.
            "opened_at": (common._run(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=root).strip()
                          if common.is_git_repo(root) else ""),
            "pr": "",
        },
    })
    print(f"praxis: task opened, '{title}' (cap {max_iter} turns).")
    if subs:
        print(f"praxis: {len(subs)} subtask(s) planned. One commit each, one pull "
              "request for the task.")
        print(render_plan(load(root)))
    return 0


def cmd_plan(root, data, args) -> int:
    # `collect`-style: stop at the first option, so `plan "s1" --branch x`
    # does not turn "x" into a phantom subtask that can never be finished.
    titles = []
    for arg in args[1:]:
        if arg.startswith("--"):
            break
        titles.append(arg)
    if not titles:
        print("usage: task_state.py plan \"subtask 1\" \"subtask 2\" ...")
        return 1
    existing = {s.get("title"): s for s in subtasks_of(data)}
    # Re-planning keeps the state of any subtask that survives the rewrite, so
    # adding a step to a plan does not silently reopen the finished ones.
    data["subtasks"] = [existing.get(t, {"title": t, "status": PENDING, "commit": ""})
                        for t in titles]
    save(root, data)
    print(f"praxis: plan recorded, {len(titles)} subtask(s).")
    print(render_plan(data))
    return 0


def cmd_subtask(root, data, args) -> int:
    if len(args) < 2 or args[1] not in ("start", "done"):
        print("usage: task_state.py subtask start|done <n> [--commit <sha>]")
        return 1
    action = args[1]
    i = _index(args[2:], data)
    sub = data["subtasks"][i]

    if action == "start":
        sub["status"] = IN_PROGRESS
        save(root, data)
        print(f"praxis: subtask {i + 1} in progress, '{sub['title']}'.")
        return 0

    sub["status"] = DONE
    commit = common.cli_opt(args, "--commit", "")
    if not commit and common.is_git_repo(root):
        commit = common._run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=root).strip()
    # A subtask that ends on a commit some other subtask already claimed, or on
    # the commit the task opened at, produced no commit of its own: the tracking
    # this whole mechanism exists for is gone. Checked against every recorded
    # commit, not just the previous one, so finishing subtasks out of order does
    # not slip past it.
    claimed = {s.get("commit") for j, s in enumerate(data["subtasks"])
               if j != i and s.get("commit")}
    opened_at = (data.get("delivery") or {}).get("opened_at", "")
    uncommitted = bool(commit and (commit in claimed or commit == opened_at))
    sub["commit"] = "" if uncommitted else commit
    save(root, data)

    print(f"praxis: subtask {i + 1} done, '{sub['title']}'"
          + (f" ({commit})." if sub["commit"] else "."))
    if uncommitted:
        print("praxis: WARNING, this subtask shares a commit with the previous "
              "one. Commit each subtask separately so the history shows what was "
              "done and why; a task's pull request should read as its plan.")
    remaining = unfinished(data)
    if remaining:
        print(f"praxis: {len(remaining)} subtask(s) left.")
        print(render_plan(data))
    return 0


def cmd_delivery(root, data, args) -> int:
    delivery = data.get("delivery") or {}
    for flag, key in (("--branch", "branch"), ("--pr", "pr")):
        value = common.cli_opt(args, flag, None)
        if value is not None:
            delivery[key] = value
    data["delivery"] = delivery
    save(root, data)
    print(f"praxis: delivery, branch={delivery.get('branch') or '?'} "
          f"base={delivery.get('base') or '?'} pr={delivery.get('pr') or 'not opened'}")
    return 0


def cmd_done(root, data, args) -> int:
    remaining = unfinished(data)
    if remaining and "--force" not in args:
        print(f"praxis: {len(remaining)} subtask(s) are not finished, so this task "
              "is not done:")
        print(render_plan(data))
        print("praxis: finish them, or re-plan with `task_state.py plan ...` if the "
              "work genuinely changed shape. `--force` closes anyway and should be "
              "explained to the user.")
        return 1

    data["open"] = False
    data["status"] = DONE
    save(root, data)
    print("praxis: task closed, done.")
    missing = [s["title"] for s in subtasks_of(data) if not s.get("commit")]
    if missing:
        print("praxis: note, these subtasks recorded no commit of their own: "
              + "; ".join(missing))
    delivery = data.get("delivery") or {}
    if not delivery.get("pr"):
        print("praxis: no pull request recorded for this task. Deliver it "
              "(`/praxis:ship`) so the work is versioned, then "
              "`task_state.py delivery --pr <url>`.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: task_state.py open|plan|subtask|delivery|resume|waiting|"
              "done|clear|status ...")
        return 1
    root = common.project_dir({})
    cmd = args[0]

    if cmd == "open":
        if len(args) < 2:
            print("usage: task_state.py open \"<title>\" [--criteria c1 c2] "
                  "[--subtasks s1 s2] [--max N] [--branch <name>]")
            return 1
        return cmd_open(root, args)

    data = load(root)
    if not data:
        print("praxis: no task state.")
        return 0

    if cmd == "plan":
        return cmd_plan(root, data, args)
    if cmd == "subtask":
        return cmd_subtask(root, data, args)
    if cmd == "delivery":
        return cmd_delivery(root, data, args)
    if cmd == "done":
        return cmd_done(root, data, args)
    if cmd == "resume":
        data["status"] = IN_PROGRESS
        save(root, data)
        print("praxis: task resumed.")
    elif cmd == "waiting":
        data["status"] = "waiting_for_user"
        save(root, data)
        print("praxis: task set to waiting_for_user (you may stop to ask).")
    elif cmd == "clear":
        data["open"] = False
        data["status"] = "cleared"
        save(root, data)
        print("praxis: task cleared.")
    elif cmd == "status":
        print(json.dumps(data, indent=2))
    else:
        print(f"praxis: unknown command '{cmd}'.")
        return 1
    return 0


if __name__ == "__main__":
    # A CLI whose exit code decides whether a task closes. Failing open here
    # would report a finished task that the state file never recorded.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"praxis: task state command failed: {exc}")
        sys.exit(1)
