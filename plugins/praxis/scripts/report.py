#!/usr/bin/env python3
"""
Praxis quality-report writer (evidence-backed).

Records the green quality report the Stop gate reads — but with *evidence*
rather than a bare pass flag: the per-vertical verdicts, and a test run this
script performs **itself**.

Running the tests here rather than accepting a reported exit code is the point.
The gate's guarantee is only as strong as its weakest input, and a caller-supplied
"--tests-exit 0" is a claim, not a result: it would let an unverified green report
close the gate on a regression. So the command is executed, its real exit code is
recorded, and a failing run's output tail is kept for diagnosis.

Usage:
    report.py record \
        [--tests "pytest"] [--timeout 900] \
        --verticals "doc-reference=pass,duplication=pass,regression=pass,\
adversarial=pass,edge-case=pass,performance=pass,completeness=pass"
    report.py show

--tests defaults to the repo's detected test command. Overriding it is recorded
as a substitution, because running *a* command proves nothing while running the
project's suite proves something: the gate does not accept a substituted run on
its own (a legitimate override — one package of a monorepo — should be stated to
the user). If the repo has no detectable test command and none is given, the
report is recorded without a test requirement, and the missing coverage should be
reported. A report with no vertical verdicts attests to nothing and is 'fail'.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

NAME = "quality_report.json"

# Generous enough for a real suite, bounded so a hung test run can't wedge the
# session. Override per-invocation with --timeout.
TEST_TIMEOUT = 900


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


def run_tests(root, cmd: str, timeout: int):
    """Execute `cmd` in the repo and return (exit_code, tail_of_output).

    Returns (None, reason) when the command could not be run at all, so the
    caller can distinguish "tests failed" from "tests never ran".

    Output goes to a temp file rather than a pipe: a verbose suite can emit
    hundreds of megabytes over a long timeout, and only the tail is ever kept.
    The shell runs in its own process group so a timeout kills the whole test
    tree — killing just the shell would leave the real test process holding the
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
        kept.append(f"[praxis: redacted — {', '.join(found)}]" if found else line)
    return "\n".join(kept)


def record(root, args) -> None:
    detected = common.detect_test_command(root)
    tests = common.cli_opt(args, "--tests", detected)
    verticals = parse_verticals(common.cli_opt(args, "--verticals", ""))

    # Running *a* command proves nothing; running the project's tests does. A
    # substituted command (`--tests true`, `pytest || true`) would otherwise buy
    # a green report for a suite that never ran, which is the exact loophole this
    # script exists to close. Overriding is still legitimate — a monorepo package,
    # a narrower selection — so it is recorded rather than refused, and the gate
    # decides whether to accept it.
    substituted = bool(detected) and tests.strip() != detected.strip()
    if substituted:
        print(f"praxis: recording a substituted test command (detected: `{detected}`).")

    # The command is executed, so it must not become a way to read a secret that
    # guard_paths would refuse for an ordinary Bash call.
    for token in tests.replace("'", " ").replace('"', " ").split():
        if common.is_sensitive_path(token):
            print(f"praxis: refusing to run a test command touching {token}.")
            raise SystemExit(1)
    try:
        timeout = int(common.cli_opt(args, "--timeout", TEST_TIMEOUT))
    except ValueError:
        timeout = TEST_TIMEOUT

    # `--tests-exit` was how the exit code used to be supplied. It is still
    # accepted so existing invocations don't break, but it is never trusted, and
    # saying so is better than silently ignoring an argument the caller believes
    # is taking effect.
    if common.cli_opt(args, "--tests-exit", None) is not None:
        print("praxis: --tests-exit is ignored — report.py runs the tests and "
              "records the real exit code.")

    # The report's whole value is that it is evidence, not a claim — so the test
    # run happens HERE, and its real exit code is what gets recorded.
    tests_exit, tests_output, verified = None, "", False
    if tests:
        tests_exit, tests_output = run_tests(root, tests, timeout)
        verified = tests_exit is not None
        if verified:
            print(f"praxis: ran `{tests}` → exit {tests_exit}")
        else:
            print(f"praxis: `{tests}` did not run ({tests_output}).")
        if tests_exit not in (0, None) and tests_output:
            print(tests_output)

    # An empty vertical set used to count as "all pass", so a bare `report.py
    # record` produced a green report attesting to nothing at all.
    all_pass = bool(verticals) and all(v == "pass" for v in verticals.values())
    if not verticals:
        print("praxis: no --verticals given — a report attests to the auditors that "
              "actually ran, so this is recorded as 'fail'.")
    tests_ok = (tests_exit == 0) if tests else True
    status = "pass" if (all_pass and tests_ok) else "fail"

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
            "verticals": verticals,
        },
    }
    common.write_state(root, NAME, report)
    print(f"praxis: quality report recorded — status={status}, "
          f"tests={tests or 'none'} exit={tests_exit}, "
          f"verticals={'all pass' if all_pass else 'NOT all pass'}")
    if status != "pass":
        print("praxis: status is 'fail' — the Stop gate will keep you working until green.")
        if not all_pass:
            failed = sorted(k for k, v in verticals.items() if v != "pass")
            print(f"praxis: failing vertical(s): {', '.join(failed)}")


def show(root) -> None:
    print(json.dumps(common.read_state(root, NAME) or {"(no report)": True}, indent=2))


def main() -> int:
    root = common.project_dir({})
    args = sys.argv[1:]
    if not args:
        print("usage: report.py record [--tests CMD] [--timeout SECONDS] "
              "[--verticals a=pass,...] | show")
        return 1
    if args[0] == "record":
        record(root, args[1:])
    elif args[0] == "show":
        show(root)
    else:
        print(f"praxis: unknown command '{args[0]}'")
        return 1
    return 0


if __name__ == "__main__":
    # Unlike the hooks, this is a CLI whose exit code the caller reads: failing
    # open would report a green audit that was never written.
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"praxis: failed to record the quality report: {exc}")
        sys.exit(1)
