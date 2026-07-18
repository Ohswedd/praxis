#!/usr/bin/env python3
"""
praxis placeholder / incompleteness scanner (utility).

Deterministic backstop for the rule "nothing left unfinished, no placeholders,
no silently-narrowed scope". Scans either the working-tree diff (default) or
given files for markers that signal unfinished or stubbed work.

Usage:
    python3 scan_placeholders.py                # scan `git diff` added lines
    python3 scan_placeholders.py --all          # scan all tracked files
    python3 scan_placeholders.py <file> [...]   # scan specific files
    python3 scan_placeholders.py --json         # machine-readable output

Exit code: 0 if clean, 1 if any marker found (so it can gate). The
completeness-auditor subagent layers judgement on top (some markers are
legitimate and pre-existing); this tool supplies the raw, cited signal.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


# (label, regex). Kept high-signal to limit false positives.
MARKERS = [
    ("TODO/FIXME/XXX/HACK", r"\b(TODO|FIXME|XXX|HACK)\b"),
    ("not-implemented (py)", r"\braise\s+NotImplementedError\b|\bNotImplemented\b"),
    ("not-implemented (rust)", r"\b(unimplemented!|todo!)\s*\("),
    ("not-implemented (go/generic)", r"panic\(\s*['\"](TODO|not implemented|unimplemented)"),
    ("not-implemented (js/ts)", r"throw new Error\(\s*['\"](TODO|not implemented|unimplemented)"),
    ("placeholder token", r"<\s*(placeholder|your[_-].+?|fill[_-]?in|todo)\s*>|__(PLACEHOLDER|FIXME)__"),
    ("stub ellipsis", r"^\s*\.\.\.\s*(#.*)?$"),
    ("empty pass stub", r"^\s*pass\s*#\s*(todo|stub|implement)"),
    ("hardcoded change-me", r"(?i)(change[_-]?me|replace[_-]?this|dummy[_-]?value|example\.com/api)"),
    ("debug leftover", r"\b(console\.log|println!|System\.out\.println|debugger)\b\s*\(.*(debug|test|xxx)"),
    ("commented-out code block",
     r"^\s*//\s*(def|function|class|public|private|const|let|var|return|if|for)\b.*[;{]\s*$"
     r"|^\s*#\s*(def|class)\b.*:\s*$"),
]

_COMPILED = [(label, re.compile(pat, re.MULTILINE)) for label, pat in MARKERS]


def added_lines_from_diff(root: Path) -> list:
    """Return (file, lineno, text) for lines ADDED in the working-tree diff."""
    out = common._run(["git", "diff", "--unified=0", "--no-color"], cwd=root, timeout=20)
    if not out:
        out = common._run(["git", "diff", "--staged", "--unified=0", "--no-color"],
                          cwd=root, timeout=20)
    results = []
    cur_file = None
    new_ln = 0
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            cur_file = line[6:].strip()
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            new_ln = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            results.append((cur_file, new_ln, line[1:]))
            new_ln += 1
    return results


def scan_text_lines(pairs) -> list:
    findings = []
    for fname, lineno, text in pairs:
        for label, rx in _COMPILED:
            if rx.search(text):
                findings.append({"file": fname, "line": lineno,
                                 "marker": label, "text": text.strip()[:160]})
    return findings


def scan_files(paths) -> list:
    pairs = []
    for p in paths:
        fp = Path(p)
        try:
            for i, line in enumerate(fp.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                pairs.append((str(p), i, line))
        except Exception:
            continue
    return scan_text_lines(pairs)


def main() -> int:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    root = common.project_dir({})

    if args == ["--all"]:
        findings = scan_files(str(root / f) for f in common.tracked_files(root))
    elif args:
        findings = scan_files(args)
    else:
        findings = scan_text_lines(added_lines_from_diff(root))

    if as_json:
        print(json.dumps({"count": len(findings), "findings": findings}, indent=2))
    else:
        if not findings:
            print("praxis: no placeholder/incompleteness markers found.")
        else:
            print(f"praxis: {len(findings)} placeholder/incompleteness marker(s):")
            for f in findings:
                loc = f"{f['file']}:{f['line']}" if f["file"] else "?"
                print(f"  - [{f['marker']}] {loc}  {f['text']}")
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open: never break a session because the scanner errored.
        sys.exit(0)
