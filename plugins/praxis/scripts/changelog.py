#!/usr/bin/env python3
"""
Praxis changelog maintainer (operates on the *target project's* CHANGELOG.md).

Keeps a Keep-a-Changelog file current so the project's history is never lost —
every change is recorded under [Unreleased] as it happens, preserving knowledge
without regression. Change types map to Conventional Commits
(feat→Added, fix→Fixed, etc.).

Usage:
    changelog.py add --type added   "Stripe checkout integration"
    changelog.py add --type fixed   "off-by-one in pagination offset"
    changelog.py release 1.4.0        # move [Unreleased] into a dated version
    changelog.py show                 # print the [Unreleased] section

Types: added | changed | fixed | removed | deprecated | security
"""

from __future__ import annotations

import datetime as _dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

TYPES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]

HEADER = """# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]
"""


def path(root):
    return root / "CHANGELOG.md"


def ensure(root) -> str:
    p = path(root)
    if not p.exists():
        p.write_text(HEADER, encoding="utf-8")
    return p.read_text(encoding="utf-8")


def add(root, ctype: str, message: str) -> None:
    ctype = ctype.strip().capitalize()
    if ctype not in TYPES:
        print(f"praxis: unknown type '{ctype}'. Use one of: {', '.join(t.lower() for t in TYPES)}")
        return
    text = ensure(root)
    lines = text.splitlines()

    # locate [Unreleased] header
    try:
        u = next(i for i, l in enumerate(lines) if l.strip().lower().startswith("## [unreleased]"))
    except StopIteration:
        lines.insert(0, "## [Unreleased]"); u = 0

    # find the end of the [Unreleased] section (next '## ' or EOF)
    end = len(lines)
    for i in range(u + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    # find the type subsection within [Unreleased]
    sub = None
    for i in range(u + 1, end):
        if lines[i].strip().lower() == f"### {ctype.lower()}":
            sub = i
            break

    bullet = f"- {message}"
    if sub is None:
        # insert subsection in canonical order just after the Unreleased header block
        insert_at = u + 1
        while insert_at < end and not lines[insert_at].startswith("### ") and lines[insert_at].strip() == "":
            insert_at += 1
        block = [f"### {ctype}", bullet, ""]
        lines[insert_at:insert_at] = block
    else:
        # append bullet right after the last existing bullet in the subsection
        last_bullet = sub
        j = sub + 1
        while j < end and not lines[j].startswith("### ") and not lines[j].startswith("## "):
            if lines[j].startswith("- "):
                last_bullet = j
            j += 1
        lines.insert(last_bullet + 1, bullet)

    path(root).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"praxis: CHANGELOG [Unreleased] › {ctype}: {message}")


def release(root, version: str) -> None:
    text = ensure(root)
    today = _dt.date.today().isoformat()
    if "## [Unreleased]" not in text:
        print("praxis: no [Unreleased] section."); return
    text = text.replace("## [Unreleased]",
                        f"## [Unreleased]\n\n## [{version}] - {today}", 1)
    path(root).write_text(text, encoding="utf-8")
    print(f"praxis: released {version} ({today}).")


def show(root) -> None:
    text = ensure(root)
    lines = text.splitlines()
    try:
        u = next(i for i, l in enumerate(lines) if l.strip().lower().startswith("## [unreleased]"))
    except StopIteration:
        print("(no [Unreleased] section)"); return
    end = len(lines)
    for i in range(u + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i; break
    print("\n".join(lines[u:end]).strip() or "## [Unreleased]\n(empty)")


def main() -> int:
    root = common.project_dir({})
    args = sys.argv[1:]
    if not args:
        print("usage: changelog.py add --type <t> \"msg\" | release <ver> | show"); return 1
    cmd = args[0]
    if cmd == "add":
        ctype, msg = "Changed", None
        if "--type" in args:
            ctype = args[args.index("--type") + 1]
        rest = [a for k, a in enumerate(args[1:], 1)
                if a not in ("--type", ctype)]
        msg = " ".join(rest).strip()
        if not msg:
            print("praxis: nothing to add (empty message)."); return 1
        add(root, ctype, msg)
    elif cmd == "release":
        if len(args) < 2:
            print("usage: changelog.py release <version>"); return 1
        release(root, args[1])
    elif cmd == "show":
        show(root)
    else:
        print(f"praxis: unknown command '{cmd}'"); return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
