#!/usr/bin/env python3
"""
praxis review scope: what is actually under review, and how to diff it.

Every auditor needs the same answer to one question, and getting it wrong is
silent. `git diff` on a branch that has committed anything is empty, so a review
scoped that way reads nothing, finds nothing, and reports PASS. The better the
delivery discipline (one commit per subtask), the more complete that blindness
becomes.

So the scope is the branch: every commit since it left its base, plus whatever is
still uncommitted, plus untracked files that appear in no diff at all. This prints
that scope and the exact commands to inspect it, so the rubric and each subagent
work from the same base rather than each guessing.

Usage:
    scope.py             # human-readable
    scope.py --json      # machine-readable
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

#: Files listed inline before the rest is summarised as a count.
PREVIEW = 40


def collect(root) -> dict:
    base = common.review_base(root)
    committed = common.committed_files(root)
    working = sorted(set(common.changed_files(root)) - set(committed))
    return {
        "is_git_repo": common.is_git_repo(root),
        "branch": common.current_branch(root),
        "default_branch": common.git_default_branch(root) if common.is_git_repo(root) else "",
        "base": base or "",
        "commits": common.branch_commits(root),
        "committed_files": committed,
        "working_files": working,
        "files": common.changed_files(root),
        "ui_files": common.ui_files_in_change(root),
        "review_pending": common.review_pending(root),
        "signature": common.change_signature(root) if common.is_git_repo(root) else "",
    }


def render(scope: dict) -> str:
    if not scope["is_git_repo"]:
        return ("praxis scope: not a git repository. The change is whatever is on "
                "disk; there is no base to diff against.")
    if not scope["review_pending"]:
        return (f"praxis scope: nothing to review on `{scope['branch']}`. No commits "
                "since the base, and the working tree is clean.")

    lines = [f"## praxis review scope  (branch `{scope['branch']}`)", ""]
    if scope["base"]:
        lines.append(f"**Base:** `{scope['base'][:12]}` "
                     f"(merge-base with `{scope['default_branch']}`)")
        lines.append(f"**Commits on this branch:** {len(scope['commits'])}")
        for c in scope["commits"][:PREVIEW]:
            lines.append(f"  - {c}")
        if len(scope["commits"]) > PREVIEW:
            lines.append(f"  - ... and {len(scope['commits']) - PREVIEW} more")
    else:
        lines.append(f"**Base:** none. This is `{scope['default_branch']}` itself, or "
                     "the branch has committed nothing yet, so the review scope is "
                     "the working tree alone.")
    lines.append("")

    lines.append(f"**Files under review: {len(scope['files'])}** "
                 f"({len(scope['committed_files'])} committed, "
                 f"{len(scope['working_files'])} uncommitted)")
    for f in scope["files"][:PREVIEW]:
        where = "committed" if f in scope["committed_files"] else "working tree"
        lines.append(f"  - {f}  ({where})")
    if len(scope["files"]) > PREVIEW:
        lines.append(f"  - ... and {len(scope['files']) - PREVIEW} more")
    if scope["ui_files"]:
        lines.append(f"  → {len(scope['ui_files'])} of these are user-facing surface, "
                     "so the accessibility and design-consistency verticals apply.")
    lines.append("")

    lines.append("**Diff it with:**")
    if scope["base"]:
        lines.append(f"```bash\ngit diff {scope['base'][:12]}...HEAD      "
                     "# what this branch has committed\n"
                     f"git log --stat {scope['base'][:12]}..HEAD  "
                     "# commit by commit, in the order it happened\n"
                     "git diff                        # not yet staged\n"
                     "git diff --staged               # staged\n```")
        lines.append("Reviewing commit by commit shows the *order* the work was done "
                     "in, which is where a fix-up of a bug this same branch "
                     "introduced, or an accidental revert, becomes visible.")
    else:
        lines.append("```bash\ngit diff\ngit diff --staged\n```")
    lines.append("")
    lines.append("Untracked files are part of the change and appear in no diff: read "
                 "them directly. `git diff` alone is never the scope.")
    return "\n".join(lines)


def main() -> int:
    root = common.project_dir({})
    scope = collect(root)
    if "--json" in sys.argv[1:]:
        print(json.dumps(scope, indent=2))
    else:
        print(render(scope))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Read-only reporting: never break a review because the scope printer
        # tripped, but say so rather than printing an empty scope that would be
        # read as "nothing changed".
        print(f"praxis: could not resolve the review scope: {exc}")
        sys.exit(1)
