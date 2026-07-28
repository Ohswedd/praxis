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
    debt.py paid <n> --by "..."  # mark entry n repaid, and record how

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
    """The register's text, creating it if absent. For writers only."""
    p = path(root)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        _write(p, HEADER)
    return p.read_text(encoding="utf-8")


def read(root) -> str:
    """The register's text, or "" if there is none. Creates nothing.

    `list` and `paid` used `ensure`, so merely reading the register wrote a new
    `docs/DEBT.md` into a repo that never had one: an untracked file that makes
    the tree dirty and arms the Stop gate over a file praxis itself just created.
    """
    p = path(root)
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def _write(p, text: str) -> None:
    """Atomic, like every other praxis writer: the register is the user's file."""
    tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, p)
    except Exception:
        try:
            tmp.unlink()
        except Exception:
            pass
        raise


def next_number(text: str) -> int:
    nums = [int(n) for n in ENTRY_RE.findall(text)]
    return (max(nums) + 1) if nums else 1


def add(root, args) -> int:
    title = " ".join(args[0].split())   # a newline would inject a fake heading
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
        "- Status: open",
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
    _write(p, text.rstrip("\n") + "\n" + "\n".join(entry))
    print(f"praxis: debt recorded as {common.rel_path(root, p)} entry {num}: {title}")
    return 0


def paid(root, args) -> int:
    if not args or not args[0].isdigit():
        print("usage: debt.py paid <entry number>")
        return 1
    num = int(args[0])
    text = read(root)

    # Bounded to the named entry's own block. A regex spanning `## N.` to the
    # next `- Status: open` looks right and is not: with `.*?` it backtracks past
    # an entry that is already repaid and closes the *next* open one, reporting
    # success for the number the user asked for. That silently retires a debt
    # nobody decided to retire, in a file the auditor then trusts.
    starts = [(int(m.group(1)), m.start()) for m in ENTRY_RE.finditer(text)]
    block = None
    for i, (n, at) in enumerate(starts):
        if n == num:
            end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
            block = (at, end)
            break
    if block is None:
        print(f"praxis: there is no debt entry {num}.")
        return 1

    at, end = block
    body = text[at:end]
    by = common.cli_opt(args, "--by", "")

    new_body, count = re.subn(r"(?m)^- Status: open$",
                              f"- Status: repaid {_dt.date.today().isoformat()}",
                              body, count=1)
    if not count and not by:
        print(f"praxis: debt entry {num} is not open. Pass --by \"<how it was "
              "repaid>\" to record that against it.")
        return 1

    if by:
        # An entry that says only "repaid" is a dead line: the next reader cannot
        # tell whether the principal was paid, the debt was designed away, or the
        # premise turned out to be wrong. Recording *how* is what makes the
        # register worth keeping, and it is the only place a mistaken premise
        # gets corrected without rewriting the history of what was believed.
        new_body = re.sub(r"(?m)^\*\*Repaid by\.\*\*.*$", "", new_body).rstrip("\n")
        new_body += f"\n\n**Repaid by.** {by}\n"
    _write(path(root), text[:at] + new_body + text[end:])
    print(f"praxis: debt entry {num} marked repaid."
          if count else f"praxis: recorded how entry {num} was repaid.")
    return 0


def entries(text: str) -> list:
    """(number, title, status) per entry, parsed block by block.

    Block by block rather than with one spanning regex: a single pattern from
    `## N.` to the next `- Status:` backtracks across entry boundaries, so one
    malformed entry swallows the next and that debt vanishes from the register
    the auditor reads.
    """
    starts = [(int(m.group(1)), m.start(), m.end()) for m in ENTRY_RE.finditer(text)]
    out = []
    for i, (num, at, after) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        block = text[at:end]
        title = block[after - at:].splitlines()[0].strip() if block else ""
        status = "unknown"
        for line in block.splitlines():
            if line.startswith("- Status: "):
                status = line[len("- Status: "):].strip().split()[0]
                break
        out.append((num, title, status))
    return out


def list_debt(root) -> int:
    text = read(root)
    found = entries(text)
    if not found:
        print("praxis: the debt register is empty.")
        return 0
    entries_ = [(str(n), t, s) for n, t, s in found]
    open_n = sum(1 for _, _, s in entries_ if s == "open")
    print(f"praxis: {len(entries_)} entry(ies), {open_n} open, in "
          f"{common.rel_path(root, path(root))}")
    for num, title, status in entries_:
        label = {"open": "open", "unknown": "????"}.get(status, "paid")
        print(f"  [{label}] {num}. {title}")
    return 0


def main() -> int:
    root = common.project_dir({})
    args = sys.argv[1:]
    if not args:
        print("usage: debt.py add \"<title>\" --interest \"...\" --principal \"...\" "
              "[--why ...] [--where ...] | list | paid <n> [--by \"how\"]")
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
