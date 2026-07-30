#!/usr/bin/env python3
"""
praxis Stop gate.

A Stop hook that exits 2 forces Claude to keep working instead of ending the
turn. praxis uses this for two deterministic jobs so the user never has to run
/goal or drive the loop manually:

  A. TASK COMPLETION LOOP (praxis's built-in /goal replacement).
     While a task recorded via task_state.py is open and in_progress, the gate
     keeps the session working turn after turn until Claude marks it done, or
     marks it waiting_for_user at a genuine decision point (then the gate lets it
     stop to ask). A hard iteration cap prevents runaway; the loop is bound to the
     session that started working it.

  B. PER-CHANGE QUALITY GATE (fallback for ad-hoc edits with no task).
     If there is no open task, the gate refuses to end the turn while the git tree
     has unreviewed changes and no signed green quality report matches the state.
     Refusals escalate, each one names something more concrete than the last
     (the workflow, then the missing evidence, then the consequence), because a
     single generic reminder is trivially acknowledged and stepped past. Any
     unfinished marker or house-style violation in the change's own diff leads the
     message: an unfinished marker is the signature of a deferred, MVP-shaped
     delivery, and a style violation is a rule that prose alone has failed to
     enforce. Two caps (per change state and per session) guarantee the gate can
     never trap a session.

     A change that touches user-facing surface (markup, styles, components,
     `docs/design/`) additionally needs the accessibility and design-consistency
     verdicts in its report. Those two verticals are what separate a designed
     interface from an assembled one, and they were the two most easily skipped
     while the requirement lived only in prose.

Both are deterministic and driven by state files, not by parsing the prompt.

Escapes: `touch .claude/.praxis/skip-gate` (repo) or `PRAXIS_GATE=off` (session).
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

REPORT = "quality_report.json"
NOTIFIED = "gate_notified.json"
TASK = "task.json"
STALE_SECONDS = 12 * 3600

# How many times one change state may be refused before the gate releases it.
# Escalating refusals beat a single reminder, which is trivially stepped past,
# while the cap guarantees the session can always finish.
MAX_NUDGES = 3
# Total refusals allowed per session, so a change set that keeps mutating (and so
# keeps re-keying the per-state counter) can never loop indefinitely.
SESSION_NUDGE_CAP = 12


def gate_disabled(root) -> bool:
    """The one question this hook asks before anything else.

    Resolved through the shared switch ladder rather than re-derived here, so
    what `/praxis:config` reports and what this hook enforces cannot disagree.
    """
    return not common.gate_enabled(root)


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
        common.allow()  # Claude is asking the user something: let it stop

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
            "without being marked done. Handing back to you: review progress, "
            "then run task_state.py resume to continue or done/clear to close.\n"
        )
        # Hand back the *task* loop, not the quality gate: falling through keeps
        # unreviewed code covered, instead of leaving the repo ungated until the
        # task goes stale.
        return False

    task["iterations"] = iters + 1
    common.write_state(root, TASK, task)

    crit = task.get("criteria", [])
    crit_txt = "\n".join(f"  - {c}" for c in crit) if crit else "  (none recorded)"
    common.block(
        f"[praxis] Task '{task.get('title','')}' is not finished "
        f"(turn {iters + 1}/{cap}). Keep working end to end.\n"
        f"Acceptance criteria:\n{crit_txt}\n"
        + _plan_status(task) +
        "Next: either continue the next step; or, if EVERY criterion is met and the "
        "praxis audit is green, run "
        "`python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py\" done`. "
        "If you need a decision from the user, run `task_state.py waiting` first, "
        "then stop and ask."
    )
    return True


def _plan_status(task) -> str:
    """The subtask plan, and the delivery discipline that goes with it.

    Restated on every refusal because this is where it is acted on: the point of
    a plan is that the next step is never in doubt, and the point of one commit
    per subtask is that the pull request ends up reading like the plan.
    """
    subs = task.get("subtasks")
    # Coerced, not trusted. task.json is read straight off disk, and a hand
    # edit, a 3.0 file or a torn write can make `subtasks` a string or a list of
    # strings. `s.get` would then raise inside the argument to `common.block`,
    # the exception would reach main's handler, and that handler calls `allow()`:
    # a malformed plan would release the gate on an open, unfinished task.
    subs = [s for s in subs if isinstance(s, dict)] if isinstance(subs, list) else []
    if not subs:
        return ""
    mark = {"done": "x", "in_progress": ">", "pending": " "}
    lines = [f"Plan ({sum(1 for s in subs if s.get('status') == 'done')}/{len(subs)} "
             "subtasks done):"]
    for i, sub in enumerate(subs, 1):
        commit = f"  [{sub['commit']}]" if sub.get("commit") else ""
        lines.append(f"  [{mark.get(sub.get('status'), ' ')}] {i}. "
                     f"{sub.get('title', '')}{commit}")
    nxt = next((i for i, s in enumerate(subs, 1) if s.get("status") != "done"), None)
    if nxt:
        lines.append(f"Work subtask {nxt} next. Commit it on its own "
                     "(`task_state.py subtask done {n}` records the sha), so the "
                     "task's pull request reads as this plan.")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# B. Per-change quality gate (no open task)
# --------------------------------------------------------------------------- #
def _sessions(root) -> dict:
    state = common.read_state(root, NOTIFIED)
    sessions = state.get("sessions")
    return sessions if isinstance(sessions, dict) else {}


def read_nudges(root, session_id) -> dict:
    """This session's refusal record: {counts: {sig: n}, total: n, disclosed: bool}."""
    entry = _sessions(root).get(session_id)
    if not isinstance(entry, dict):
        return {"counts": {}, "total": 0, "disclosed": False}
    return {
        "counts": entry.get("counts") if isinstance(entry.get("counts"), dict) else {},
        "total": int(entry.get("total", 0)),
        "disclosed": bool(entry.get("disclosed")),
    }


