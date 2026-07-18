#!/usr/bin/env python3
"""
praxis doctor (utility invoked by /praxis:doctor).

Read-only self-check. Reports:
  * installed praxis plugin version (from plugin.json)
  * repo management state and setup completeness
  * drift between the current repo config and praxis expectations
  * whether the quality gate is currently enabled

Offline-safe. Prints a human-readable report; the doctor command's skill decides
what to fix and always asks before changing anything.
"""

from __future__ import annotations

import json
import os
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

    gate_off = (
        os.environ.get("PRAXIS_GATE", "").lower() in ("off", "0", "false")
        or (common.state_dir(root) / "skip-gate").exists()
    )
    out.append(("quality gate", "DISABLED" if gate_off else "ENABLED"))
    out.append(("auto-pilot", "ON" if common.autopilot_on(root) else "OFF"))
    out.append((".praxis.toml config", "present" if (root / ".praxis.toml").exists() else "defaults"))
    return out


def main() -> None:
    data = common.read_hook_input()
    root = common.project_dir(data)
    lines = [f"## praxis doctor  (plugin v{plugin_version()})", ""]
    # plugin self-integrity
    try:
        import subprocess
        here = Path(__file__).resolve().parent
        sc = subprocess.run([sys.executable, str(here / "selfcheck.py")],
                            capture_output=True, text=True, timeout=30)
        lines.append(f"- plugin integrity: **{'OK' if sc.returncode == 0 else 'PROBLEM'}**")
    except Exception:
        lines.append("- plugin integrity: **unknown**")
    for name, status in checks(root):
        lines.append(f"- {name}: **{status}**")
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
