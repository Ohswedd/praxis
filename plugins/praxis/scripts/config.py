#!/usr/bin/env python3
"""
praxis settings, read and toggled in one place.

praxis has four switches a user actually flips: auto-pilot (ask nothing, decide
by best-practice), auto-merge (praxis merges its own PRs, or a human does),
auto-bootstrap (set an unmanaged repo up on its own), and the Stop gate. Each
used to have its own script and its own command, which made the surface larger
without making anything clearer, and left some with no command at all.

Every switch resolves the same way, most specific first:

    environment variable  ->  repo toggle file  ->  .praxis.toml  ->  default

so `status` is the authoritative answer to "what is actually in force here", and
the source of a surprising value is always named.

`mode` is the one setting that is not a switch: whether this repository is ours
to set up (`owner`) or one we only contribute to (`contributor`) has a third
state, `auto`, in which praxis works it out from the repo's own git history. So
it records a value rather than an existence, and flipping it also adds or removes
the per-clone exclude block that keeps praxis's files out of the project.

Usage:
    config.py                       # everything, resolved, with its source
    config.py status
    config.py mode       owner|contributor|auto
    config.py autopilot  on|off
    config.py auto-merge on|off
    config.py bootstrap  on|off
    config.py gate       on|off
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


# The switch table and its resolver live in `common`, because every *reader* of a
# switch is a hook and this module is only its presentation layer. Two copies of
# the ladder is how the settings command and the gate it reports on came to
# disagree about the same `PRAXIS_GATE`.
SWITCHES = common.SWITCHES
resolve = common.resolve_switch
_ON_WORDS = common.ON_WORDS
_OFF_WORDS = common.OFF_WORDS

DESCRIPTIONS = {
    "autopilot": ("ON: praxis asks nothing and resolves each decision by the "
                  "best-practice that fits, recording it in the report.",
                  "OFF: praxis stops to ask at a genuine decision point."),
    "auto-merge": ("ON: praxis self-reviews and merges its own PRs once the audit "
                   "and the required checks are green.",
                   "OFF: praxis opens the PR and leaves the merge to a human."),
    "bootstrap": ("ON: a repo praxis has not set up is bootstrapped first, in the "
                  "same turn, before the work starts.",
                  "OFF: praxis works in this repo without a brief or guardrails "
                  "until you run the bootstrap yourself."),
    "gate": ("ON: the Stop hook holds the turn open until the change is audited "
             "and any open task is finished.",
             "OFF: praxis can end a turn with the change unreviewed."),
}

MODE_DESCRIPTIONS = {
    common.OWNER: ("praxis maintains CLAUDE.md, .claude/settings.json, /docs, "
                   "CHANGELOG.md and ADRs as this project's own committed files."),
    common.CONTRIBUTOR: ("this repository is not ours: praxis writes CLAUDE.local.md, "
                         ".claude/settings.local.json and .claude/.praxis/knowledge/, "
                         "all git-excluded, and adds nothing to the project itself."),
}


def set_mode(root: Path, want: str) -> int:
    """Record the workspace mode, and make the exclusions match it.

    Writing the toggle without updating `.git/info/exclude` would leave a clone
    labelled `contributor` whose praxis files are still visible to `git add -A`,
    which is the failure the mode exists to prevent.
    """
    toggle = common.state_dir(root) / common.WORKSPACE_TOGGLE
    try:
        if want == common.AUTO:
            toggle.unlink(missing_ok=True)
        else:
            toggle.write_text(want + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"praxis: could not write the workspace toggle: {exc}")
        return 1

    mode, source = common.workspace_mode_reason(root)
    changed = common.ensure_local_exclusions(root, mode == common.CONTRIBUTOR)
    print(f"praxis mode: {mode} (from {source})")
    print(f"            {MODE_DESCRIPTIONS[mode]}")
    if changed:
        print("            .git/info/exclude updated "
              f"({'added' if mode == common.CONTRIBUTOR else 'removed'} the praxis block).")
    if want != common.AUTO and mode != want:
        print(f"praxis: WARNING, you asked for {want} but {source} still forces "
              f"{mode}. Change that source instead.")
        return 1
    return 0


def set_switch(root: Path, switch: str, on: bool) -> int:
    toggle, env_var, key, inverted = SWITCHES[switch]
    flag = common.state_dir(root) / toggle
    # The gate's toggle file records the OFF state, so writing it means the
    # opposite of what it means for the other two switches.
    want_file = (not on) if inverted else on
    try:
        if want_file:
            flag.write_text("on\n", encoding="utf-8")
        else:
            flag.unlink(missing_ok=True)
    except Exception as exc:
        print(f"praxis: could not write the {switch} toggle: {exc}")
        return 1

    value, source = resolve(root, switch)
    state = "ON" if value else "OFF"
    print(f"praxis {switch}: {state} ({DESCRIPTIONS[switch][0 if value else 1]})")
    if value != on:
        # Silently leaving the switch in the opposite state would be the worst
        # outcome: the user believes they changed the policy and every later turn
        # acts on the old one.
        print(f"praxis: WARNING, you asked for {'ON' if on else 'OFF'} but "
              f"{source} still forces {state}. Change that source instead.")
        return 1
    return 0


def status(root: Path) -> int:
    print(f"## praxis settings  ({root})")
    mode, source = common.workspace_mode_reason(root)
    print(f"  {'mode':<11} {mode:<3}  (from {source})")
    print(f"              {MODE_DESCRIPTIONS[mode]}")
    print(f"              brief={common.brief_path(root).name}  "
          f"settings={common.settings_path(root).relative_to(root)}  "
          f"knowledge={_knowledge_label(root)}")
    for switch in SWITCHES:
        value, source = resolve(root, switch)
        state = "ON " if value else "OFF"
        print(f"  {switch:<11} {state}  (from {source})")
        print(f"              {DESCRIPTIONS[switch][0 if value else 1]}")
    cfg = common.read_config(root)
    print(f"  {'test evidence':<11} {'required' if cfg.get('gate.require_tests') else 'optional'}"
          f"  (gate.require_tests)")
    print(f"  {'UI verticals':<11} "
          f"{'required' if cfg.get('gate.require_ui_verticals') else 'optional'} on UI changes"
          f"  (gate.require_ui_verticals)")
    print(f"  {'em dashes':<11} {'banned' if cfg.get('style.ban_em_dash') else 'allowed'}"
          f"  (style.ban_em_dash)")
    print(f"  {'AI credits':<11} "
          f"{'banned' if cfg.get('style.ban_ai_attribution') else 'allowed'}"
          f"  (style.ban_ai_attribution)")
    if common.is_git_repo(root):
        print(f"  {'PR base':<11} {common.git_default_branch(root)}  (git.default_branch)")
    print("\nToggle: config.py <autopilot|auto-merge|bootstrap|gate> <on|off>, "
          "or config.py mode <owner|contributor|auto>.\n"
          "Version a permanent choice in .praxis.toml instead of a toggle file "
          "(in contributor mode, in .claude/.praxis/praxis.toml, which is local).")
    return 0


def _knowledge_label(root: Path) -> str:
    """Where /docs, CHANGELOG.md and ADRs go, as a path relative to the repo."""
    kroot = common.knowledge_root(root)
    try:
        return "the repo root" if kroot == root else str(kroot.relative_to(root)) + "/"
    except ValueError:
        return str(kroot)


def main() -> int:
    root = common.project_dir({})
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0] == "status":
        return status(root)

    switch = args[0]
    if switch == "mode":
        if len(args) < 2:
            mode, source = common.workspace_mode_reason(root)
            print(f"praxis mode: {mode} (from {source})")
            return 0
        want = args[1].strip().lower()
        if want not in (common.OWNER, common.CONTRIBUTOR, common.AUTO):
            print(f"praxis: '{want}' is not a workspace mode. Use "
                  f"{common.OWNER}, {common.CONTRIBUTOR}, or {common.AUTO}.")
            return 1
        return set_mode(root, want)

    if switch not in SWITCHES:
        print(f"praxis: unknown setting '{switch}'. "
              f"Known: mode, {', '.join(SWITCHES)}, or `status`.")
        return 1
    if len(args) < 2:
        value, source = resolve(root, switch)
        print(f"praxis {switch}: {'ON' if value else 'OFF'} (from {source})")
        return 0

    want = args[1].strip().lower()
    if want in _ON_WORDS:
        return set_switch(root, switch, True)
    if want in _OFF_WORDS:
        return set_switch(root, switch, False)
    print(f"praxis: '{want}' is not a state. Use on or off.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # A CLI whose exit code the caller reads: a silent success would report a
        # setting change that never happened.
        print(f"praxis: settings command failed: {exc}")
        sys.exit(1)