def write_nudges(root, session_id, entry) -> bool:
    """Persist this session's refusal record. False if it could not be written.

    Each session owns its own entry: a single shared record would let two windows
    on the same repo wipe each other's counters on every turn, and the caps that
    guarantee the gate releases would then never be reached.
    """
    state = common.read_state(root, NOTIFIED)
    sessions = _sessions(root)
    entry["ts"] = time.time()
    sessions[session_id] = entry
    # Drop the oldest sessions rather than an arbitrary slice, so the record of
    # the session currently being gated is never the one evicted.
    if len(sessions) > 20:
        ordered = sorted(sessions.items(), key=lambda kv: kv[1].get("ts", 0), reverse=True)
        sessions = dict(ordered[:20])
        sessions[session_id] = entry
    state["sessions"] = sessions
    state.pop("counts", None)      # pre-1.5 shape
    state.pop("session", None)
    try:
        common.write_state_strict(root, NOTIFIED, state)
        return True
    except Exception:
        return False


def missing_ui_verticals(root, rep) -> list:
    """UI verticals a recorded report owes but does not carry."""
    return common.missing_ui_verticals(root, (rep.get("evidence") or {}).get("verticals") or {})


def has_green_report(root, sig) -> bool:
    rep = common.read_state(root, REPORT)
    if not (rep.get("signature") == sig
            and rep.get("status") == "pass"
            and (time.time() - rep.get("ts", 0)) < 24 * 3600):
        return False
    # A change to markup, styles, or components is design work whether or not it
    # was framed as such, so the two UI auditors are part of its evidence.
    if missing_ui_verticals(root, rep):
        return False
    return not report_gaps(root, rep)


