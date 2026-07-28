#!/usr/bin/env python3
"""
praxis house-style scanner (utility).

Deterministic backstop for two rules that are stated everywhere in praxis's
doctrine and still get broken, because prose instructions are easy to comply with
in the abstract and forget in the moment:

  * **No em dashes.** As a sentence break the em dash is the most recognisable
    tell of unedited generated prose. A colon, a comma, parentheses, or a full
    stop always says the same thing more precisely. The spaced en dash is banned
    with it; the unspaced en dash of a numeric range is correct and is left alone.
  * **No AI attribution.** A `Co-Authored-By: Claude` trailer, a "generated with"  praxis:ack: the rule names the shape it refuses
    footer, or a robot emoji credit hands the project's authorship to the tool
    that typed it. The history and the pull requests belong to the project.

Scans the current change by default (unstaged diff + staged diff + untracked
files), or the files you name. A line carrying `praxis:ack` is exempt, which is
how a legitimate case is recorded, such as a fixture that must contain the very
character being matched.

Usage:
    python3 scan_style.py                  # scan the current change
    python3 scan_style.py --all            # scan all tracked files
    python3 scan_style.py <file> [...]     # scan specific files
    python3 scan_style.py --json           # machine-readable output

Exit code: 0 if clean, 1 if any finding, so it can gate.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

# Config keys that switch each category off, for a project that genuinely wants
# one of them (a typography-heavy site, a fork that credits its tooling).
_CATEGORY_CONFIG = {
    "dash": "style.ban_em_dash",
    "attribution": "style.ban_ai_attribution",
}


def _enabled(root: Path) -> dict:
    cfg = common.read_config(root)
    return {cat: bool(cfg.get(key, True)) for cat, key in _CATEGORY_CONFIG.items()}


def scan_text_lines(pairs, enabled: dict) -> list:
    """Findings for (file, lineno, text) triples."""
    findings = []
    for fname, lineno, text in pairs:
        if common.is_acked(text):
            continue
        if enabled.get("dash"):
            for name in common.scan_banned_dashes(text):
                findings.append(_finding(fname, lineno, "dash", name, text))
        if enabled.get("attribution"):
            for name in common.scan_ai_attribution(text):
                findings.append(_finding(fname, lineno, "attribution", name, text))
    return findings


def _finding(fname, lineno, category, marker, text) -> dict:
    return {
        "file": fname,
        "line": lineno,
        "category": category,
        "marker": marker,
        "text": text.strip()[:160],
        "fix": _FIX[category],
    }


_FIX = {
    "dash": "rewrite with a colon, a comma, parentheses, or two sentences",
    "attribution": "remove the credit; the work is the project's own",
}


def scan_files(root: Path, rels, enabled: dict) -> list:
    pairs = []
    for rel in rels:
        fp = Path(rel)
        if not fp.is_absolute():
            fp = root / rel
        try:
            body = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(body.splitlines(), 1):
            pairs.append((str(rel), i, line))
    return scan_text_lines(pairs, enabled)


def main() -> int:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    root = common.project_dir({})
    enabled = _enabled(root)

    if not any(enabled.values()):
        if as_json:
            print(json.dumps({"count": 0, "findings": [], "disabled": True}, indent=2))
        else:
            print("praxis: house-style checks are disabled in .praxis.toml.")
        return 0

    if args == ["--all"]:
        rels = [f for f in common.tracked_files(root) if common.is_scannable(root, f)]
        findings = scan_files(root, rels, enabled)
    elif args:
        findings = scan_files(root, args, enabled)
    else:
        findings = scan_text_lines(common.added_line_pairs(root), enabled)

    if as_json:
        print(json.dumps({"count": len(findings), "findings": findings}, indent=2))
    elif not findings:
        print("praxis: no house-style violations found.")
    else:
        print(f"praxis: {len(findings)} house-style violation(s):")
        for f in findings:
            loc = f"{f['file']}:{f['line']}" if f["file"] else "?"
            print(f"  - [{f['marker']}] {loc}  {f['text']}")
            print(f"      fix: {f['fix']}")
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open: never break a session because the scanner errored.
        sys.exit(0)
