#!/usr/bin/env python3
"""
praxis PostToolUse handler (Write | Edit | MultiEdit).

Deterministic, cheap, language-agnostic hygiene after each edit:
  * auto-format the edited file with whatever formatter the project already uses
  * surface (but never silently accept) any secret that just landed in the file

PostToolUse cannot undo an edit, so this reacts rather than prevents; prevention
lives in guard_paths.py. Formatter discovery is by capability, not by a fixed
language list — if the tool isn't available, we skip quietly.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


# (extension) -> ordered list of (executable, argv-template). First available wins.
FORMATTERS = {
    ".py": [("ruff", ["ruff", "format", "{f}"]), ("black", ["black", "-q", "{f}"])],
    ".js": [("prettier", ["prettier", "--write", "{f}"])],
    ".jsx": [("prettier", ["prettier", "--write", "{f}"])],
    ".ts": [("prettier", ["prettier", "--write", "{f}"])],
    ".tsx": [("prettier", ["prettier", "--write", "{f}"])],
    ".json": [("prettier", ["prettier", "--write", "{f}"])],
    ".css": [("prettier", ["prettier", "--write", "{f}"])],
    ".scss": [("prettier", ["prettier", "--write", "{f}"])],
    ".html": [("prettier", ["prettier", "--write", "{f}"])],
    ".md": [("prettier", ["prettier", "--write", "{f}"])],
    ".go": [("gofmt", ["gofmt", "-w", "{f}"])],
    ".rs": [("rustfmt", ["rustfmt", "{f}"])],
    ".rb": [("rubocop", ["rubocop", "-A", "{f}"])],
    ".sh": [("shfmt", ["shfmt", "-w", "{f}"])],
    ".java": [("google-java-format", ["google-java-format", "-i", "{f}"])],
    ".kt": [("ktlint", ["ktlint", "-F", "{f}"])],
}


def _which(name: str) -> bool:
    return shutil.which(name) is not None


# Formatters whose output is a single canonical style — always safe to run.
_CANONICAL = {"gofmt", "rustfmt"}


def _adopts(root: Path, exe: str) -> bool:
    """True if the project actually adopts this formatter.

    Prevents reformatting a file with a tool the project doesn't use (e.g.
    running `ruff format` where the team standardised on `black`), which would
    fight the project's real conventions. Canonical formatters are always allowed;
    configurable ones require an adoption signal.
    """
    if exe in _CANONICAL:
        return True
    try:
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore") \
            if (root / "pyproject.toml").exists() else ""
    except Exception:
        pyproject = ""

    if exe == "black":
        return "[tool.black]" in pyproject or (root / ".black").exists() \
            or "black" in pyproject
    if exe == "ruff":
        return "[tool.ruff]" in pyproject or (root / "ruff.toml").exists() \
            or (root / ".ruff.toml").exists()
    if exe == "prettier":
        if any((root).glob(".prettierrc*")) or (root / "prettier.config.js").exists():
            return True
        try:
            pkg = (root / "package.json").read_text(encoding="utf-8", errors="ignore")
            return "prettier" in pkg
        except Exception:
            return False
    if exe == "rubocop":
        return (root / ".rubocop.yml").exists()
    if exe == "shfmt":
        return (root / ".editorconfig").exists()
    if exe in ("google-java-format", "ktlint"):
        for build in ("build.gradle", "build.gradle.kts", "pom.xml"):
            try:
                if exe.split("-")[0] in (root / build).read_text(encoding="utf-8", errors="ignore"):
                    return True
            except Exception:
                pass
        return False
    return False


def format_file(fp: Path, root: Path) -> str:
    ext = fp.suffix.lower()
    for exe, argv in FORMATTERS.get(ext, []):
        if _which(exe) and _adopts(root, exe):
            cmd = [a.replace("{f}", str(fp)) for a in argv]
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return f"formatted with {exe}"
            except Exception:
                return ""
    return ""


def main() -> None:
    data = common.read_hook_input()
    tool_input = data.get("tool_input", {}) or {}
    fp_str = tool_input.get("file_path") or tool_input.get("path") or ""
    if not fp_str:
        common.allow()
    fp = Path(fp_str)
    if not fp.exists() or not fp.is_file():
        common.allow()

    notes = []
    root = common.project_dir(data)
    fmt = format_file(fp, root)
    if fmt:
        notes.append(fmt)

    secrets = common.scan_file_for_secrets(fp)
    if secrets:
        # PostToolUse stderr is shown to the model; flag loudly but do not block.
        common.emit_context("")  # no context injection here
        sys.stderr.write(
            f"[praxis] WARNING: possible secret(s) written to {fp.name}: "
            f"{', '.join(secrets)}. Remove/rotate and use an environment variable "
            "or a redacted template.\n"
        )

    if notes:
        # Non-context informational note for the transcript/debug log.
        print(json.dumps({"suppressOutput": True}))
    common.allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        common.allow()