def report_gaps(root, rep) -> list:
    """Why this report is not evidence, re-derived here rather than trusted.

    `report.py` computes the same verdict when it writes the file, and this asks
    again from the recorded evidence. Not redundancy: the report is a JSON file in
    a directory anyone can write, and a gate that accepted `"status": "pass"` on
    its own would be a gate whose whole guarantee is one hand-edited line away.
    """
    cfg = common.read_config(root)
    # `or {}` because a hand-written report with a null evidence block would
    # otherwise raise here, and an exception in this hook fails open.
    ev = rep.get("evidence") or {}
    gaps = []

    # Evidence requirement: if the repo has a test command, the report must record
    # a passing run that report.py actually executed, so a "green" report is
    # backed by a real result, not trust. Reports written before evidence was
    # verified (pre-1.5 schema) carry no `test_verified` flag and are rejected
    # rather than grandfathered: an unverifiable claim is not evidence.
    # Teams can relax this with `require_tests = false` in .praxis.toml.
    if cfg.get("gate.require_tests", True) and common.detect_test_command(root):
        if ev.get("test_exit") not in (0,) or not ev.get("test_verified"):
            gaps.append("the tests did not pass, or were never run by report.py")
        # A substituted command (`--tests true`) can exit 0 without running the
        # suite. Overriding is legitimate, so it is surfaced to the model rather
        # than silently accepted, but it does not buy a green gate on its own.
        elif ev.get("test_substituted"):
            gaps.append(f"the report ran `{ev.get('test_command')}` instead of the "
                        f"project's `{ev.get('detected_test_command')}`")

    # The deterministic scanners. Before they were recorded here, a green report
    # was the way *past* them: the gate runs them only when no report exists.
    scans = ev.get("scans")
    if not isinstance(scans, dict) or not ev.get("scans_verified"):
        gaps.append("the deterministic scanners were not run and recorded "
                    "(re-record with report.py, which runs them itself)")
    else:
        for key, label, check in (
                ("placeholders", "unfinished-work marker(s)", "unfinished work"),
                ("style", "house-style violation(s)", "house style"),
                ("knowledge", "living-knowledge gap(s)", "living knowledge")):
            entry = scans.get(key) if isinstance(scans.get(key), dict) else {}
            count = entry.get("count", 0)
            if not entry.get("ran"):
                gaps.append(f"the {check} scan could not run")
            elif count and key == "knowledge":
                if cfg.get("gate.require_knowledge", True) and not ev.get("knowledge_ack"):
                    gaps.append(f"{count} {label}, neither fixed nor acknowledged")
            elif count:
                gaps.append(f"{count} {label} in this change")

    runtime = ev.get("runtime") if isinstance(ev.get("runtime"), dict) else {}
    if runtime.get("required") and runtime.get("exit") not in (0,):
        gaps.append("the project's end-to-end harness did not pass on a change "
                    "to what a user sees")

    # A verdict nobody had to substantiate is a verdict nobody had to reach.
    if cfg.get("gate.require_evidence", True):
        verticals = ev.get("verticals") if isinstance(ev.get("verticals"), dict) else {}
        recorded = (ev.get("vertical_evidence")
                    if isinstance(ev.get("vertical_evidence"), dict) else {})
        unbacked = sorted(k for k in verticals if k not in recorded)
        if unbacked:
            gaps.append("no recorded evidence for: " + ", ".join(unbacked))
    return gaps


def handle_per_change(root, session_id):
    # "Is there anything to review", not "is the tree dirty". Committing work
    # used to end the review: one `git commit` emptied every diff praxis looks
    # at, so the better the delivery discipline, the less the gate saw.
    if not common.review_pending(root):
        common.allow()
    sig = common.change_signature(root)
    if has_green_report(root, sig):
        common.allow()
    if _unchanged_since_session_start(root, sig):
        common.allow()

    nudges = read_nudges(root, session_id)
    nudges["counts"][sig] = nudges["counts"].get(sig, 0) + 1
    nudges["total"] += 1
    per_state, total = nudges["counts"][sig], nudges["total"]

    # If the counter cannot be persisted, the caps below can never be reached,
    # so the gate would block every turn forever. Fail open instead.
    if not write_nudges(root, session_id, nudges):
        common.allow()

    if per_state > MAX_NUDGES or total >= SESSION_NUDGE_CAP:
        # Releasing silently would skip the one message that matters most: the
        # instruction to tell the user the change is going out unaudited. Spend
        # one final turn on it, then release for good.
        if nudges["disclosed"]:
            common.allow()
        nudges["disclosed"] = True
        write_nudges(root, session_id, nudges)
        common.block(_final_disclosure(root, sig))

    # Escalate on the session total, not the per-change count: Claude normally
    # edits between two Stops, which re-keys the signature, so a per-change
    # counter would restart at 1 every turn and the refusal would never sharpen.
    common.block(_escalating_message(
        root, sig, min(total, MAX_NUDGES),
        common.run_scanner("scan_placeholders.py", root, timeout=20),
        common.run_scanner("scan_style.py", root, timeout=20),
        common.run_scanner("knowledge_check.py", root, timeout=20)))


