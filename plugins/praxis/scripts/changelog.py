#!/usr/bin/env python3
"""
Praxis changelog maintainer (operates on the *target project's* CHANGELOG.md).

Keeps a Keep-a-Changelog file current so the project's history is never lost:
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
    """The changelog this repo's mode says to write.

    In a repository we only contribute to, an existing `CHANGELOG.md` is joined
    (a pull request that skipped the project's own changelog is a worse pull
    request), and a missing one is left missing: introducing the convention is the
    maintainers' call, so praxis keeps that record under `.claude/.praxis/`.
    """
    return common.knowledge_path(root, "CHANGELOG.md")


def ensure(root) -> str:
    p = path(root)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HEADER, encoding="utf-8")
    return p.read_text(encoding="utf-8")


def _canonical_insert_index(lines, unreleased, section_end, ctype) -> int:
    """Index for a new '### ctype' block that keeps subsections in TYPES order.

    Places the block after every subsection that ranks before this type and before
    the first that ranks after it, so [Unreleased] follows Keep a Changelog order
    regardless of the order entries are recorded.
    """
    rank = TYPES.index(ctype)
    insert_at = unreleased + 1
    while insert_at < section_end and lines[insert_at].strip() == "":
        insert_at += 1
    i = insert_at
    while i < section_end:
        if lines[i].startswith("### "):
            existing = lines[i][4:].strip().capitalize()
            if existing in TYPES and TYPES.index(existing) < rank:
                i += 1
                while i < section_end and not lines[i].startswith(("### ", "## ")):
                    i += 1
                insert_at = i
                continue
            return i
        i += 1
    return insert_at


def add(root, ctype: str, message: str) -> None:
    ctype = ctype.strip().capitalize()
    if ctype not in TYPES:
        print(f"praxis: unknown type '{ctype}'. Use one of: {', '.join(t.lower() for t in TYPES)}")
        return
    text = ensure(root)
    lines = text.splitlines()

    try:
        unreleased = next(i for i, l in enumerate(lines)
                          if l.strip().lower().startswith("## [unreleased]"))
    except StopIteration:
        # No [Unreleased] yet: place it above the latest version section, never
        # above the document title.
        unreleased = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
        lines[unreleased:unreleased] = ["## [Unreleased]", ""]

    section_end = len(lines)
    for i in range(unreleased + 1, len(lines)):
        if lines[i].startswith("## "):
            section_end = i
            break

    subsection = None
    for i in range(unreleased + 1, section_end):
        if lines[i].strip().lower() == f"### {ctype.lower()}":
            subsection = i
            break

    bullet = f"- {message}"
    if subsection is None:
        insert_at = _canonical_insert_index(lines, unreleased, section_end, ctype)
        lines[insert_at:insert_at] = [f"### {ctype}", bullet, ""]
    else:
        # Append after the subsection's last bullet so entries keep insertion order.
        last_bullet = subsection
        j = subsection + 1
        while j < section_end and not lines[j].startswith(("### ", "## ")):
            if lines[j].startswith("- "):
                last_bullet = j
            j += 1
        lines.insert(last_bullet + 1, bullet)

    p = path(root)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Name the file, not just the section: in contributor mode this is a local
    # record rather than the project's changelog, and a caller that believes it
    # updated the repo's would report the wrong thing to the user.
    print(f"praxis: {common.rel_path(root, p)} [Unreleased] › {ctype}: {message}")

    # When the record lives outside git (a project with no changelog of its own),
    # this is the only evidence that it was written for *this* change rather than
    # for some earlier one. The entry is on disk either way, so a failure here is
    # reported rather than raised: it costs the living-knowledge check its
    # evidence, and a user who is not told that cannot act on the refusal.
    if not common.record_changelog_write(root, p, ctype, message):
        print("praxis: WARNING, the entry was written but could not be recorded "
              f"in .claude/.praxis/{common.CHANGELOG_LOG}. The living-knowledge "
              "check reads that record, so it will report this change as having "
              "no changelog entry until the state directory is writable.")


def release(root, version: str) -> None:
    text = ensure(root)
    today = _dt.date.today().isoformat()
    if "## [Unreleased]" not in text:
        print("praxis: no [Unreleased] section."); return
    text = text.replace("## [Unreleased]",
                        f"## [Unreleased]\n\n## [{version}] - {today}", 1)
    p = path(root)
    p.write_text(text, encoding="utf-8")
    print(f"praxis: released {version} ({today}) in {common.rel_path(root, p)}.")


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
        ctype = "Changed"
        if "--type" in args:
            at = args.index("--type")
            if at + 1 >= len(args):
                print("praxis: --type needs a value "
                      f"({', '.join(t.lower() for t in TYPES)}).")
                return 1
            ctype = args[at + 1]
            # Drop the flag and its value by position. Filtering by equality
            # would also swallow a message word that happens to match the type,
            # turning `add --type fixed fixed the parser` into "the parser".
            rest = args[1:at] + args[at + 2:]
        else:
            rest = args[1:]
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
    # A CLI whose caller reports "changelog updated" on the strength of its exit
    # code. Failing open here would record a change that was never written, which
    # is the one lie the living-knowledge contract cannot absorb.
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"praxis: could not update the changelog: {exc}")
        sys.exit(1)
