#!/usr/bin/env python3
"""
praxis Stop gate.

A Stop hook that exits 2 forces Claude to keep working instead of ending the
turn. praxis uses this for two deterministic jobs so the user never has to run
/goal or drive the loop manually:

  A. TASK COMPLETION LOOP (praxis's built-in /goal replacement).
     While a task recorded via task_state.py is open and in_progress, the gate
     keeps the session working turn after turn until Claude marks it done — or
     marks it waiting_for_user at a genuine decision point (then the gate lets it
     stop to ask). A hard iteration cap prevents runaway; the loop is bound to the
     session that started working it.

  B. PER-CHANGE QUALITY GATE (fallback for ad-hoc edits with no task).
     If there is no open task, the gate refuses to end the turn while the git tree
     has unreviewed changes and no signed green quality report matches the state.

Both are deterministic and driven by state files, not by parsing the prompt.

Escapes: `touch .claude/.praxis/skip-gate` (repo) or `PRAXIS_GATE=off` (session).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

REPORT = "quality_report.json"
NOTIFIED = "gate_notified.json"
TASK = "task.json"
STALE_SECONDS = 12 * 3600


def gate_disabled(root) -> bool:
    if os.environ.get("PRAXIS_GATE", "").lower() in ("off", "0", "false"):
        return True
    if (common.state_dir(root) / "skip-gate").exists():
        return True
    if common.read_config(root).get("gate.enabled", True) is False:
        return True
    return False


# --------------------------------------------------------------------------- #
# A. Task completion loop
# --------------------------------------------------------------------------- #
def handle_task(root, session_id):
    """Return True if this hook has decided the outcome (task loop active)."""
    task = common.read_state(root, TASK)
    if not task or not task.get("open"):
        return False

    status = task.get("status", "in_progress")
    if status in ("done", "cleared"):
        return False  # fall through to per-change gate
    if status == "waiting_for_user":
        common.allow()  # Claude is asking the user something — let it stop

    # Stale task from an abandoned session: don't hijack an unrelated session.
    if (time.time() - task.get("updated", 0)) > STALE_SECONDS:
        return False

    # Bind the task to the first session that actively works it.
    bound = task.get("session", "")
    if not bound:
        task["session"] = session_id
        bound = session_id
    elif bound != session_id:
        return False  # another session owns this task; surfaced at SessionStart

    iters = task.get("iterations", 0)
    cap = task.get("max_iterations", 25)
    if iters >= cap:
        # Safety valve: hand control back rather than loop forever.
        task["status"] = "cap_reached"
        common.write_state(root, TASK, task)
        sys.stderr.write(
            f"[praxis] Task '{task.get('title','')}' hit its {cap}-turn cap "
            "without being marked done. Handing back to you — review progress, "
            "then run task_state.py resume to continue or done/clear to close.\n"
        )
        common.allow()

    task["iterations"] = iters + 1
    common.write_state(root, TASK, task)

    crit = task.get("criteria", [])
    crit_txt = "\n".join(f"  - {c}" for c in crit) if crit else "  (none recorded)"
    common.block(
        f"[praxis] Task '{task.get('title','')}' is not finished "
        f"(turn {iters + 1}/{cap}). Keep working end to end.\n"
        f"Acceptance criteria:\n{crit_txt}\n"
        "Next: either continue the next step; or, if EVERY criterion is met and the "
        "praxis audit is green, run "
        "`python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py\" done`. "
        "If you need a decision from the user, run `task_state.py waiting` first, "
        "then stop and ask."
    )
    return True


# --------------------------------------------------------------------------- #
# B. Per-change quality gate (no open task)
# --------------------------------------------------------------------------- #
def already_notified(root, sig, session_id) -> bool:
    state = common.read_state(root, NOTIFIED)
    return state.get("session") == session_id and sig in state.get("signatures", [])


def mark_notified(root, sig, session_id) -> None:
    state = common.read_state(root, NOTIFIED)
    if state.get("session") != session_id:
        state = {"session": session_id, "signatures": []}
    sigs = state.get("signatures", [])
    if sig not in sigs:
        sigs.append(sig)
    state["signatures"] = sigs[-50:]
    common.write_state(root, NOTIFIED, state)


def has_green_report(root, sig) -> bool:
    rep = common.read_state(root, REPORT)
    if not (rep.get("signature") == sig
            and rep.get("status") == "pass"
            and (time.time() - rep.get("ts", 0)) < 24 * 3600):
        return False
    # Evidence requirement: if the repo has a test command, the report must record
    # a passing run — so a "green" report is backed by a real result, not trust.
    # Teams can relax this with `require_tests = false` in .praxis.toml.
    if common.read_config(root).get("gate.require_tests", True) and common.detect_test_command(root):
        ev = rep.get("evidence", {})
        if ev.get("test_exit") not in (0,):
            return False
    return True


def handle_per_change(root, session_id):
    if not common.working_tree_dirty(root):
        common.allow()
    sig = common.change_signature(root)
    if has_green_report(root, sig):
        common.allow()
    if already_notified(root, sig, session_id):
        common.allow()
    mark_notified(root, sig, session_id)
    common.block(
        "[praxis] Uncommitted code changes have not passed the quality rubric.\n"
        "Run the review before finishing: use the `quality-rubric` skill "
        "(or `/praxis:audit`). It dispatches the read-only vertical auditors — "
        "adversarial, regression, duplication, performance, edge-case, "
        "doc-reference, and completeness — then a horizontal consistency pass, and "
        "records a green report when everything holds.\n"
        + _placeholder_summary(root) +
        "If you deliberately want to stop without a full audit, tell the user why, "
        "or create .claude/.praxis/skip-gate to opt this repo out."
    )


def _placeholder_summary(root) -> str:
    try:
        here = os.path.dirname(__file__)
        out = subprocess.run(
            [sys.executable, os.path.join(here, "scan_placeholders.py"), "--json"],
            capture_output=True, text=True, timeout=20,
        )
        data = json.loads(out.stdout or "{}")
        findings = data.get("findings", [])[:8]
        if not findings:
            return ""
        lines = ["\nUnfinished markers detected in the current diff "
                 "(resolve or explicitly report as out-of-scope):"]
        for f in findings:
            loc = f"{f.get('file','?')}:{f.get('line','?')}"
            lines.append(f"  - [{f.get('marker')}] {loc}")
        return "\n".join(lines) + "\n"
    except Exception:
        return ""


def main() -> None:
    data = common.read_hook_input()
    root = common.project_dir(data)
    session_id = data.get("session_id", "")

    if not common.is_git_repo(root):
        common.allow()
    if gate_disabled(root):
        common.allow()

    # A) task loop takes precedence when a task is actively open.
    if handle_task(root, session_id):
        return
    # B) otherwise, the per-change quality gate.
    handle_per_change(root, session_id)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        common.allow()