def _unchanged_since_session_start(root, sig) -> bool:
    """True if the tree is byte-for-byte as this session found it.

    A repo can be dirty because of work that predates the session. Gating a turn
    that changed nothing would demand an audit of somebody else's diff, and
    would misattribute their unfinished markers to this change.
    """
    baseline = common.read_state(root, "last_session_audit.json").get("signature")
    return bool(baseline) and baseline == sig


def _cited(findings: list, limit: int = 10) -> list:
    """Findings rendered as `- [marker] file:line  text` lines, capped.

    Reads both scanner shapes: the line scanners report a `marker` and the text
    they matched, the knowledge check reports a `kind` and what is missing.
    """
    lines = []
    for f in findings[:limit]:
        loc = f"{f.get('file','?')}:{f.get('line','?')}"
        label = f.get("marker") or f.get("kind") or "finding"
        body = (f.get("text") or f.get("detail") or "")[:100]
        lines.append(f"  - [{label}] {loc}  {body}")
    if len(findings) > limit:
        lines.append(f"  - ... and {len(findings) - limit} more")
    return lines


def _escalating_message(root, sig, attempt: int, unfinished: list, style: list,
                        knowledge: list) -> str:
    """The block reason, sharpening with each refusal.

    Escalation matters: a single generic reminder is easy to acknowledge and
    step past. Each attempt names something more concrete, first the workflow,
    then the specific evidence that is missing, then the consequence.
    """
    parts = []

    if unfinished:
        # Unfinished work in one's own diff is the clearest possible signal of a
        # deferred, MVP-shaped delivery: it leads the message at every attempt.
        parts.append(
            f"[praxis] BLOCKED: this change leaves {len(unfinished)} unfinished "
            "marker(s) in its own diff. Finish them; do not hand back partial work:"
        )
        parts += _cited(unfinished)
        parts.append(
            "Each one is either (a) in scope: implement it properly now, or (b) out "
            "of scope: remove it from the code and state it under 'Out of scope / "
            "follow-ups' in your report. A marker left in the diff is neither.\n"
            "If a phrase is a legitimate, accepted limitation, annotate that line "
            "with `praxis:ack` so the reason is recorded in the code."
        )

    if style:
        parts.append(
            f"[praxis] BLOCKED: {len(style)} house-style violation(s) in this "
            "change's own diff:"
        )
        parts += _cited(style)
        parts.append(
            "Fix each one in the file, not in your explanation: rewrite an em dash "
            "as a colon, a comma, parentheses, or two sentences, and delete any AI "
            "co-author or generated-by credit outright. `praxis:ack` on the line "
            "exempts a case that is genuinely correct, such as a fixture that must "
            "contain the character."
        )

    if knowledge:
        parts.append(
            f"[praxis] BLOCKED: this change leaves {len(knowledge)} "
            "living-knowledge gap(s). Documentation is part of done, not a "
            "follow-up:"
        )
        parts += _cited(knowledge)
        parts.append(
            "Update the docs this change made untrue, record the "
            "`[Unreleased]` entry (`changelog.py add --type <type> \"...\"`), and "
            "restore anything a document lost. If one of these genuinely does not "
            "apply, record the reason with `report.py record --knowledge-ack "
            "\"<why>\"` so it stays in the report instead of disappearing."
        )

    ui_missing = missing_ui_verticals(root, common.read_state(root, REPORT))
    if ui_missing:
        touched = common.ui_files_in_change(root)
        parts.append(
            f"[praxis] This change touches {len(touched)} user-facing file(s) "
            f"(e.g. {', '.join(touched[:3])}), so it is design work and its report "
            f"is not green without: {', '.join(ui_missing)}.\n"
            "Dispatch `@praxis:accessibility-auditor` and "
            "`@praxis:design-consistency-auditor`, fix what they find, and add "
            "`accessibility=pass,design-consistency=pass` to the --verticals string. "
            "If no design system exists yet, the `frontend-pipeline` skill "
            "establishes one first."
        )

    if attempt == 1:
        parts.append(
            "[praxis] Uncommitted changes have not passed the quality rubric.\n"
            # Say why on the FIRST refusal too: if a report exists but was
            # rejected (stale signature, substituted test command), repeating the
            # generic instruction sends the model round the same loop blind.
            + _report_status(root, sig) +
            "Run it before finishing: the `quality-rubric` skill (or `/praxis:audit`). "
            "It dispatches the read-only vertical auditors: adversarial, regression, "
            "duplication, performance, edge-case, doc-reference, debt, completeness (plus "
            "accessibility and design-consistency if this change touches UI), then a "
            "horizontal pass, and records the green report."
        )
    elif attempt == 2:
        parts.append(
            "[praxis] Still no green report for the current change state "
            f"(attempt {attempt}/{MAX_NUDGES}). Reminding you is not the point: the "
            "auditors have to actually run.\n"
            + _report_status(root, sig) +
            "Do this now, concretely:\n"
            "  1. `git diff` to scope the change and its blast radius.\n"
            "  2. Dispatch each vertical auditor as a subagent on that diff.\n"
            "  3. Fix every FAIL: do not defer, do not narrow the scope silently.\n"
            "  4. Run the project's tests.\n"
            "  5. `python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/report.py\" record "
            "--verticals \"...\"`: it runs the tests itself and records the real "
            "exit code."
        )
    else:
        parts.append(
            f"[praxis] Attempt {attempt}. The audit still has not run.\n"
            + _report_status(root, sig) +
            "Stop restating the plan and execute it: dispatch the auditors, fix what "
            "they find, run the tests, record the report. If a specific thing is "
            "blocking you, say what it is instead of finishing quietly."
        )

    parts.append(
        "Escapes: `.claude/.praxis/skip-gate` (repo) or `PRAXIS_GATE=off` (session)."
    )
    return "\n".join(parts)


