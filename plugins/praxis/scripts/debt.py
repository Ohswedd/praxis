#!/usr/bin/env python3
"""
praxis technical-debt register (operates on the *target project's* docs/DEBT.md).

Debt is not a synonym for bad code. A shortcut taken for a stated reason and
written down is a legitimate engineering decision; the same shortcut taken
silently is the defect, because the next person meets the consequence without
the reason. This register is where the reason lives, so "we knew" is a record
rather than a claim.

Each entry carries the two numbers that make debt comparable: the **interest**
(what it costs, and how often) and the **principal** (what the real fix is). A
register that only lists what is wrong is a wish-list; one that says what each
item costs can be ranked.

Usage:
    debt.py add "Orders are re-fetched on every render" \\
        --interest "~200ms per interaction, and one support ticket a week" \\
        --principal "Cache in the query layer; needs the key refactor first" \\
        --why "The release was date-bound and the refactor is two days" \\
        --where "src/orders/list.tsx"
    debt.py list                # the register, newest first
    debt.py paid <n>            # mark entry n repaid, with the date

Entries live in docs/DEBT.md, or under .claude/.praxis/knowledge/ when the
repository is not ours (contributor mode), like every other knowledge artifact.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

REL = "docs/DEBT.md"

HEADER = """# Technical debt register

What this project has knowingly borrowed, what it costs, and what repaying it
would take. Recorded debt is a decision; unrecorded debt is a surprise.

Each entry is written when the debt is taken on, not discovered later. praxis's
`debt-auditor` reads this file during review: debt that is listed here is a
decision it will not re-report, and debt it finds that is *not* here is a finding.

Add with `debt.py add`, close with `debt.py paid <n>`.
"""

ENTRY_RE = re.compile(r"^## (\d+)\. ", re.MULTILINE)


def path(root):
    return common.knowledge_path(root, REL)


def ensure(root) -> str:
    p = path(root)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HEADER, encoding="utf-8")
    return p.read_text(encoding="utf-8")


def next_number(text: str) -> int:
    nums = [int(n) for n in ENTRY_RE.findall(text)]
    return (max(nums) + 1) if nums else 1


def add(root, args) -> int:
    title = args[0]
    if title.startswith("-"):
        print("praxis: the title comes first, before the flags: "
              "debt.py add \"<title>\" [--interest ...] [--principal ...]")
        return 1
    interest = common.cli_opt(args, "--interest", "")
    principal = common.cli_opt(args, "--principal", "")
    why = common.cli_opt(args, "--why", "")
    where = common.cli_opt(args, "--where", "")

    # Interest and principal are what make the entry rankable and actionable. An
    # entry without them is a complaint, and a register of complaints is ignored.
    missing = [n for n, v in (("--interest", interest), ("--principal", principal))
               if not v]
    if missing:
        print(f"praxis: {' and '.join(missing)} required. Debt that does not say "
              "what it costs and what would fix it cannot be prioritised against "
              "anything else, so the register fills up and stops being read.")
        return 1

    text = ensure(root)
    num = next_number(text)
    entry = [
        f"\n## {num}. {title}\n",
        f"- Recorded: {_dt.date.today().isoformat()}",
        f"- Status: open",
    ]
    if where:
        entry.append(f"- Where: {where}")
    entry += [
        "",
        f"**Interest.** {interest}",
        "",
        f"**Principal.** {principal}",
    ]
    if why:
        entry += ["", f"**Why it was taken on.** {why}"]
    entry.append("")

    p = path(root)
    p.write_text(text.rstrip("\n") + "\n" + "\n".join(entry), encoding="utf-8")
    print(f"praxis: debt recorded as {_rel(root, p)} entry {num}: {title}")
    return 0


def paid(root, args) -> int:
    if not args or not args[0].isdigit():
        print("usage: debt.py paid <entry number>")
        return 1
    num = int(args[0])
    text = ensure(root)
    pattern = re.compile(rf"(^## {num}\. .*?^- Status: )open", re.MULTILINE | re.DOTALL)
    new, count = pattern.subn(rf"\1repaid {_dt.date.today().isoformat()}", text)
    if not count:
        print(f"praxis: no open debt entry {num}.")
        return 1
    path(root).write_text(new, encoding="utf-8")
    print(f"praxis: debt entry {num} marked repaid.")
    return 0


def list_debt(root) -> int:
    text = ensure(root)
    entries = re.findall(r"^## (\d+)\. (.+?)$.*?^- Status: (\S+)",
                         text, re.MULTILINE | re.DOTALL)
    if not entries:
        print("praxis: the debt register is empty.")
        return 0
    open_n = sum(1 for _, _, s in entries if s == "open")
    print(f"praxis: {len(entries)} entry(ies), {open_n} open, in "
          f"{_rel(root, path(root))}")
    for num, title, status in entries:
        print(f"  [{'open' if status == 'open' else 'paid'}] {num}. {title}")
    return 0


def _rel(root, p) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def main() -> int:
    root = common.project_dir({})
    args = sys.argv[1:]
    if not args:
        print("usage: debt.py add \"<title>\" --interest \"...\" --principal \"...\" "
              "[--why ...] [--where ...] | list | paid <n>")
        return 1
    if args[0] == "add":
        if len(args) < 2:
            print("usage: debt.py add \"<title>\" --interest \"...\" --principal \"...\"")
            return 1
        return add(root, args[1:])
    if args[0] == "list":
        return list_debt(root)
    if args[0] == "paid":
        return paid(root, args[1:])
    print(f"praxis: unknown command '{args[0]}'")
    return 1


if __name__ == "__main__":
    # Like the other knowledge CLIs: a caller reports "debt recorded" from this
    # exit code, and a silent success would record nothing while claiming it did.
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"praxis: could not update the debt register: {exc}")
        sys.exit(1)
