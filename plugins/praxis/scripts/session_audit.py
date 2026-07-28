#!/usr/bin/env python3
"""
praxis SessionStart audit.

Runs when a session opens (and again on resume). Whatever it prints to stdout
is injected into Claude's context, so this is where praxis orients the model:

  * resolves the **workspace mode**: whether this repository is ours to set up,
    or one we merely contribute to, in which case everything praxis writes stays
    on the machine and is git-excluded
  * classifies the repo state (new / un-initialised / legacy CLAUDE.md / managed)
    and, when praxis is not set up here, *instructs* the session to bootstrap
    rather than suggesting it
  * surfaces a concise health report (secrets, missing setup, drift, TODOs)
  * states the repo's **live** configuration, so no turn ever reasons from a
    default that the repo has overridden. Documentation goes stale; the resolved
    value cannot.

It is otherwise read-only, fast, and offline-safe, and it never blocks. Its one
write is the per-clone exclude block in contributor mode, which has to exist
before anything else runs: a praxis artifact that is not excluded from the moment
it is created is one `git add -A` away from someone else's pull request.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

#: Drift findings shown inline before the rest is summarised as a count.
DRIFT_PREVIEW = 5


def quick_secret_scan(root: Path, cap: int = 400) -> list:
    hits = []
    files = common.tracked_files(root, limit=cap) or []
    if not files:
        # not a git repo yet: scan shallow with a pruning walk (skips node_modules etc.)
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


def live_config(root: Path) -> list:
    """The settings actually in force, resolved from env + toggles + .praxis.toml.

    This block exists because of a specific, repeated failure: a session reads a
    document that states a default ("praxis opens the PR and a human merges"),
    the repo has since overridden it, and the session confidently acts on and
    repeats the stale policy. A resolved value stated every session cannot go
    stale, so the resolved value wins over any prose.
    """
    cfg = common.read_config(root)
    mode, source = common.workspace_mode_reason(root)
    items = [
        f"workspace mode: **{mode}** (from {source})",
        f"quality gate: **{'ON' if common.gate_enabled(root) else 'OFF'}**",
        f"test evidence required: **{'yes' if cfg.get('gate.require_tests', True) else 'no'}**",
        f"UI verticals required on UI changes: "
        f"**{'yes' if cfg.get('gate.require_ui_verticals', True) else 'no'}**",
        f"auto-pilot: **{'ON' if common.autopilot_on(root) else 'OFF'}**",
        f"auto-bootstrap: **{'ON' if common.bootstrap_auto(root) else 'OFF'}**",
    ]
    if common.is_git_repo(root):
        merge = "ON (praxis reviews and merges its own PRs after a green audit)" \
            if common.auto_merge_on(root) else "OFF (praxis opens the PR; a human merges)"
        items.append(f"auto-merge: **{merge}**, base branch `{common.git_default_branch(root)}`")
    items.append(
        f"house style: em dashes **{'banned' if cfg.get('style.ban_em_dash', True) else 'allowed'}**, "
        f"AI attribution in commits/PRs "
        f"**{'banned' if cfg.get('style.ban_ai_attribution', True) else 'allowed'}**")
    return items


def workspace_block(root: Path) -> list:
    """Whose repository this is, why praxis thinks so, and where it will write.

    Stated every session and near the top, because it is the one fact that
    changes what a turn is allowed to leave behind. A session that assumes the
    repo is ours and is wrong does not fail loudly: it quietly adds a CLAUDE.md, a
    /docs tree and a CHANGELOG to somebody else's project, and the mistake is only
    visible in the pull request.
    """
    mode, source = common.workspace_mode_reason(root)
    if mode != common.CONTRIBUTOR:
        return [f"**Workspace:** `owner` ({source}). praxis maintains this repo's "
                "CLAUDE.md, settings, `/docs`, CHANGELOG and ADRs as committed "
                "project files."]

    common.ensure_local_exclusions(root, True)
    # Pin the verdict the first time it is reached. Without this, the ordinary
    # contribution workflow undoes the mode: you clone (contributor), praxis sets
    # up locally, you fix the bug and commit, and on the next session your own
    # address is in `git log`, detection says `owner`, and praxis starts writing
    # a CLAUDE.md and a /docs tree into a repository that is not yours.
    pinned = common.persist_workspace_mode(root, mode)
    return [
        f"**⚠️ Workspace: `contributor`** ({source}). **This repository is not "
        "ours.** Everything praxis authors stays on this machine and is excluded "
        "in `$GIT_COMMON_DIR/info/exclude`; the repo's own files are touched only "
        "where the user's actual change requires it.",
        "  - operating brief → `CLAUDE.local.md` (the repo's `CLAUDE.md` is never "
        "edited or reconciled)",
        "  - settings → `.claude/settings.local.json`; praxis config → "
        "`.claude/.praxis/praxis.toml`",
        "  - `/docs`, `CHANGELOG.md`, `docs/adr/`, `docs/design/` → updated **only "
        "if the repo already has them**, following its conventions; otherwise "
        "written under `.claude/.praxis/knowledge/`",
        "  - never create `.praxis.toml`, `/docs`, `CHANGELOG.md` or a `CLAUDE.md` "
        "here, and never edit `.gitignore` on praxis's behalf",
        "  - never stage `CLAUDE.local.md`, `.claude/.praxis/` or "
        "`.claude/settings.local.json`; the commit belongs to the project, not to "
        "your setup. Deliver through a fork/topic branch and match the repo's own "
        "commit, PR and changelog conventions.",
        "  - if this verdict is wrong, say so: `/praxis:config mode owner`."
        + (" This verdict is now pinned in `.claude/.praxis/workspace`, so your "
           "own commits here will not silently flip it back." if pinned else ""),
    ]


def bootstrap_block(root: Path, state: str) -> list:
    """The instruction to set this repo up, issued before any other work.

    Recommending it did not work. The line "Recommend /praxis:bootstrap" sat at
    the top of every session in an unmanaged repo and was routinely stepped past,
    leaving the session with no operating brief, no guardrails and no /docs, which
    is the state praxis exists to prevent.
    """
    if not common.bootstrap_required(root):
        return []
    contributor = common.is_contributor(root)
    where = common.bootstrap_targets(root)
    lines = [
        f"**⚠️ praxis is not set up in this repository (state: `{state}`). "
        "Run the `bootstrap` skill NOW, before the user's first request.** It is "
        "the first step of the pipeline, not an optional command: map the repo "
        f"read-only, then write {where}.",
        "  - Write what does not exist without asking, then carry straight on to "
        "the user's actual request in the same turn. Report the setup in one line; "
        "do not turn it into a conversation.",
    ]
    if contributor:
        lines.append("  - Nothing lands in the repository itself, so there is "
                     "nothing to confirm: the brief is additive and the repo's own "
                     "`CLAUDE.md`, if it has one, is left exactly as it is.")
    else:
        lines.append("  - The one thing to stop and ask about is reconciling an "
                     "existing non-praxis `CLAUDE.md`: that merge can drop a still-"
                     "valid instruction, so route it through "
                     "`@praxis:claudemd-verifier` and show the before/after first.")
    lines.append("  - Turn this off for this repo with `/praxis:config bootstrap "
                 "off` (or `bootstrap.auto = false`).")
    return lines


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
    state = common.repo_state(root)
    lines = ["## praxis session audit", ""]

    intro = {
        "new": "a **new / empty project**, so the setup is written from scratch.",
        "uninitialised": "an **existing codebase with no Claude Code setup**: map it read-only first, then generate the brief and the guardrails from what is actually there.",
        "legacy": "there is a **brief praxis did not write** (legacy, or from another tool). It is reconciled and migrated through the verifier so nothing valuable is lost, never overwritten.",
        "partial": "**partial Claude Code config**. Complete it, and run `/praxis:doctor` to see what is missing.",
        "managed": "**managed by praxis**. Continuous quality gates are active.",
    }.get(state, "")
    lines.append(f"**State:** `{state}`, {intro}")
    lines.append("")

    lines += workspace_block(root)
    lines.append("")

    boot = bootstrap_block(root, state)
    if boot:
        lines += boot
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

    lines.append("**Live configuration (resolved now; it outranks anything a doc says):**")
    for item in live_config(root):
        lines.append(f"  - {item}")
    test_cmd = common.detect_test_command(root)
    lines.append(f"  - test command: `{test_cmd}`" if test_cmd
                 else "  - test command: **none detected** (say so when you report coverage)")
    lines.append("")

    drift = common.run_scanner("drift.py", root)
    if drift:
        lines.append(f"**⚠️ Documentation drift: {len(drift)} finding(s).** The docs "
                     "contradict the live configuration or reference something that no "
                     "longer exists. Fix them as part of the next change (`/praxis:docs`), "
                     "and never repeat a claim from a drifted line:")
        for f in drift[:DRIFT_PREVIEW]:
            lines.append(f"  - {f.get('file')}:{f.get('line')}, {f.get('detail')}")
        if len(drift) > DRIFT_PREVIEW:
            lines.append(f"  - ... and {len(drift) - DRIFT_PREVIEW} more "
                         "(`python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/drift.py\"`)")
        lines.append("")

    # Monorepo / workspace awareness
    workspaces = common.detect_workspaces(root)
    if workspaces:
        kinds = sorted({w["kind"] for w in workspaces})
        sample = ", ".join(w["path"] for w in workspaces[:5])
        lines.append(f"**Monorepo detected:** {len(workspaces)} package(s) "
                     f"({'/'.join(kinds)}): e.g. {sample}. Run and audit the tests of the "
                     "specific package(s) you change, not just the root.")

    # Living-knowledge health. In a repository that is not ours, a missing /docs
    # or CHANGELOG is the project's choice, not a gap for praxis to fill, so the
    # answer is where praxis will keep its own records instead.
    has_docs = (root / "docs").is_dir()
    has_changelog = (root / "CHANGELOG.md").exists()
    if not has_docs or not has_changelog:
        missing = [name for name, present in (("/docs", has_docs),
                                              ("CHANGELOG.md", has_changelog))
                   if not present]
        if common.is_contributor(root):
            lines.append(f"**This repo has no {' and no '.join(missing)}.** Do not "
                         "add what it chose not to have: record what this change "
                         "needs under `.claude/.praxis/knowledge/` instead.")
        else:
            lines.append(f"**Living knowledge missing:** {', '.join(missing)}, "
                         "scaffold it as part of bootstrap (or with the "
                         "`docs-living` skill); every repo should have both.")

    if common.is_git_repo(root):
        dirty = common.git_status_porcelain(root)
        if dirty:
            lines.append(f"**Uncommitted changes:** {len(dirty)} file(s), the quality "
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
    lines.append("- Bootstrap comes first: in any repo praxis has not set up, run the "
                 "`bootstrap` skill before the work, not instead of it, then continue "
                 "in the same turn. Respect the workspace mode above: in `contributor` "
                 "every praxis artifact is local and git-excluded, and the repository "
                 "gets nothing but the change the user actually asked for.")
    lines.append("- For any multi-step task, open a praxis task so the session self-drives "
                 "to completion (no need for /goal): "
                 "`python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py\" open \"<title>\" "
                 "--criteria \"...\" --max <N>`. Mark `waiting` before stopping to ask the "
                 "user; mark `done` only when every criterion is met and the audit is green. "
                 "The Stop gate keeps you working until then.")
    lines.append("- Apply the best-practices relevant to the change (use the `best-practices` "
                 "skill: SOLID/DDD/REST/OWASP/ACID-CAP/testing as the domains require), the "
                 "minimal fitting set, matched to repo conventions; don't cargo-cult.")
    lines.append("- Any change that adds or alters user-facing surface (markup, styles, "
                 "components, `docs/design/`) IS front-end work, however it was phrased, and "
                 "runs the `frontend-pipeline` skill proportionally: business research → "
                 "story-first wireframes → design system → development → optimization. Read "
                 "its `reference/craft.md` before writing markup or styles: generic defaults "
                 "(centered everything, gradient hero, three equal cards, stock icons, lorem "
                 "ipsum, invented testimonials) are defects, not taste. The gate enforces "
                 "this: a UI diff is not green without `accessibility=pass` and "
                 "`design-consistency=pass` in the report.")
    lines.append("- House style, enforced deterministically, so do not test it: **no em "
                 "dashes** anywhere you write (a colon, a comma, parentheses, or two "
                 "sentences say it better) and **no AI attribution**, no `Co-Authored-By: "
                 "Claude`, no \"generated with\" credit, no robot emoji, in any commit, tag, "
                 "PR, release, or issue. The PreToolUse guard blocks the command; the Stop "
                 "gate blocks the turn. Both apply to your replies too, not only to files.")
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
    lines.append("- You are not building an MVP: unless the user asked for a prototype, "
                 "deliver the finished product. No placeholders/TODOs/stubs, no deferral "
                 "language ('for now', 'in a real implementation', 'you can extend this', "
                 "'future work will'), no silently narrowed scope: error handling and the "
                 "states you know are needed are in scope, not follow-ups. Everything in "
                 "scope is finished in THIS change; 'Out of scope / follow-ups' is for what "
                 "the user excluded, not for what you ran out of patience for. The Stop gate "
                 "scans your own diff AND your new untracked files for unfinished markers.")
    lines.append("- After any non-trivial change, run the quality rubric (`/praxis:audit`) "
                 "(vertical auditors: doc-reference, duplication, regression, adversarial, "
                 "edge-case, performance, completeness, plus a horizontal pass) and fix every "
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