def _final_disclosure(root, sig) -> str:
    """The last thing the gate says before it stops blocking this session."""
    return (
        "[praxis] The gate is releasing this change UNAUDITED.\n"
        + _report_status(root, sig) +
        "This is your last turn under the gate, so do one of two things, not "
        "neither:\n"
        "  a) complete the audit now (dispatch the auditors, fix findings, run the "
        "tests, `report.py record`); or\n"
        "  b) tell the user plainly, in your reply, that the change was NOT audited, "
        "which verticals are unverified, why you could not finish, and what they "
        "should check themselves.\n"
        "Do not present unaudited work as finished."
    )


def _report_status(root, sig=None) -> str:
    """One line describing why the existing report (if any) doesn't count."""
    rep = common.read_state(root, REPORT)
    if not rep:
        return "No quality report has been recorded at all.\n"
    if rep.get("signature") != (sig if sig is not None else common.change_signature(root)):
        return ("A report exists but was recorded against a different change state: "
                "the code moved since; it must be re-run.\n")
    ev = rep.get("evidence") or {}
    ui_missing = missing_ui_verticals(root, rep)
    if rep.get("status") != "pass":
        failed = [k for k, v in (ev.get("verticals") or {}).items() if v != "pass"]
        if failed:
            detail = f" Failing vertical(s): {', '.join(failed)}."
        elif ui_missing:
            # Without this branch the message reads "no verdicts were recorded"
            # for a report that recorded seven and is missing only the UI two.
            detail = (f" It carries no verdict for {', '.join(ui_missing)}, which "
                      "this change needs because it touches user-facing surface.")
        else:
            detail = " No vertical verdicts were recorded: the auditors have to run."
        return f"The recorded report status is '{rep.get('status')}'.{detail}\n"
    if ui_missing:
        return (f"The report is otherwise green but this change touches user-facing "
                f"surface and carries no verdict for: {', '.join(ui_missing)}.\n")
    gaps = report_gaps(root, rep)
    if gaps:
        return ("The report is marked pass, but its own evidence says otherwise: "
                + "; ".join(gaps) + ". Re-record it with `report.py record`, which "
                "runs the tests and the scanners itself.\n")
    return "The recorded report is stale (older than 24h).\n"


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
