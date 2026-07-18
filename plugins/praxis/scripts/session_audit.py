#!/usr/bin/env python3
"""
praxis SessionStart audit.

Runs when a session opens (and again on resume). Whatever it prints to stdout
is injected into Claude's context, so this is where praxis orients the model:

  * classifies the repo state (new / un-initialised / legacy CLAUDE.md / managed)
  * surfaces a concise health report (secrets, missing setup, drift, TODOs)
  * points Claude at the right entry command

It is intentionally read-only, fast, and offline-safe. It never blocks.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

PRAXIS_MARK = "<!-- praxis:managed -->"


def classify(root: Path) -> str:
    claude_md = root / "CLAUDE.md"
    settings = root / ".claude" / "settings.json"
    has_code = _has_source(root)

    if not has_code and not (root / ".git").exists():
        return "new"
    if not claude_md.exists() and not settings.exists():
        return "uninitialised"
    if claude_md.exists():
        try:
            body = claude_md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            body = ""
        if PRAXIS_MARK in body:
            return "managed"
        return "legacy"
    return "partial"


def _has_source(root: Path) -> bool:
    markers = [
        "package.json", "pyproject.toml", "setup.py", "requirements.txt",
        "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile",
        "composer.json", "mix.exs", "pubspec.yaml", "CMakeLists.txt",
        "Makefile", "*.sln",
    ]
    for m in markers:
        if "*" in m:
            if any(root.glob(m)):
                return True
        elif (root / m).exists():
            return True
    return False


def quick_secret_scan(root: Path, cap: int = 400) -> list:
    hits = []
    files = common.tracked_files(root, limit=cap) or []
    if not files:
        # not a git repo yet — scan shallow with a pruning walk (skips node_modules etc.)
        import os as _os
        visited = 0
        for dirpath, dirnames, filenames in _os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in common.PRUNE_DIRS and not d.startswith(".praxis")]
            for fn in filenames:
                files.append(str((Path(dirpath) / fn).relative_to(root)))
                if len(files) >= cap:
                    break
            visited += 1
            if len(files) >= cap or visited > 5000:
                break
    for rel in files:
        fp = root / rel
        if common.is_sensitive_path(rel) and _is_tracked_or_present(fp):
            hits.append(f"sensitive file present: {rel}")
        found = common.scan_file_for_secrets(fp) if fp.suffix not in (".lock",) else []
        for f in found:
            hits.append(f"{f} in {rel}")
        if len(hits) >= 12:
            hits.append("... (more findings suppressed)")
            break
    return hits


def _is_tracked_or_present(fp: Path) -> bool:
    try:
        return fp.exists()
    except Exception:
        return False


def nested_claude_md(root: Path) -> list:
    out = []
    try:
        for p in common.find_files(root, "CLAUDE.md", limit=15):
            if p == root / "CLAUDE.md":
                continue
            out.append(str(p.relative_to(root)))
    except Exception:
        pass
    return out


def build_report(root: Path) -> str:
    state = classify(root)
    lines = ["## praxis session audit", ""]

    intro = {
        "new": "This looks like a **new / empty project**. Offer to run `/praxis:bootstrap` to establish a top-tier Claude Code setup from scratch.",
        "uninitialised": "This is an **existing repo with no Claude Code setup**. Recommend `/praxis:bootstrap` to analyse the codebase and generate a CLAUDE.md + guardrails.",
        "legacy": "This repo has a **CLAUDE.md not managed by praxis** (legacy or from another tool). Recommend `/praxis:bootstrap` — it will reconcile and migrate the existing file through the verifier so nothing valuable is lost.",
        "partial": "This repo has **partial Claude Code config**. Recommend `/praxis:doctor` to reconcile it.",
        "managed": "This repo is **managed by praxis**. Continuous quality gates are active.",
    }.get(state, "")
    lines.append(f"**State:** `{state}` — {intro}")
    lines.append("")

    # Health signals
    secrets = quick_secret_scan(root)
    if secrets:
        lines.append("**⚠️ Potential secrets / sensitive files detected:**")
        for s in secrets:
            lines.append(f"  - {s}")
        lines.append("  → Treat as high priority. Do not read these into context; "
                     "recommend rotating exposed values and adding them to .gitignore.")
        lines.append("")

    nested = nested_claude_md(root)
    if nested:
        lines.append(f"**Nested CLAUDE.md files:** {len(nested)} "
                     f"(e.g. {', '.join(nested[:5])}). These load when working in "
                     "their directories; keep them consistent with the root file.")
        lines.append("")

    test_cmd = common.detect_test_command(root)
    if test_cmd:
        lines.append(f"**Detected test command:** `{test_cmd}`")

    # Monorepo / workspace awareness
    workspaces = common.detect_workspaces(root)
    if workspaces:
        kinds = sorted({w["kind"] for w in workspaces})
        sample = ", ".join(w["path"] for w in workspaces[:5])
        lines.append(f"**Monorepo detected:** {len(workspaces)} package(s) "
                     f"({'/'.join(kinds)}) — e.g. {sample}. Run and audit the tests of the "
                     "specific package(s) you change, not just the root.")

    # Living-knowledge health
    has_docs = (root / "docs").is_dir()
    has_changelog = (root / "CHANGELOG.md").exists()
    if not has_docs or not has_changelog:
        missing = []
        if not has_docs:
            missing.append("/docs")
        if not has_changelog:
            missing.append("CHANGELOG.md")
        lines.append(f"**Living knowledge missing:** {', '.join(missing)} — scaffold via "
                     "`/praxis:bootstrap` (or the `docs-living` skill); every repo should have both.")

    if common.is_git_repo(root):
        dirty = common.git_status_porcelain(root)
        if dirty:
            lines.append(f"**Uncommitted changes:** {len(dirty)} file(s) — the quality "
                         "gate will require a passing `/praxis:audit` before the turn "
                         "can finish while code is unreviewed.")
    lines.append("")

    # Surface any open praxis task so it can be resumed or cleared.
    task = common.read_state(root, "task.json")
    if task.get("open") and task.get("status") in ("in_progress", "waiting_for_user", "cap_reached"):
        lines.append(f"**Open praxis task:** '{task.get('title','')}' "
                     f"(status: {task.get('status')}, turn {task.get('iterations',0)}/"
                     f"{task.get('max_iterations','?')}). Resume it, or close it with "
                     "`task_state.py done` / `clear` if it is no longer relevant.")
        lines.append("")

    # Standing directives (reinforce the always-on workflow every session).
    lines.append("**praxis standing directives (apply to all work this session):**")
    lines.append("- Own every implementation request end to end and autonomously: "
                 "restructure the prompt into a spec → investigate → plan (plan mode) → "
                 "implement → audit → structured report. Interrupt the user ONLY at a "
                 "genuine decision point.")
    lines.append("- For any multi-step task, open a praxis task so the session self-drives "
                 "to completion (no need for /goal): "
                 "`python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py\" open \"<title>\" "
                 "--criteria \"...\" --max <N>`. Mark `waiting` before stopping to ask the "
                 "user; mark `done` only when every criterion is met and the audit is green. "
                 "The Stop gate keeps you working until then.")
    lines.append("- Apply the best-practices relevant to the change (use the `best-practices` "
                 "skill: SOLID/DDD/REST/OWASP/ACID-CAP/testing as the domains require) — the "
                 "minimal fitting set, matched to repo conventions; don't cargo-cult.")
    if common.autopilot_on(root):
        lines.append("- **AUTO-PILOT IS ON:** do not ask the user design/approach questions. "
                     "Do your own QA and decide by the best-practice that fits, recording "
                     "each decision under 'Decisions taken autonomously' in the report. Only "
                     "stop for a hard external blocker (e.g. a missing credential).")
    lines.append("- Living knowledge is part of 'done': for every behaviour/API/config/"
                 "architecture change, update `/docs` (read/search first, no regression), add a "
                 "`CHANGELOG.md` [Unreleased] entry, and record an ADR for significant or "
                 "autonomous decisions (use the `docs-living` skill). Every repo must have a `/docs`.")
    lines.append("- Documentation-first: find the authoritative docs and existing in-repo "
                 "patterns before writing; never reinvent or duplicate what exists.")
    lines.append("- Apply code-craft: self-documenting names, comments that explain *why*, "
                 "no debug leftovers, no commented-out or dead code.")
    lines.append("- Completeness is mandatory: no placeholders/TODOs/stubs and no silently "
                 "narrowed scope. State anything out-of-scope explicitly in the report.")
    lines.append("- After any non-trivial change, run the quality rubric (`/praxis:audit`) "
                 "— vertical auditors (doc-reference, duplication, regression, adversarial, "
                 "edge-case, performance, completeness) + a horizontal pass — and fix every "
                 "finding before declaring done.")
    lines.append("- praxis is effort-agnostic: it works identically at `/effort high` or "
                 "`/effort ultracode`; higher effort only deepens execution. Auditors are "
                 "pinned to Opus/high regardless.")

    # Record that we audited this session state.
    common.write_state(root, "last_session_audit.json", {
        "state": state,
        "signature": common.change_signature(root) if common.is_git_repo(root) else "",
    })
    return "\n".join(lines)


def main() -> None:
    data = common.read_hook_input()
    root = common.project_dir(data)
    try:
        report = build_report(root)
    except Exception:
        report = ("## praxis\nSession harness active. Run `/praxis:doctor` if setup "
                  "looks off.")
    common.emit_context(report)
    common.allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        common.allow()
