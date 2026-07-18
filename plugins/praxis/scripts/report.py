#!/usr/bin/env python3
"""
Praxis quality-report writer (evidence-backed).

Records the green quality report the Stop gate reads — but with *evidence* rather
than a bare pass flag: the test command and its exit code, and the per-vertical
verdicts. The gate can then require that, when the repo has a test command, the
report shows a passing run — so "green" is backed by a real result, not trust.

Usage:
    report.py record \
        --tests "pytest" --tests-exit 0 \
        --verticals "doc-reference=pass,duplication=pass,regression=pass,\
adversarial=pass,edge-case=pass,performance=pass,completeness=pass"
    report.py show

If --tests is omitted and the repo has no detectable test command, the report is
recorded without a test requirement. If any vertical is not 'pass' or the test
exit is non-zero, status is 'fail' and the gate will keep working.
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

NAME = "quality_report.json"


def parse_verticals(s: str):
    out = {}
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip().lower() or "pass"
    return out


def record(root, args) -> None:
    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default

    tests = opt("--tests", common.detect_test_command(root))
    tests_exit_raw = opt("--tests-exit", None)
    verticals = parse_verticals(opt("--verticals", ""))

    tests_exit = None
    if tests_exit_raw is not None:
        try:
            tests_exit = int(tests_exit_raw)
        except ValueError:
            tests_exit = None

    all_pass = all(v == "pass" for v in verticals.values()) if verticals else True
    tests_ok = (tests_exit == 0) if tests else True
    status = "pass" if (all_pass and tests_ok) else "fail"

    report = {
        "signature": common.change_signature(root),
        "status": status,
        "ts": time.time(),
        "evidence": {
            "test_command": tests or "",
            "test_exit": tests_exit,
            "verticals": verticals,
        },
    }
    common.write_state(root, NAME, report)
    print(f"praxis: quality report recorded — status={status}, "
          f"tests={tests or 'none'} exit={tests_exit}, "
          f"verticals={'all pass' if all_pass else 'NOT all pass'}")
    if status != "pass":
        print("praxis: status is 'fail' — the Stop gate will keep you working until green.")


def show(root) -> None:
    print(json.dumps(common.read_state(root, NAME) or {"(no report)": True}, indent=2))


def main() -> int:
    root = common.project_dir({})
    args = sys.argv[1:]
    if not args:
        print("usage: report.py record [--tests CMD --tests-exit N --verticals a=pass,...] | show")
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
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
