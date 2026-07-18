#!/usr/bin/env python3
"""
Praxis workspace lister — surfaces monorepo packages so changes are tested and
audited at the right package, not just the repo root.

Usage:
    workspaces.py            # human-readable list
    workspaces.py --json     # machine-readable
"""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


def main() -> int:
    root = common.project_dir({})
    ws = common.detect_workspaces(root)
    if "--json" in sys.argv[1:]:
        print(json.dumps({"count": len(ws), "workspaces": ws}, indent=2))
        return 0
    if not ws:
        print("praxis: single-package repo (no workspaces detected).")
        return 0
    print(f"praxis: {len(ws)} workspace package(s):")
    for w in ws:
        print(f"  - {w['path']}  ({w['kind']})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
