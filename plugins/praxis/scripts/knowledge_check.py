#!/usr/bin/env python3
"""
praxis living-knowledge check (change-scoped).

"Documentation is part of done" was, until now, prose. praxis stated it in the
output style, the task orchestrator and the docs-living skill, and nothing
measured it, so the one part of a change that nobody notices missing is exactly
the part that went missing: the behaviour shipped, the docs stayed as they were,
and the next session read a description of a system that no longer exists.

This is the deterministic half. It answers three questions about the current
change, and only about the current change, so a repo's pre-existing doc debt is
never charged to the person who touched one file today:

  1. **Did the changelog move with the behaviour?** A change that alters
     behaviour and skips the project's `CHANGELOG.md` loses the record of what
     happened at the moment it is cheapest to write.
  2. **Did any documentation move with it?** Not which document and not how
     much: the check is that a behaviour change touched the knowledge tree at
     all, because the common failure is that it touched none of it.
  3. **Did this change take documentation away?** A section deleted from a
     shrinking document is the one doc regression that reading a diff of added
     lines cannot see, and it is how a still-valid instruction quietly stops
     existing.

Mode-aware throughout. In `contributor` mode the rule is join what exists,
create nothing new, so a project without a `/docs` is never asked for one, and
the changelog looked at is whichever `changelog.py` would actually write.

Usage:
    python3 knowledge_check.py            # human-readable report
    python3 knowledge_check.py --json     # machine-readable

Exit code: 0 if clean, 1 if any finding, so it can gate. `report.py` runs it
itself and records the result as evidence, which is why a green quality report
can no longer be recorded over a change that dropped its documentation.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

#: Prose suffixes. A change to one of these documents the system; a change to
#: anything else is the system.
PROSE_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}

#: Files that carry no behaviour worth a changelog line. Everything not listed
#: here counts, including configuration and CI, because a change to how the
#: project builds or deploys is exactly the kind of thing readers need recorded.
HOUSEKEEPING = {
    ".gitignore", ".gitattributes", ".editorconfig", ".dockerignore",
    ".npmignore", ".prettierignore", ".eslintignore", "CODEOWNERS", "LICENSE",
    "LICENSE.txt", "LICENSE.md", "NOTICE", ".DS_Store",
}

#: Test paths. A change confined to tests documents itself, and demanding a
#: changelog entry for adding a test case is the kind of noise that gets a whole
#: check switched off.
TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|spec|specs|__tests__|__mocks__|e2e|testdata|fixtures)(/|$)"
    r"|(^|/)(test_[^/]+|[^/]+_test)\.[A-Za-z0-9]+$"
    r"|\.(test|spec)\.[A-Za-z0-9]+$",
    re.IGNORECASE,
)

#: An ATX markdown heading. Setext underlining is not matched on purpose: `---`
#: under a line is indistinguishable from a horizontal rule in a diff of removed
#: lines, and a check that guesses is worse than one that admits its scope.
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")

#: Per-file cap on reported missing headings. A wholesale rewrite would otherwise
#: print a hundred lines that all say the same thing.
MAX_HEADINGS_PER_FILE = 8

#: Ceiling on the prose read back to check whether a heading merely moved.
MAX_CORPUS_BYTES = 4_000_000


def is_prose(rel: str) -> bool:
    return Path(rel).suffix.lower() in PROSE_SUFFIXES


def is_behaviour_file(rel: str) -> bool:
    """True when changing `rel` changes what the project does."""
    name = Path(rel).name
    if name in HOUSEKEEPING or is_prose(rel):
        return False
    if TEST_PATH_RE.search(rel):
        return False
    return common.is_diff_scannable(rel)


def doc_surfaces(root: Path, rel: str) -> bool:
    """True when `rel` is part of this project's knowledge tree.

    The brief counts: `CLAUDE.md` is the document a session actually reads, and a
    change that updates it has updated the knowledge that matters most.
    """
    norm = rel.replace("\\", "/")
    if norm.startswith("docs/"):
        return True
    name = Path(norm).name
    if name in ("CLAUDE.md", "CLAUDE.local.md"):
        return True
    return is_prose(norm) and "/" not in norm and name != "CHANGELOG.md"


def unreleased_is_empty(text: str) -> bool:
    """True when the changelog has no entry under [Unreleased]."""
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.strip().lower().startswith("## [unreleased]"))
    except StopIteration:
        return True
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.strip().startswith(("- ", "* ")):
            return False
    return True


def check_changelog(root: Path, behaviour: list) -> list:
    """Whether this change recorded itself where `changelog.py` would write."""
    if not behaviour:
        return []
    target = common.knowledge_path(root, "CHANGELOG.md")
    rel = common.repo_relative(root, target)

    # Under the repo: the file is tracked, so "was it part of this change" is a
    # question git can answer exactly.
    if rel and not common.is_praxis_state(rel):
        if rel in common.changed_files(root):
            return []
        return [{
            "kind": "changelog",
            "file": rel,
            "line": 0,
            "detail": (f"{len(behaviour)} behaviour-bearing file(s) changed and "
                       f"{rel} was not touched. Record it: changelog.py add "
                       "--type <added|changed|fixed|removed|security|deprecated> "
                       "\"<what changed>\"."),
        }]

    # Local knowledge (contributor mode, project without a changelog). The file
    # is git-excluded, so no diff can see it and the strongest available evidence
    # is that praxis wrote an entry into it at all. Stated rather than dressed up:
    # this proves the record exists, not that it describes today's work.
    try:
        text = target.read_text(encoding="utf-8") if target.exists() else ""
    except Exception:
        text = ""
    if text and not unreleased_is_empty(text):
        return []
    return [{
        "kind": "changelog",
        "file": common.rel_path(root, target),
        "line": 0,
        "detail": ("this repository has no CHANGELOG.md of its own, so praxis "
                   "keeps the record locally, and that record has no "
                   "[Unreleased] entry. Add one: changelog.py add --type "
                   "<type> \"<what changed>\"."),
    }]


def check_docs_touched(root: Path, behaviour: list, changed: list) -> list:
    """Whether a behaviour change moved any documentation at all."""
    if not behaviour:
        return []
    if any(doc_surfaces(root, f) for f in changed):
        return []
    # Join what exists: a project we only contribute to, with no docs tree of its
    # own, is not asked to grow one for a bug fix.
    if common.is_contributor(root) and not (root / "docs").is_dir():
        return []
    return [{
        "kind": "docs",
        "file": "docs/",
        "line": 0,
        "detail": (f"{len(behaviour)} behaviour-bearing file(s) changed "
                   f"(e.g. {', '.join(behaviour[:3])}) and no document moved "
                   "with them. Read the docs covering this area first, then "
                   "update what this change made untrue."),
    }]


def _corpus(root: Path, changed: list) -> str:
    """The current text of every prose file in the change, concatenated.

    Read back so a heading that *moved* is not reported as a heading that was
    lost: a renamed document, a section promoted into its own file, and a
    paragraph relocated between two docs are all ordinary edits, and a check that
    called them regressions would be ignored within a week.
    """
    budget = MAX_CORPUS_BYTES
    parts = []
    for rel in changed:
        if not is_prose(rel) or budget <= 0:
            continue
        try:
            body = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        budget -= len(body)
        parts.append(body)
    return "\n".join(parts).lower()


def check_doc_regression(root: Path, changed: list) -> list:
    """Documentation this change removed: whole files, and lost sections."""
    findings = []
    removed = common.removed_lines(root)
    counts = common.changed_line_counts(root)
    corpus = _corpus(root, changed)

    for rel in sorted(removed):
        if not is_prose(rel):
            continue
        added, gone = counts.get(rel, (0, 0))
        exists = (root / rel).exists()
        if exists and gone <= added:
            # The document grew or held its size: an edit, not a removal.
            continue
        if not exists:
            findings.append({
                "kind": "doc-regression",
                "file": rel,
                "line": 0,
                "detail": (f"this document was deleted ({gone} line(s)). If it is "
                           "genuinely obsolete, say so; if its content moved, "
                           "make sure all of it arrived somewhere."),
            })
            continue
        lost = []
        for line in removed[rel]:
            m = HEADING_RE.match(line)
            if not m:
                continue
            title = m.group(2).strip()
            if title and title.lower() not in corpus:
                lost.append(title)
        for title in lost[:MAX_HEADINGS_PER_FILE]:
            findings.append({
                "kind": "doc-regression",
                "file": rel,
                "line": 0,
                "detail": (f"the section \"{title}\" was removed and appears "
                           f"nowhere else in this change, while {rel} shrank by "
                           f"{gone - added} line(s). Restore it, or state why it "
                           "is obsolete."),
            })
        if len(lost) > MAX_HEADINGS_PER_FILE:
            findings.append({
                "kind": "doc-regression",
                "file": rel,
                "line": 0,
                "detail": (f"... and {len(lost) - MAX_HEADINGS_PER_FILE} further "
                           "section(s) removed from this document."),
            })
    return findings


def collect(root: Path) -> list:
    if not common.is_git_repo(root):
        return []
    changed = common.changed_files(root)
    behaviour = [f for f in changed if is_behaviour_file(f)]
    return (check_changelog(root, behaviour)
            + check_docs_touched(root, behaviour, changed)
            + check_doc_regression(root, changed))


def main() -> int:
    args = sys.argv[1:]
    root = common.project_dir({})
    findings = collect(root)

    if "--json" in args:
        print(json.dumps({"count": len(findings), "findings": findings}, indent=2))
    elif not findings:
        print("praxis: living knowledge is current for this change "
              "(changelog recorded, docs moved with the behaviour, nothing lost).")
    else:
        print(f"praxis: {len(findings)} living-knowledge finding(s):")
        for f in findings:
            print(f"  - [{f['kind']}] {f['file']}  {f['detail']}")
        print("Fix these as part of this change (the `docs-living` skill covers "
              "all three). If one is genuinely not applicable, record the reason "
              "with `report.py record --knowledge-ack \"<why>\"`, which keeps it "
              "in the report instead of losing it.")
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # A scanner, like its siblings: a crash must never wedge a session. It
        # still says so, because a silent 0 here reads as "knowledge is current".
        print(f"praxis: the living-knowledge check could not run: {exc}")
        sys.exit(0)
