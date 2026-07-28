#!/usr/bin/env python3
"""
praxis placeholder / incompleteness scanner (utility).

Deterministic backstop for the rule "nothing left unfinished, no placeholders,
no silently-narrowed scope". Scans either the current change (default) or given
files for markers that signal unfinished or stubbed work.

"The current change" means the unstaged diff, the staged diff, *and* every
untracked file: a file created during the work is untracked until it is staged,
so a scanner reading only `git diff` never sees the new code at all.

Two marker classes:
  * literal markers (TODO, NotImplementedError, stub ellipsis, ...) praxis:ack
    matched everywhere;
  * deferral prose: comments that admit the code is a stand-in without using a
    literal marker ("temporary", "you can extend this", "omitted for brevity").
    This is the usual shape of unfinished work in generated code, so it carries
    the same weight. Matched only in comments, and never in prose files, where
    such wording is description rather than a postponed implementation. A line
    carrying `praxis:ack` is exempt.

Usage:
    python3 scan_placeholders.py                # scan the current change
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


# Deferred-work *language*: prose that admits the code is a stand-in, without
# using an explicit marker. This is how unfinished work usually reaches a diff: an
# apologetic comment rather than an explicit flag, so it is scanned with the
# same weight as an explicit one.
DEFERRAL_MARKERS = [
    ("deferred: temporary stand-in",
     r"(?i)\b(for\s+now|for\s+the\s+moment|for\s+the\s+time\s+being|"
     r"temporar(y|ily)|provisional|interim\s+(solution|fix|version)|"
     r"placeholder\s+(for|until|value)|stop[\s-]?gap|"
     r"until\s+(we|it|this|they)\s+(have|has|add|adds|implement|implements|support))\b"),
    ("deferred: production-grade version postponed",
     r"(?i)\b(in\s+(a|the)\s+real\s+(implementation|app|system|world|scenario|deployment)|"
     r"in\s+production(\s+(you|we|this))?\s+(would|should|you'd|we'd)|"
     r"(real|proper|production|full|complete|robust)\s+"
     r"(implementation|version|solution)\s+would|"
     r"not\s+production[\s-]?(ready|grade))\b"),
    ("deferred: self-declared prototype",
     r"(?i)\b(simplified\s+(version|for|implementation|here)|"
     r"(basic|naive|minimal|rudimentary|crude|toy|dummy|fake|mock)\s+"
     r"(implementation|version|approach|handler|client|response)\b|"
     r"(this\s+is\s+)?(just|only)\s+an?\s+(mvp|prototype|proof[\s-]of[\s-]concept|poc|sketch|"
     r"example|demo|skeleton)|"
     r"good\s+enough\s+for\s+now|first\s+(pass|cut)\s+(only|at)|"
     r"(keeping|kept|keep)\s+(it|this)\s+simple\s+for)\b"),
    ("deferred: hand-off to the reader",
     r"(?i)\b(left\s+as\s+an\s+exercise|you\s+(can|could|may|might|should|would|'ll)\s+"
     r"(want\s+to\s+)?(extend|add|implement|expand|improve|replace|customi[sz]e|swap|wire)|"
     r"(feel\s+free\s+to|consider)\s+(extending|adding|implementing|replacing)|"
     r"extend\s+this\s+as\s+needed|adapt\s+(this|as)\s+(to|needed)|"
     r"replace\s+(this|with)\s+(with\s+)?(your|a\s+real|an?\s+actual))\b"),
    ("deferred: acknowledged gap",
     r"(?i)\b(not\s+(yet\s+)?(implemented|handled|supported|covered|wired|hooked)|"
     r"doesn'?t\s+(yet\s+)?(handle|support|cover|validate)|"
     r"(no|without|missing)\s+(error\s+handling|validation|retry|auth)|"
     r"skipping\s+(validation|error\s+handling|the)|"
     r"(omitted|elided|stubbed|abbreviated|truncated)\s+for\s+brevity|"
     r"a\s+full\s+implementation\s+would|"
     r"(out\s+of\s+scope|beyond\s+the\s+scope)\s+(for|of)\s+(this|now)|"
     r"(future|later)\s+(work|iteration|pr|commit)\s+(will|can|should)|"
     # Both the contracted and the spelled-out subject form, which defer
     # identically. The alternation is written out rather than made optional so
     # that the word "well" cannot open a false match.
     r"(we|i)\s?(?:'ll|will)\s+(add|handle|implement|fix)\s+(this|that|it)\s+"
     r"(later|next))\b"),
]

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
_COMPILED_DEFERRAL = [(label, re.compile(pat, re.MULTILINE)) for label, pat in DEFERRAL_MARKERS]

# Deferral prose is matched only inside comments/docstrings. Natural-language
# admissions live in comments; matching them in ordinary strings would flag every
# piece of code that merely *mentions* the phrase (error copy, UI text, this
# scanner's own patterns) and make the signal useless.
_COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*|<!--|--|;|\"\"\"|''')|(?<=\s)(#|//)\s")

# Prose files document behaviour; deferral wording there is description, not a
# postponed implementation. Literal markers still apply to them.
_PROSE_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}

def scan_text_lines(pairs) -> list:
    findings = []
    for fname, lineno, text in pairs:
        if common.is_acked(text):
            continue
        for label, rx in _COMPILED:
            if rx.search(text):
                findings.append({"file": fname, "line": lineno,
                                 "marker": label, "text": text.strip()[:160]})
        if _deferral_applies(fname, text):
            for label, rx in _COMPILED_DEFERRAL:
                if rx.search(text):
                    findings.append({"file": fname, "line": lineno,
                                     "marker": label, "text": text.strip()[:160]})
    return findings


def _deferral_applies(fname, text: str) -> bool:
    """True if deferral prose in `text` should be treated as a finding."""
    if fname and Path(fname).suffix.lower() in _PROSE_SUFFIXES:
        return False
    return bool(_COMMENT_RE.search(text))


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
        findings = scan_text_lines(common.added_line_pairs(root))

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
