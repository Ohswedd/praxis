#!/usr/bin/env python3
"""
praxis drift detector (utility invoked by /praxis:doctor and the SessionStart audit).

Documentation rots in a specific, predictable way: it states as a constant
something that is actually configuration or code, and then the configuration or
the code moves. The two shapes praxis sees most often are

  * **config drift**: CLAUDE.md or a doc asserts behaviour that the repo's live
    settings contradict. The canonical case: the docs say praxis opens a pull
    request and leaves the merge to a human, long after the repo turned
    `auto_merge` on. Every session then reads the wrong policy and states it back
    to the user with total confidence.
  * **reference drift**: a documented command, file, or slash command no longer
    exists. A build command that was renamed, a module that moved, a
    `/praxis:scan` that was folded into `/praxis:audit`.

Both are detected mechanically here, against the live repo, so they surface
without anyone remembering to look. Findings are advisory: this reports, it never
edits. `docs-living` and `claudemd-living` do the fixing.

Usage:
    python3 drift.py             # human-readable report
    python3 drift.py --json      # machine-readable

Exit code: 0 if no drift, 1 if any finding, so it can gate a docs check in CI.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Files whose statements are read as authoritative by a session: the root
# instructions, the docs tree, and every nested CLAUDE.md. Anything deeper is
# project prose, which is free to say what it likes.
DOC_GLOBS = ("CLAUDE.md", "CLAUDE.local.md", "README.md", "docs/*.md")

MAX_DOCS = 60


def doc_files(root: Path) -> list:
    """The instruction-carrying documents, deduplicated and repo-relative.

    Nested CLAUDE.md files are found with the pruning walk rather than
    `glob("**/CLAUDE.md")`, which descends node_modules, .venv and build output
    and materialises the whole tree before yielding anything. This runs inside
    the SessionStart budget, so the walk has to be bounded.
    """
    seen, out = set(), []

    def take(p: Path) -> bool:
        """Record `p`; False once the cap is reached."""
        try:
            rel = str(p.relative_to(root))
        except ValueError:
            return True
        if rel in seen or not p.is_file() or not common.is_scannable(root, rel):
            return True
        seen.add(rel)
        out.append(rel)
        return len(out) < MAX_DOCS

    for pattern in DOC_GLOBS:
        try:
            matches = sorted(root.glob(pattern))
        except Exception:
            continue
        for p in matches:
            if not take(p):
                return out
    for p in common.find_files(root, "CLAUDE.md", limit=MAX_DOCS):
        if not take(p):
            break
    return out


# --------------------------------------------------------------------------- #
# Config drift
# --------------------------------------------------------------------------- #
# (setting, live-value reader, claim-when-true regex, claim-when-false regex)
#
# Each pair says: "if the setting is X, a document asserting the opposite of X is
# drift." Patterns are written to match the *assertion*, not a mention: a doc is
# free to describe both states ("with auto-merge on, praxis merges") as long as it
# does not declare the one that is not in force.
_ASSERTION_RULES = [
    (
        "git.auto_merge",
        lambda root: common.auto_merge_on(root),
        # Asserted while auto-merge is OFF: claims praxis merges by itself.
        re.compile(r"(?i)\bpraxis\s+(merges|will\s+merge)\b"
                   r"|\bmerges?\s+(its\s+own|the)\s+PRs?\s+automatically\b"
                   r"|\bauto[\s_-]?merge\s+is\s+(on|enabled)\b"),
        # Asserted while auto-merge is ON: claims praxis never merges.
        re.compile(r"(?i)(never|does\s+not|doesn'?t|will\s+not|won'?t)\s+merges?\b"
                   r"|\bhuman\s+merges\b|\bleaves?\s+the\s+merge\s+to\s+(you|a\s+human)"
                   r"|\bstops?\s+(after|at)\s+(opening\s+)?the\s+PR\b"
                   r"|\bauto[\s_-]?merge\s+is\s+(off|disabled)\b"),
        "delivery policy",
    ),
    (
        "autopilot",
        lambda root: common.autopilot_on(root),
        re.compile(r"(?i)auto[\s-]?pilot\s+is\s+(on|enabled)\b"),
        re.compile(r"(?i)auto[\s-]?pilot\s+is\s+(off|disabled)\b"),
        "auto-pilot state",
    ),
    (
        "gate.enabled",
        # The value in force, not just the config layer: a doc saying "the gate is
        # off" is correct when PRAXIS_GATE=off, and flagging it would be the
        # checker itself going stale.
        lambda root: common.gate_enabled(root),
        # Asserted while the gate is OFF: claims it is on.
        re.compile(r"(?i)the\s+(quality\s+|stop\s+)?gate\s+is\s+(on|enabled|active)\b"),
        # Asserted while the gate is ON: claims it is off. These two were the
        # wrong way round, which made the rule a pure false-positive generator
        # (it flagged a doc for correctly saying the gate is on) that could never
        # catch the drift it exists for.
        re.compile(r"(?i)the\s+(quality\s+|stop\s+)?gate\s+is\s+(off|disabled)\b"),
        "quality gate",
    ),
]


# Connectives that make a clause conditional rather than declarative. A doc is
# supposed to explain both states of a toggle ("off by default: praxis stops at
# the PR"); only an unqualified claim about the state currently in force is
# drift. Without this exemption the checker fires on correct documentation and
# becomes noise, which is precisely how a drift report gets ignored.
_QUALIFIED_RE = re.compile(
    r"(?i)\b(unless|if|when|whenever|by\s+default|defaults?\s+to|the\s+default|"
    r"opt(ing|ed)?[\s-]?in|off\s*[:(]|on\s*[:(]|toggle)\b"
    r"|PRAXIS_[A-Z_]+|\[(git|gate|autopilot|style|audit)\]|"
    r"(git|gate|autopilot|style)\.[a-z_]+")

# How far around a match to look for a qualifier. Prose wraps, so the "unless you
# opt in" that qualifies a claim is routinely on the next line.
_QUALIFIER_WINDOW = 1


def config_drift(root: Path, docs: list) -> list:
    """Documents asserting the opposite of a live setting."""
    findings = []
    for setting, live_of, claims_when_false, claims_when_true, label in _ASSERTION_RULES:
        try:
            live = bool(live_of(root))
        except Exception:
            continue
        contradiction = claims_when_true if live else claims_when_false
        for rel in docs:
            lines = _lines(root, rel)
            for index, (lineno, line) in enumerate(lines):
                if common.is_acked(line) or not contradiction.search(line):
                    continue
                if _qualified_near(lines, index):
                    continue
                findings.append({
                    "kind": "config",
                    "setting": setting,
                    "file": rel,
                    "line": lineno,
                    "live": "on" if live else "off",
                    "text": line.strip()[:160],
                    "detail": (f"{label}: the repo has {setting}="
                               f"{'on' if live else 'off'}, this line states the "
                               "opposite as a fact"),
                })
    return findings


def _qualified_near(lines: list, index: int) -> bool:
    lo = max(0, index - _QUALIFIER_WINDOW)
    hi = min(len(lines), index + _QUALIFIER_WINDOW + 1)
    return any(_QUALIFIED_RE.search(text) for _, text in lines[lo:hi])


def _lines(root: Path, rel: str):
    """Every line of a document, ack'd lines included.

    The ack is applied where a finding would be raised, not here: dropping lines
    would shift the qualifier window and unbalance fenced-block tracking.
    """
    try:
        body = (root / rel).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return list(enumerate(body.splitlines(), 1))


# --------------------------------------------------------------------------- #
# Reference drift
# --------------------------------------------------------------------------- #
_NPM_SCRIPT_RE = re.compile(r"\b(?:npm|pnpm|yarn|bun)\s+run\s+([A-Za-z0-9:_-]+)")
_MAKE_TARGET_RE = re.compile(r"\bmake\s+([A-Za-z0-9_-]+)")
_SLASH_CMD_RE = re.compile(r"/praxis:([a-z0-9-]+)")

# A markdown link target. Only links are checked for existence: a backticked path
# is often illustrative ("write `docs/design/BRIEF.md` in the target repo"),
# whereas a link is a navigational promise, so a broken one is unambiguous drift
# and the check stays free of the false positives that make a report ignorable.
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

# Inline code spans and fenced blocks: the only places a command is a command
# rather than a sentence containing the word "make".
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _npm_scripts(root: Path) -> set:
    try:
        pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
        return set(pkg.get("scripts", {}))
    except Exception:
        return set()


def _make_targets(root: Path) -> set:
    try:
        body = (root / "Makefile").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()
    return set(re.findall(r"^([A-Za-z0-9_-]+):", body, re.MULTILINE))


def _praxis_commands() -> set:
    try:
        return {p.stem for p in (PLUGIN_ROOT / "commands").glob("*.md")}
    except Exception:
        return set()


def reference_drift(root: Path, docs: list) -> list:
    """Documented commands, slash commands, and links that no longer resolve."""
    findings = []
    has_pkg = (root / "package.json").exists()
    has_make = (root / "Makefile").exists()
    npm, make = _npm_scripts(root), _make_targets(root)
    commands = _praxis_commands()

    for rel in docs:
        for lineno, line, code in _code_aware_lines(root, rel):
            if common.is_acked(line):
                continue
            if has_pkg:
                for script in _NPM_SCRIPT_RE.findall(code):
                    if script not in npm:
                        findings.append(_ref(rel, lineno, line, "npm script",
                                             f"`npm run {script}` is documented but "
                                             "package.json has no such script"))
            if has_make:
                for target in _MAKE_TARGET_RE.findall(code):
                    if target not in make:
                        findings.append(_ref(rel, lineno, line, "make target",
                                             f"`make {target}` is documented but the "
                                             "Makefile has no such target"))
            # Only meaningful inside praxis's own repo, where the command files live.
            if commands:
                for cmd in _SLASH_CMD_RE.findall(line):
                    if cmd not in commands:
                        findings.append(_ref(rel, lineno, line, "slash command",
                                             f"`/praxis:{cmd}` no longer exists"))
            for target in _LINK_RE.findall(line):
                if _broken_link(root, rel, target):
                    findings.append(_ref(rel, lineno, line, "link",
                                         f"`{target}` does not resolve from {rel}"))
    return findings


def _ref(rel, lineno, line, kind, detail) -> dict:
    return {"kind": "reference", "subkind": kind, "file": rel, "line": lineno,
            "text": line.strip()[:160], "detail": detail}


def _code_aware_lines(root: Path, rel: str):
    """(lineno, full line, the code part of that line) for one document.

    The code part is the fenced-block body or the inline code spans, so a
    sentence like "make design decisions auditable" is never read as an
    invocation of a `design` make target.
    """
    out = []
    in_fence = False
    for lineno, line in _lines(root, rel):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append((lineno, line, ""))
            continue
        code = line if in_fence else " ".join(_CODE_SPAN_RE.findall(line))
        out.append((lineno, line, code))
    return out


def _broken_link(root: Path, rel: str, target: str) -> bool:
    """True for a relative link that resolves to nothing on disk."""
    target = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not target or "://" in target or target.startswith(("#", "mailto:", "/")):
        return False
    if any(ch in target for ch in "<>*"):
        return False   # a placeholder like docs/<name>.md
    base = (root / rel).parent
    return not (base / target).exists()


def collect(root: Path):
    """(findings, truncated) for one repo.

    The truncation flag is returned rather than swallowed: a checker that quietly
    stops at a cap and still prints "none" is claiming coverage it did not have,
    which is the exact failure this whole module exists to prevent.
    """
    docs = doc_files(root)
    findings = config_drift(root, docs) + reference_drift(root, docs)
    return findings, len(docs) >= MAX_DOCS


def render(findings: list, truncated: bool = False) -> str:
    note = (f"\n(Only the first {MAX_DOCS} instruction documents were checked; "
            "there may be more.)" if truncated else "")
    if not findings:
        return ("praxis drift: none, the docs match the live configuration and code."
                + note)
    lines = [f"praxis drift: {len(findings)} finding(s)." + note]
    for f in findings:
        lines.append(f"  - {f['file']}:{f['line']}  [{f['kind']}] {f['detail']}")
        lines.append(f"      {f['text']}")
    lines.append("Fix with the `docs-living` / `claudemd-living` skills "
                 "(`/praxis:docs`), not by hand-editing around the symptom.")
    return "\n".join(lines)


def main() -> int:
    root = common.project_dir({})
    findings, truncated = collect(root)
    if "--json" in sys.argv[1:]:
        print(json.dumps({"count": len(findings), "findings": findings,
                          "truncated": truncated}, indent=2))
    else:
        print(render(findings, truncated))
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open: drift reporting must never break a session or a CI job.
        sys.exit(0)
