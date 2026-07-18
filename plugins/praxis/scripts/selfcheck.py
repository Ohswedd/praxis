#!/usr/bin/env python3
"""
Praxis self-check — validates the plugin's own integrity.

Verifies the things that would silently break the plugin at load time:
  * all JSON manifests parse; plugin/marketplace versions agree
  * hooks.json references scripts that actually exist
  * every agent, skill (SKILL.md), command, and the output style has YAML
    frontmatter with the required keys — and frontmatter that actually parses
    (unquoted scalars containing ': ' are rejected: YAML silently drops them)
  * every Python script byte-compiles

Exit code 0 if healthy, 1 if any problem — so it can gate CI. Run it directly, or
via `/praxis:doctor`.
"""

from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent   # plugins/praxis
ROOT = PLUGIN.parent.parent                        # repo root


def _frontmatter_keys(md: Path):
    """Top-level frontmatter keys, or None if the file has no frontmatter or
    frontmatter that YAML would fail to parse.

    A silent, high-impact failure mode: an unquoted plain scalar value containing
    ': ' (colon-space), e.g. `description: understand a repo: its purpose ...`.
    A YAML loader rejects that line, drops the *entire* frontmatter, and the
    agent/skill then loads with empty metadata (name, tools, model all lost). We
    treat it as invalid here so `make check`/CI catch it before publish, instead
    of only `claude plugin validate` catching it after."""
    try:
        text = md.read_text(encoding="utf-8")
    except Exception:
        return None
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    keys = set()
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z0-9_-]+):(.*)$", line)
        if not mm:
            continue
        keys.add(mm.group(1))
        value = mm.group(2).strip()
        if value[:1] not in ("", '"', "'") and ": " in value:
            return None  # unquoted scalar with ': ' — YAML would drop the frontmatter
    return keys


def check():
    errors, checks = [], 0

    def need(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            errors.append(msg)

    # manifests
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    market_json = ROOT / ".claude-plugin" / "marketplace.json"
    try:
        pj = json.loads(plugin_json.read_text())
        need("name" in pj and "version" in pj, "plugin.json missing name/version")
    except Exception as e:
        pj = {}
        errors.append(f"plugin.json invalid: {e}")
    try:
        mj = json.loads(market_json.read_text())
        mv = mj.get("metadata", {}).get("version")
        need(mv == pj.get("version"),
             f"version mismatch: plugin={pj.get('version')} marketplace={mv}")
    except Exception as e:
        errors.append(f"marketplace.json invalid: {e}")

    # hooks reference existing scripts
    try:
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
        refs = re.findall(r"scripts/([A-Za-z0-9_]+\.py)", json.dumps(hooks))
        for r in refs:
            need((PLUGIN / "scripts" / r).exists(), f"hook references missing script: {r}")
    except Exception as e:
        errors.append(f"hooks.json invalid: {e}")

    # frontmatter on agents / skills / commands / output styles
    for md in (PLUGIN / "agents").glob("*.md"):
        k = _frontmatter_keys(md)
        need(k and {"name", "description"} <= k, f"agent {md.name}: bad/missing frontmatter")
    for skill in (PLUGIN / "skills").glob("*/SKILL.md"):
        k = _frontmatter_keys(skill)
        need(k and {"name", "description"} <= k,
             f"skill {skill.parent.name}: bad/missing frontmatter")
    for cmd in (PLUGIN / "commands").glob("*.md"):
        k = _frontmatter_keys(cmd)
        need(k and "description" in k, f"command {cmd.name}: missing description frontmatter")
    for style in (PLUGIN / "output-styles").glob("*.md"):
        k = _frontmatter_keys(style)
        need(k and {"name", "description"} <= k, f"output-style {style.name}: bad frontmatter")

    # python compiles
    for py in (PLUGIN / "scripts").rglob("*.py"):
        try:
            py_compile.compile(str(py), doraise=True)
            checks += 1
        except Exception as e:
            errors.append(f"compile error in {py.name}: {e}")

    # agent references (@praxis:name) must resolve to real agents
    agent_names = set()
    for md in (PLUGIN / "agents").glob("*.md"):
        k = _frontmatter_keys(md)
        # read the name value
        try:
            for line in md.read_text(encoding="utf-8").splitlines():
                mm = re.match(r"^name:\s*(\S+)", line)
                if mm:
                    agent_names.add(mm.group(1))
                    break
        except Exception:
            pass
    referenced = set()
    for area in ("skills", "commands", "output-styles"):
        for md in (PLUGIN / area).rglob("*.md"):
            try:
                referenced |= set(re.findall(r"@praxis:([a-z0-9-]+)", md.read_text(encoding="utf-8")))
            except Exception:
                pass
    for ref in sorted(referenced):
        need(ref in agent_names, f"dangling agent reference @praxis:{ref}")

    # marketplace source paths resolve to a plugin
    try:
        mj = json.loads(market_json.read_text())
        for pl in mj.get("plugins", []):
            src = (ROOT / pl.get("source", "")).resolve()
            need((src / ".claude-plugin" / "plugin.json").exists(),
                 f"marketplace source has no plugin.json: {pl.get('source')}")
    except Exception:
        pass

    return checks, errors


def main() -> int:
    checks, errors = check()
    if errors:
        print(f"praxis selfcheck: {len(errors)} problem(s) across {checks} checks:")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print(f"praxis selfcheck: OK ({checks} checks passed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
