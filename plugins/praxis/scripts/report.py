#!/usr/bin/env python3
"""
Praxis quality-report writer (evidence-backed).

Records the green quality report the Stop gate reads, but with *evidence*
rather than a bare pass flag. Nothing here is taken on trust from the caller,
because everything here is exactly what a caller under pressure to finish would
be tempted to assert:

  * **the tests** are run by this script, and the real exit code is recorded. A
    caller-supplied "--tests-exit 0" is a claim, not a result.
  * **the deterministic scanners** (unfinished work, house style, living
    knowledge) are run by this script too. They used to run only in the Stop
    gate, and the gate skips them the moment a green report exists, so recording
    a report was itself the way past them: a placeholder, an em dash or a
    dropped document could ship inside a change that reported itself clean.
  * **the runtime check**, when the project has an end-to-end harness and the
    change touches what a user sees. A unit suite proves a function; it does not
    prove the page renders or the flow completes.
  * **each vertical verdict** must have been recorded, one at a time, with a
    summary and at least one citation that resolves against the repository. A
    fabricated `file:line` is refused at the moment it is written, which is the
    only moment anyone can still check it cheaply.

Usage:
    report.py vertical <name> --verdict pass|notes|fail \
        --summary "what was examined and concluded" \
        --evidence "src/a.py:120,src/b.py"
    report.py record \
        [--tests "pytest"] [--timeout 900] \
        [--runtime "npm run e2e"] [--runtime-timeout 900] \
        [--knowledge-ack "why a living-knowledge finding does not apply"] \
        --verticals "doc-reference=pass,duplication=pass,regression=pass,\
adversarial=pass,edge-case=pass,performance=pass,debt=pass,completeness=pass"
    report.py show

--tests defaults to the repo's detected test command. Overriding it is recorded
as a substitution, because running *a* command proves nothing while running the
project's suite proves something: the gate does not accept a substituted run on
its own (a legitimate override, one package of a monorepo, should be stated to
the user). If the repo has no detectable test command and none is given, the
report is recorded without a test requirement, and the missing coverage should be
reported. A report with no vertical verdicts attests to nothing and is 'fail'.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

NAME = "quality_report.json"

#: The per-vertical evidence store. Separate from the report because it is
#: written across a whole audit, one auditor at a time, while the report is one
#: atomic statement about the finished state.
LEDGER = "audit_ledger.json"

# Generous enough for a real suite, bounded so a hung test run can't wedge the
# session. Override per-invocation with --timeout.
TEST_TIMEOUT = 900

#: Deterministic scanners this script runs itself, and what a finding from each
#: one means. All three gate the report; only `knowledge` can be acknowledged,
#: because "this change genuinely needed no doc" is a real answer while "this
#: placeholder is fine" is not.
SCANNERS = (
    ("placeholders", "scan_placeholders.py", "unfinished work"),
    ("style", "scan_style.py", "house-style violations"),
    ("knowledge", "knowledge_check.py", "living-knowledge gaps"),
)

SCAN_TIMEOUT = 90

#: Findings from each scanner kept in the report. Enough to act on without
#: turning a state file into a log.
MAX_RECORDED_FINDINGS = 20

VERDICTS = ("pass", "notes", "fail")

#: A verdict summarised in five words attests to nothing, and "PASS" with no
#: sentence behind it is precisely the shape a fabricated audit takes.
MIN_SUMMARY = 30

#: An acknowledgement short enough to type without thinking is not a reason.
MIN_ACK = 30

#: How long a vertical's recorded evidence stays usable. Long enough to survive
#: an audit interrupted by a meeting, short enough that yesterday's verdict is
#: never quietly reused for today's change.
LEDGER_TTL = 24 * 3600


def parse_verticals(s: str):
    out = {}
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip().lower() or "pass"
    return out


TAIL_LINES = 20


def run_command(root, cmd: str, timeout: int):
    """Execute `cmd` in the repo and return (exit_code, tail_of_output).

    Returns (None, reason) when the command could not be run at all, so the
    caller can distinguish "it failed" from "it never ran".

    Output goes to a temp file rather than a pipe: a verbose suite can emit
    hundreds of megabytes over a long timeout, and only the tail is ever kept.
    The shell runs in its own process group so a timeout kills the whole test
    tree: killing just the shell would leave the real test process holding the
    output handle, and the wait would never return.
    """
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as out:
        try:
            proc = subprocess.Popen(
                cmd, shell=True, cwd=str(root),
                stdout=out, stderr=subprocess.STDOUT, start_new_session=True,
            )
        except Exception as exc:
            return None, f"could not execute: {exc}"
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            return None, f"timed out after {timeout}s"
        return code, _tail(out)


def _kill_tree(proc) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except Exception:
        pass


def _tail(fh) -> str:
    """Last TAIL_LINES of the run, with any secret in them redacted.

    The tail is persisted to `quality_report.json`; failing tests routinely print
    tokens and connection strings from the environment, and that file can end up
    staged by a `git add -A`.
    """
    try:
        fh.seek(max(0, fh.tell() - 64_000))
        lines = fh.read().strip().splitlines()[-TAIL_LINES:]
    except Exception:
        return ""
    kept = []
    for line in lines:
        found = common.scan_secrets_in_text(line)
        kept.append(f"[praxis: redacted, {', '.join(found)}]" if found else line)
    return "\n".join(kept)


# --------------------------------------------------------------------------- #
# The per-vertical evidence ledger
# --------------------------------------------------------------------------- #
def _split_citation(raw: str):
    """('src/a.py', '120-140') for a citation, with an empty range if none given.

    Split from the right on a numeric tail rather than parsed with one regex: a
    path may legitimately contain a colon, and an optional trailing group makes
    a single pattern ambiguous about which colon it owns.
    """
    path, _, tail = raw.rpartition(":")
    if path and re.fullmatch(r"\d+(?:-\d+)?", tail):
        return path.strip(), tail
    return raw.strip(), ""


def verify_citation(root, raw: str):
    """(ok, detail) for one `path` or `path:line` citation.

    This is where fabrication is actually caught. An auditor that read the code
    can name a file and a line from it for free; an audit that did not happen
    cannot, and inventing one fails here rather than three weeks later when
    somebody follows the reference.
    """
    path, span = _split_citation(raw)
    if not path:
        return False, "empty citation"
    rel = common.repo_relative(root, path)
    if rel is None:
        return False, f"`{path}` is outside this repository"
    target = root / rel
    if not target.is_file():
        return False, f"`{rel}` does not exist"
    if not span:
        return True, rel
    start, _, end = span.partition("-")
    first, last = int(start), int(end or start)
    if first < 1 or last < first:
        return False, f"`{raw}` is not a line range"
    try:
        total = len(target.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception as exc:
        return False, f"`{rel}` could not be read ({exc.__class__.__name__})"
    if last > total:
        return False, f"`{rel}` has {total} line(s), so line {last} does not exist"
    return True, f"{rel}:{span}"


def read_ledger(root) -> dict:
    entries = common.read_state(root, LEDGER).get("verticals")
    return entries if isinstance(entries, dict) else {}


def fresh_ledger(root) -> dict:
    """Ledger entries still inside their TTL."""
    now = time.time()
    return {k: v for k, v in read_ledger(root).items()
            if isinstance(v, dict) and (now - v.get("ts", 0)) < LEDGER_TTL}


def record_vertical(root, args) -> int:
    if not args or args[0].startswith("-"):
        print("usage: report.py vertical <name> --verdict pass|notes|fail "
              "--summary \"...\" --evidence \"path:line,path\"")
        return 1
    name = args[0].strip().lower()
    verdict = (common.cli_opt(args, "--verdict", "") or "").strip().lower()
    summary = " ".join((common.cli_opt(args, "--summary", "") or "").split())
    evidence = common.cli_opt(args, "--evidence", "") or ""

    if verdict not in VERDICTS:
        print(f"praxis: --verdict must be one of {', '.join(VERDICTS)} "
              f"(got '{verdict}').")
        return 1
    if len(summary) < MIN_SUMMARY:
        print(f"praxis: --summary must say what was examined and concluded "
              f"(at least {MIN_SUMMARY} characters). A one-word verdict is the "
              "shape an audit takes when it did not happen.")
        return 1

    cited, problems = [], []
    for raw in evidence.split(","):
        raw = raw.strip()
        if not raw:
            continue
        ok, detail = verify_citation(root, raw)
        (cited if ok else problems).append(detail)
    if problems:
        print(f"praxis: refusing to record '{name}': "
              f"{len(problems)} citation(s) do not resolve.")
        for p in problems:
            print(f"  - {p}")
        print("Cite what you actually read. A reference that does not resolve is "
              "worse than none: it reads as verified and is not.")
        return 1
    if not cited:
        print(f"praxis: '{name}' needs --evidence with at least one citation "
              "(`path` or `path:line`) naming what this vertical examined.")
        return 1

    state = common.read_state(root, LEDGER)
    entries = state.get("verticals")
    state["verticals"] = entries if isinstance(entries, dict) else {}
    state["verticals"][name] = {
        "verdict": verdict,
        "summary": summary,
        "evidence": cited,
        "ts": time.time(),
        "signature": common.change_signature(root),
    }
    try:
        common.write_state_strict(root, LEDGER, state)
    except Exception as exc:
        print(f"praxis: could not write the evidence ledger: {exc}")
        return 1
    print(f"praxis: {name}={verdict} recorded, {len(cited)} citation(s) verified "
          f"({', '.join(cited[:3])}{'...' if len(cited) > 3 else ''}).")
    return 0


def missing_evidence(root, verticals: dict):
    """(missing, mismatched, stale) for the verdicts a report is about to claim."""
    ledger = fresh_ledger(root)
    sig = common.change_signature(root)
    missing = [k for k in verticals if k not in ledger]
    mismatched = [f"{k}: claimed {v}, recorded {ledger[k].get('verdict')}"
                  for k, v in verticals.items()
                  if k in ledger and ledger[k].get("verdict") != v]
    stale = [k for k in verticals
             if k in ledger and ledger[k].get("signature") not in (sig, None)]
    return missing, mismatched, stale


# --------------------------------------------------------------------------- #
# The deterministic scanners
# --------------------------------------------------------------------------- #
def run_scan(root, script: str):
    """(ran, findings) for one sibling `--json` scanner.

    Unlike `common.run_scanner`, a scanner that could not run is reported as
    such rather than as an empty list. The hooks fail open because a broken
    scanner must not wedge a session; a *report* that failed open would state
    that a check passed when it never executed, which is the one thing this
    file exists not to do.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)
    try:
        out = subprocess.run(
            [sys.executable, path, "--json"], capture_output=True, text=True,
            timeout=SCAN_TIMEOUT, cwd=str(root),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        findings = json.loads(out.stdout or "{}").get("findings", [])
        return True, (findings if isinstance(findings, list) else [])
    except Exception as exc:
        print(f"praxis: {script} did not run ({exc.__class__.__name__}: {exc}).")
        return False, []


def _cited(findings, limit=5):
    for f in findings[:limit]:
        loc = f"{f.get('file', '?')}:{f.get('line', '?')}"
        print(f"    - [{f.get('marker') or f.get('kind') or 'finding'}] {loc}  "
              f"{(f.get('text') or f.get('detail') or '')[:120]}")
    if len(findings) > limit:
        print(f"    - ... and {len(findings) - limit} more")


# --------------------------------------------------------------------------- #
# Recording the report
# --------------------------------------------------------------------------- #
def _guard_command(cmd: str, kind: str) -> None:
    """A command this script executes must not become a way to read a secret."""
    for token in cmd.replace("'", " ").replace('"', " ").split():
        if common.is_sensitive_path(token):
            print(f"praxis: refusing to run a {kind} command touching {token}.")
            raise SystemExit(1)


def _timeout(args, flag: str) -> int:
    try:
        return int(common.cli_opt(args, flag, TEST_TIMEOUT))
    except ValueError:
        return TEST_TIMEOUT


def record(root, args) -> None:
    detected = common.detect_test_command(root)
    tests = common.cli_opt(args, "--tests", detected)
    verticals = parse_verticals(common.cli_opt(args, "--verticals", ""))
    cfg = common.read_config(root)

    # Running *a* command proves nothing; running the project's tests does. A
    # substituted command (`--tests true`, `pytest || true`) would otherwise buy
    # a green report for a suite that never ran, which is the exact loophole this
    # script exists to close. Overriding is still legitimate: a monorepo package,
    # a narrower selection, so it is recorded rather than refused, and the gate
    # decides whether to accept it.
    substituted = bool(detected) and tests.strip() != detected.strip()
    if substituted:
        print(f"praxis: recording a substituted test command (detected: `{detected}`).")

    # `--tests-exit` was how the exit code used to be supplied. It is still
    # accepted so existing invocations don't break, but it is never trusted, and
    # saying so is better than silently ignoring an argument the caller believes
    # is taking effect.
    if common.cli_opt(args, "--tests-exit", None) is not None:
        print("praxis: --tests-exit is ignored, report.py runs the tests and "
              "records the real exit code.")

    # The report's whole value is that it is evidence, not a claim, so the test
    # run happens HERE, and its real exit code is what gets recorded.
    tests_exit, tests_output, verified = None, "", False
    if tests:
        _guard_command(tests, "test")
        tests_exit, tests_output = run_command(root, tests, _timeout(args, "--timeout"))
        verified = tests_exit is not None
        if verified:
            print(f"praxis: ran `{tests}` -> exit {tests_exit}")
        else:
            print(f"praxis: `{tests}` did not run ({tests_output}).")
        if tests_exit not in (0, None) and tests_output:
            print(tests_output)

    runtime = _runtime_evidence(root, args, cfg)
    scans, scans_ran = _scan_evidence(root)
    knowledge_ack = " ".join((common.cli_opt(args, "--knowledge-ack", "") or "").split())

    blocking = _blocking_scans(cfg, scans, knowledge_ack)

    # An empty vertical set used to count as "all pass", so a bare `report.py
    # record` produced a green report attesting to nothing at all.
    all_pass = bool(verticals) and all(v == "pass" for v in verticals.values())
    if not verticals:
        print("praxis: no --verticals given, a report attests to the auditors that "
              "actually ran, so this is recorded as 'fail'.")

    evidence_gap = _evidence_gap(root, verticals, cfg)

    # The gate rejects a UI change with no UI verdicts anyway. Saying so here,
    # right after the auditors were supposed to run, turns a confusing Stop-time
    # refusal into an actionable one.
    ui_missing = common.missing_ui_verticals(root, verticals)
    if ui_missing:
        touched = common.ui_files_in_change(root)
        print(f"praxis: this change touches user-facing files "
              f"({', '.join(touched[:3])}{'...' if len(touched) > 3 else ''}), so it "
              f"needs the UI verticals. Missing: {', '.join(ui_missing)}.")

    tests_ok = (tests_exit == 0) if tests else True
    runtime_ok = (not runtime["required"]) or runtime["exit"] == 0
    status = "pass" if (all_pass and tests_ok and runtime_ok and not ui_missing
                        and not blocking and not evidence_gap and scans_ran) else "fail"

    report = {
        "signature": common.change_signature(root),
        "status": status,
        "ts": time.time(),
        "evidence": {
            "test_command": tests or "",
            "detected_test_command": detected or "",
            "test_substituted": substituted,
            "test_exit": tests_exit,
            "test_verified": verified,
            # Kept for any non-passing run, including one that never started:
            # on a timeout or a missing binary the reason IS the diagnosis.
            "test_output_tail": "" if tests_exit == 0 else tests_output,
            "runtime": runtime,
            "scans": scans,
            "scans_verified": scans_ran,
            "knowledge_ack": knowledge_ack,
            "verticals": verticals,
            "vertical_evidence": {k: v for k, v in fresh_ledger(root).items()
                                  if k in verticals},
        },
    }
    common.write_state(root, NAME, report)
    print(f"praxis: quality report recorded, status={status}, "
          f"tests={tests or 'none'} exit={tests_exit}, "
          f"verticals={'all pass' if all_pass else 'NOT all pass'}")
    if status != "pass":
        print("praxis: status is 'fail', the Stop gate will keep you working until green.")
        if not all_pass and verticals:
            failed = sorted(k for k, v in verticals.items() if v != "pass")
            print(f"praxis: failing vertical(s): {', '.join(failed)}")


def _runtime_evidence(root, args, cfg) -> dict:
    """Run the project's end-to-end harness when this change owes one.

    Owed when the change touches user-facing surface and the project already has
    a harness: the two conditions together mean a check exists that would catch
    what the unit suite cannot, and the change is of the kind it catches. An
    explicit `--runtime` always runs, because asking for it is reason enough.
    """
    detected = common.detect_runtime_command(root)
    given = common.cli_opt(args, "--runtime", None)
    ui = common.ui_files_in_change(root)
    required = bool(detected and ui and cfg.get("gate.require_runtime", True))
    cmd = (given if given is not None else (detected if required else ""))

    result = {"command": cmd or "", "detected": detected or "",
              "required": required, "exit": None, "verified": False,
              "output_tail": "", "ui_files": len(ui)}
    if not cmd:
        if required:
            # Unreachable while `required` implies `detected`, but a caller can
            # pass `--runtime ""` to blank it, and a silent skip there would be
            # the report lying by omission.
            print("praxis: this change needs a runtime check and no command was "
                  "given. Pass --runtime \"<cmd>\", or set "
                  "`require_runtime = false` under [gate] and say why.")
        elif detected and ui:
            print(f"praxis: runtime check skipped (`{detected}` detected but "
                  "gate.require_runtime is off).")
        elif ui and not detected:
            print(f"praxis: {len(ui)} user-facing file(s) changed and this project "
                  "has no end-to-end harness. Verify the change in the running "
                  "product yourself (the `runtime-verification` skill covers how) "
                  "and say in the report what you exercised.")
        return result

    _guard_command(cmd, "runtime")
    exit_code, tail = run_command(root, cmd, _timeout(args, "--runtime-timeout"))
    result["exit"] = exit_code
    result["verified"] = exit_code is not None
    result["output_tail"] = "" if exit_code == 0 else tail
    if exit_code is None:
        print(f"praxis: `{cmd}` did not run ({tail}).")
    else:
        print(f"praxis: runtime check ran `{cmd}` -> exit {exit_code}")
        if exit_code != 0 and tail:
            print(tail)
    return result


def _scan_evidence(root):
    """Run every deterministic scanner and return (results, all_of_them_ran)."""
    scans, ran_all = {}, True
    for key, script, label in SCANNERS:
        ran, findings = run_scan(root, script)
        ran_all = ran_all and ran
        scans[key] = {"ran": ran, "count": len(findings),
                      "findings": findings[:MAX_RECORDED_FINDINGS]}
        if not ran:
            print(f"praxis: {label} could not be checked, so this report cannot "
                  "be green. Fix the scanner or the environment and re-record.")
        elif findings:
            print(f"praxis: {len(findings)} {label} in this change:")
            _cited(findings)
    return scans, ran_all


def _blocking_scans(cfg, scans, ack: str):
    """Scanner results that keep the report from being green."""
    blocking = []
    for key, _script, label in SCANNERS:
        count = scans.get(key, {}).get("count", 0)
        if not count:
            continue
        if key == "knowledge":
            if not cfg.get("gate.require_knowledge", True):
                continue
            if len(ack) >= MIN_ACK:
                print(f"praxis: {count} {label} acknowledged: \"{ack}\"")
                continue
            if ack:
                print(f"praxis: --knowledge-ack must give a real reason (at least "
                      f"{MIN_ACK} characters).")
        blocking.append(f"{label} ({count})")
    if blocking:
        print(f"praxis: unresolved: {', '.join(blocking)}. Fix them in the code "
              "and the docs, not in the report.")
    return blocking


def _evidence_gap(root, verticals, cfg):
    """Verdicts claimed without recorded evidence, reported as they are found."""
    if not verticals or not cfg.get("gate.require_evidence", True):
        return []
    missing, mismatched, stale = missing_evidence(root, verticals)
    if stale:
        # A warning, not a gap: the report itself is signature-keyed, so the gate
        # already rejects a stale audit. This only says which verdicts were
        # reached before the code reached its current state.
        print(f"praxis: evidence for {', '.join(sorted(stale))} was recorded "
              "against an earlier state of the change. Re-run those auditors if "
              "the code they read has since moved.")
    if mismatched:
        print("praxis: a claimed verdict contradicts its recorded evidence:")
        for m in sorted(mismatched):
            print(f"  - {m}")
    if missing:
        print(f"praxis: no recorded evidence for: {', '.join(sorted(missing))}.")
        print("  Record each auditor's verdict as it finishes:")
        print("    report.py vertical <name> --verdict pass --summary \"...\" "
              "--evidence \"path:line\"")
        print("  A verdict with nothing behind it is the shape an audit takes "
              "when it did not run. Turn this off with "
              "`require_evidence = false` under [gate] if your workflow records "
              "it elsewhere.")
    return sorted(set(missing) | set(mismatched))


def show(root, args) -> None:
    if "--ledger" in args:
        print(json.dumps(read_ledger(root) or {"(no evidence recorded)": True}, indent=2))
        return
    print(json.dumps(common.read_state(root, NAME) or {"(no report)": True}, indent=2))


def main() -> int:
    root = common.project_dir({})
    args = sys.argv[1:]
    if not args:
        print("usage: report.py record [--tests CMD] [--timeout SECONDS] "
              "[--runtime CMD] [--runtime-timeout SECONDS] "
              "[--knowledge-ack REASON] [--verticals a=pass,...]\n"
              "       report.py vertical <name> --verdict pass|notes|fail "
              "--summary \"...\" --evidence \"path:line,...\"\n"
              "       report.py show [--ledger]")
        return 1
    if args[0] == "record":
        record(root, args[1:])
    elif args[0] == "vertical":
        return record_vertical(root, args[1:])
    elif args[0] == "show":
        show(root, args[1:])
    else:
        print(f"praxis: unknown command '{args[0]}'")
        return 1
    return 0


if __name__ == "__main__":
    # Unlike the hooks, this is a CLI whose exit code the caller reads: failing
    # open would report a green audit that was never written.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"praxis: failed to record the quality report: {exc}")
        sys.exit(1)
