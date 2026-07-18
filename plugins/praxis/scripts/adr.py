#!/usr/bin/env python3
"""
Praxis ADR maintainer (operates on the *target project's* docs/adr/).

Architecture Decision Records capture *why* a significant or autonomous decision
was made, so the knowledge survives. In auto-pilot, every non-trivial autonomous
decision should also be persisted here — not only in the report.

Usage:
    adr.py new "Use optimistic locking for order updates" \
        --status accepted \
        --context "High read/low write contention; ..." \
        --decision "Adopt optimistic locking with a version column." \
        --consequences "Retries on conflict; simpler than pessimistic locks."
    adr.py list

Files: docs/adr/NNNN-kebab-title.md, sequentially numbered.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


def adr_dir(root):
    d = root / "docs" / "adr"
    d.mkdir(parents=True, exist_ok=True)
    return d


def next_number(d) -> int:
    n = 0
    for f in d.glob("[0-9][0-9][0-9][0-9]-*.md"):
        try:
            n = max(n, int(f.name[:4]))
        except ValueError:
            pass
    return n + 1


def kebab(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return s[:60] or "decision"


def arg(args, name, default=""):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


def new(root, args) -> None:
    title = args[0]
    status = arg(args, "--status", "accepted")
    context = arg(args, "--context", "")
    decision = arg(args, "--decision", "")
    consequences = arg(args, "--consequences", "")
    alternatives = arg(args, "--alternatives", "")

    d = adr_dir(root)
    num = next_number(d)
    fname = f"{num:04d}-{kebab(title)}.md"
    body = f"""# {num}. {title}

- Status: {status}
- Date: {_dt.date.today().isoformat()}

## Context
{context or "_Describe the forces and constraints that led to this decision._"}

## Decision
{decision or "_State the decision clearly._"}

## Consequences
{consequences or "_State the resulting trade-offs, positive and negative._"}
"""
    if alternatives:
        body += f"\n## Alternatives considered\n{alternatives}\n"
    (d / fname).write_text(body, encoding="utf-8")
    print(f"praxis: ADR created — docs/adr/{fname}")


def list_adrs(root) -> None:
    d = adr_dir(root)
    files = sorted(d.glob("[0-9][0-9][0-9][0-9]-*.md"))
    if not files:
        print("praxis: no ADRs yet.")
        return
    for f in files:
        first = f.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        print(f"  {first}  ({f.name})")


def main() -> int:
    root = common.project_dir({})
    args = sys.argv[1:]
    if not args:
        print("usage: adr.py new \"title\" [--status --context --decision --consequences --alternatives] | list")
        return 1
    if args[0] == "new":
        if len(args) < 2:
            print("usage: adr.py new \"title\" ..."); return 1
        new(root, args[1:])
    elif args[0] == "list":
        list_adrs(root)
    else:
        print(f"praxis: unknown command '{args[0]}'"); return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
