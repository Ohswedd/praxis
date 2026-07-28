#!/usr/bin/env python3
"""
praxis settings, read and toggled in one place.

praxis has three switches a user actually flips: auto-pilot (ask nothing, decide
by best-practice), auto-merge (praxis merges its own PRs, or a human does), and
the Stop gate. Each used to have its own script and its own command, which made
the surface larger without making anything clearer, and left the third with no
command at all.

Every switch resolves the same way, most specific first:

    environment variable  ->  repo toggle file  ->  .praxis.toml  ->  default

so `status` is the authoritative answer to "what is actually in force here", and
the source of a surprising value is always named.

Usage:
    config.py                       # everything, resolved, with its source
    config.py status
    config.py autopilot  on|off
    config.py auto-merge on|off
    config.py gate       on|off
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


# switch -> (toggle filename, env var, config key, inverted?)
#
# The gate is inverted: its toggle file is `skip-gate`, so the file's presence
# means OFF while the other two mean ON. Encoding that here keeps one code path
# instead of special-casing the gate at every call site.
SWITCHES = {
    "autopilot": ("autopilot", "PRAXIS_AUTOPILOT", "autopilot.default", False),
    "auto-merge": ("auto-merge", "PRAXIS_AUTO_MERGE", "git.auto_merge", False),
    "gate": ("skip-gate", "PRAXIS_GATE", "gate.enabled", True),
}

_ON_WORDS = ("on", "1", "true", "yes", "enable", "enabled")
_OFF_WORDS = ("off", "0", "false", "no", "disable", "disabled")

DESCRIPTIONS = {
    "autopilot": ("ON: praxis asks nothing and resolves each decision by the "
                  "best-practice that fits, recording it in the report.",
                  "OFF: praxis stops to ask at a genuine decision point."),
    "auto-merge": ("ON: praxis self-reviews and merges its own PRs once the audit "
                   "and the required checks are green.",
                   "OFF: praxis opens the PR and leaves the merge to a human."),
    "gate": ("ON: the Stop hook holds the turn open until the change is audited "
             "and any open task is finished.",
             "OFF: praxis can end a turn with the change unreviewed."),
}


def resolve(root: Path, switch: str):
    """(value, source) for one switch, most specific source first.

    Only the toggle *file* is inverted. `PRAXIS_GATE=off` disables the gate and
    `gate.enabled = true` enables it, both read the natural way round; it is
    solely the file that records the off state by existing. Applying the
    inversion to all three sources would make `PRAXIS_GATE=on` report the gate as
    disabled, which is the opposite of what the hook does with it.
    """
    toggle, env_var, key, inverted = SWITCHES[switch]
    env = os.environ.get(env_var, "").strip().lower()
    if env in _ON_WORDS:
        return True, f"env {env_var}={env}"
    if env in _OFF_WORDS:
        return False, f"env {env_var}={env}"
    if (common.state_dir(root) / toggle).exists():
        return (False if inverted else True), f".claude/.praxis/{toggle}"
    cfg = common.read_config(root)
    return bool(cfg.get(key)), (".praxis.toml" if (root / ".praxis.toml").exists()
                                else "default")


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
    print("\nToggle: config.py <autopilot|auto-merge|gate> <on|off>. "
          "Version a permanent choice in .praxis.toml instead of a toggle file.")
    return 0


def main() -> int:
    root = common.project_dir({})
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0] == "status":
        return status(root)

    switch = args[0]
    if switch not in SWITCHES:
        print(f"praxis: unknown setting '{switch}'. "
              f"Known: {', '.join(SWITCHES)}, or `status`.")
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
