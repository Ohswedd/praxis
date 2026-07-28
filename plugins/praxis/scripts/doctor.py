#!/usr/bin/env python3
"""
praxis doctor (utility invoked by /praxis:doctor).

Read-only self-check. Reports:
  * installed praxis plugin version (from plugin.json)
  * repo management state and setup completeness
  * the settings actually in force (not their defaults)
  * documentation drift: docs that contradict the live config or reference
    something that no longer exists
  * whether the quality gate is currently enabled

Offline-safe. Prints a human-readable report; the doctor command's skill decides
what to fix and always asks before changing anything.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


def plugin_version() -> str:
    here = Path(__file__).resolve().parent.parent
    manifest = here / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("version", "?")
    except Exception:
        return "?"


def checks(root: Path):
    out = []
    ok = lambda b: "OK" if b else "MISSING"

    claude_md = (root / "CLAUDE.md").exists()
    settings = (root / ".claude" / "settings.json").exists()
    gitignore = root / ".gitignore"
    ignores_state = False
    if gitignore.exists():
        try:
            ignores_state = ".praxis" in gitignore.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    out.append(("CLAUDE.md present", ok(claude_md)))
    out.append((".claude/settings.json present", ok(settings)))
    out.append(("/docs present", ok((root / "docs").is_dir())))
    out.append(("CHANGELOG.md present", ok((root / "CHANGELOG.md").exists())))
    out.append((".gitignore covers .claude/.praxis", ok(ignores_state)))

    cfg = common.read_config(root)
    gate_off = (
        os.environ.get("PRAXIS_GATE", "").lower() in ("off", "0", "false")
        or (common.state_dir(root) / "skip-gate").exists()
        or cfg.get("gate.enabled", True) is False
    )
    out.append(("quality gate", "DISABLED" if gate_off else "ENABLED"))
    out.append(("test evidence required", "yes" if cfg.get("gate.require_tests", True) else "no"))
    out.append(("UI verticals required on UI changes",
                "yes" if cfg.get("gate.require_ui_verticals", True) else "no"))
    out.append(("auto-pilot", "ON" if common.autopilot_on(root) else "OFF"))
    if common.is_git_repo(root):
        merge = "auto-merge ON" if common.auto_merge_on(root) else "PR only (human merges)"
        out.append((f"git delivery (base: {common.git_default_branch(root)})", merge))
    out.append(("house style: em dashes",
                "banned" if cfg.get("style.ban_em_dash", True) else "allowed"))
    out.append(("house style: AI attribution",
                "banned" if cfg.get("style.ban_ai_attribution", True) else "allowed"))
    out.append((".praxis.toml config", "present" if (root / ".praxis.toml").exists() else "defaults"))
    return out


def _integrity() -> str:
    """The self-check verdict, with the scope it actually covered.

    Naming the scope matters here: doctor usually runs against an installed
    plugin, where the marketplace and the repo prose are simply not present. A
    bare OK would imply they were examined, and the honest line is the one that
    says which question was answered.
    """
    here = Path(__file__).resolve().parent
    try:
        sc = subprocess.run(
            [sys.executable, str(here / "selfcheck.py")],
            capture_output=True, text=True, timeout=30,
            # A diagnostic must not write to the directory it is diagnosing. The
            # self-check imports a module, and an import caches bytecode beside
            # it, which for an installed plugin means mutating the plugin cache.
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except Exception as exc:
        return f"unknown ({exc.__class__.__name__})"

    scope = ("full source tree" if "repo scope" in sc.stdout
             else "installed plugin" if "installed-plugin scope" in sc.stdout
             else "unrecognised scope")
    if sc.returncode == 0:
        return f"OK ({scope})"
    problems = [ln.strip().lstrip("✗ ") for ln in sc.stdout.splitlines()
                if ln.strip().startswith("✗")]
    if not problems:
        return f"PROBLEM ({scope}), see `selfcheck.py` for the detail"
    # Name the first problem and say where the rest are: a bare count is a dead
    # end for a reader who cannot see the subprocess output.
    rest = (f" (+{len(problems) - 1} more, run "
            "`python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/selfcheck.py\"`)"
            if len(problems) > 1 else "")
    return f"PROBLEM ({scope}): {problems[0]}{rest}"


def main() -> None:
    data = common.read_hook_input()
    root = common.project_dir(data)
    lines = [f"## praxis doctor  (plugin v{plugin_version()})", ""]
    lines.append(f"- plugin integrity: **{_integrity()}**")
    for name, status in checks(root):
        lines.append(f"- {name}: **{status}**")

    drift = common.run_scanner("drift.py", root)
    lines.append("")
    if drift:
        lines.append(f"### Documentation drift: {len(drift)} finding(s)")
        for f in drift[:15]:
            lines.append(f"- `{f.get('file')}:{f.get('line')}` {f.get('detail')}")
        if len(drift) > 15:
            lines.append(f"- ... and {len(drift) - 15} more")
        lines.append("Fix with `/praxis:docs`, which routes CLAUDE.md edits through the "
                     "regression verifier rather than overwriting them.")
    else:
        lines.append("- documentation drift: **none** "
                     "(docs agree with the live config and every reference resolves)")

    lines.append("")
    lines.append("Run `/praxis:bootstrap` to (re)establish any MISSING items. "
                 "praxis proposes changes and asks before writing.")
    common.emit_context("\n".join(lines))
    common.allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        common.allow()
