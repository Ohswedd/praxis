#!/usr/bin/env python3
"""
Praxis repo-scan ledger — the deterministic backbone of /praxis:scan.

A repo-wide audit lives or dies on coverage honesty: on a large codebase it is
easy for an LLM pass to quietly sample "the interesting files" and report the
repo as reviewed. This ledger makes that impossible. It inventories every
auditable file, partitions the inventory into shards, and tracks which
shard × dimension passes actually ran and what each finding's lifecycle was
(open → confirmed/refuted → fixed/deferred). The final report is computed from
recorded state, never from memory.

Usage:
    repo_scan.py init [--scope PATH] [--shard-files N] [--shard-lines N] \
        [--max-files N] [--force]
    repo_scan.py baseline --tests "CMD" --exit N
    repo_scan.py status [--json]
    repo_scan.py shard <id> [--json]
    repo_scan.py mark <shard-id> <dimension>
    repo_scan.py finding add --shard <id> --dimension <dim> --severity <sev> \
        --file <path> --title "..." [--detail "..."]
    repo_scan.py finding verify <fid> --verdict confirmed|refuted|downgraded \
        [--severity <sev>] [--note "..."]
    repo_scan.py finding fix <fid> [--note "..."]
    repo_scan.py finding defer <fid> --reason "..."
    repo_scan.py finding list [--status S] [--json]
    repo_scan.py report [--json]
    repo_scan.py clear [--force]

State lives at .claude/.praxis/repo_scan.json (git-ignored), so a scan survives
session restarts and resumes exactly where it stopped.

Unlike the hook scripts, this CLI does NOT fail open: a ledger that cannot be
read or written is an error, because a swallowed failure here would let the
scan claim coverage it never persisted (ADR-0006).
"""

from __future__ import annotations

import json
import os
import stat
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402

NAME = "repo_scan.json"

# One dimension per praxis vertical auditor; the skill maps each to its agent.
DIMENSIONS = [
    "adversarial",   # security, abuse, unsafe states
    "edge-case",     # correctness, boundaries, error paths
    "regression",    # contracts vs tests, broken promises
    "duplication",   # copy-paste, reinvention, over-engineering
    "performance",   # complexity, hot paths, growth
    "doc-reference", # authoritative docs + in-repo pattern conformance
    "completeness",  # stubs, dead code, debt, unwired pieces
]

SEVERITIES = ("critical", "high", "medium", "low")

# Files that carry no auditable logic. Extension-based, lowercase.
_SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".pdf", ".zip", ".gz", ".tar", ".tgz", ".jar", ".war",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".mov", ".avi", ".webm",
    ".so", ".dylib", ".dll", ".exe", ".bin", ".wasm", ".pyc", ".class",
    ".min.js", ".min.css", ".map",
}
_SKIP_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock",
    "poetry.lock", "pipfile.lock", "composer.lock", "gemfile.lock", "go.sum",
}
_MAX_FILE_BYTES = 500_000  # beyond this it is almost certainly generated


def _load(root):
    try:
        return common.read_state_strict(root, NAME)
    except Exception:
        print(f"praxis repo-scan: {NAME} exists but cannot be parsed — likely a "
              "partial write from an interrupted session. Inspect/restore "
              f".claude/.praxis/{NAME}, or discard it with 'clear --force'.")
        sys.exit(1)


def _save(root, data):
    # Strict on purpose: a failed write must surface, not report success.
    data["updated"] = time.time()
    common.write_state_strict(root, NAME, data)


def _skip_reason(rel: str, root) -> str:
    """Why a tracked file is excluded from the audit inventory ('' = keep)."""
    norm = rel.replace("\\", "/")
    low = norm.lower()
    parts = norm.split("/")
    if any(p in common.PRUNE_DIRS for p in parts[:-1]):
        return "vendored"
    if norm.startswith(".claude/") or norm.startswith(".claude-plugin/"):
        return "meta"
    base = parts[-1].lower()
    if base in _SKIP_NAMES:
        return "lockfile"
    for ext in _SKIP_EXTS:
        if low.endswith(ext):
            return "binary"
    fp = root / rel
    try:
        st = fp.stat()
        if not stat.S_ISREG(st.st_mode):
            return "special"  # FIFO/device/socket: opening one can block forever
        if st.st_size > _MAX_FILE_BYTES:
            return "oversize"
        with open(fp, "rb") as fh:
            if b"\x00" in fh.read(8000):
                return "binary"
    except Exception:
        return "unreadable"
    return ""


def _count_lines(fp) -> int:
    try:
        with open(fp, "rb") as fh:
            return sum(1 for _ in fh)
    except Exception:
        return 0


def _inventory(root, scope: str, max_files: int):
    """(kept [(rel, lines)], excluded {reason: count}, overflow) for the scope.

    `scope` must already be normalised ('.' or a clean relative path).
    Fetches one file beyond max_files so truncation is *detectable*: an
    overflow reason ('' | 'files' | 'dirs') is returned to the caller instead
    of silently dropping the tail — a truncated inventory would forge
    full-coverage claims.
    """
    fetch = max_files + 1
    dir_cap = False
    if common.is_git_repo(root):
        # Scope via git pathspec so a sub-scope of a huge repo is never
        # clipped by a truncation that happened before filtering.
        files = common.tracked_files(root, limit=fetch,
                                     pathspec="" if scope == "." else scope)
    elif scope != "." and (root / scope).is_file():
        files = [scope]
    else:
        base = root if scope == "." else root / scope
        walked, dir_cap = common.walk_files(base, limit=fetch)
        files = walked if scope == "." else [f"{scope}/{rel}" for rel in walked]
    overflow = "dirs" if dir_cap else ("files" if len(files) > max_files else "")
    files = files[:max_files]
    if scope != ".":
        files = [f for f in files if f == scope or f.startswith(scope + "/")]
    kept, excluded = [], {}
    for rel in sorted(set(files)):
        reason = _skip_reason(rel, root)
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        kept.append((rel, _count_lines(root / rel)))
    return kept, excluded, overflow


def _make_shards(kept, shard_files: int, shard_lines: int):
    """Group by top-level directory, then split each group by the caps.

    Grouping keeps a shard semantically coherent (one subsystem), which lets an
    auditor reason about the files as a unit instead of a random sample.
    """
    groups = {}
    for rel, lines in kept:
        key = rel.split("/", 1)[0] if "/" in rel else "."
        groups.setdefault(key, []).append((rel, lines))
    shards = []
    for key in sorted(groups):
        batch, batch_lines = [], 0
        for rel, lines in groups[key]:
            if batch and (len(batch) >= shard_files or batch_lines + lines > shard_lines):
                shards.append({"group": key, "files": batch, "lines": batch_lines})
                batch, batch_lines = [], 0
            batch.append(rel)
            batch_lines += lines
        if batch:
            shards.append({"group": key, "files": batch, "lines": batch_lines})
    for i, sh in enumerate(shards, 1):
        sh["id"] = f"S{i:02d}"
        sh["done"] = []
    return shards


def _shard_by_id(data, sid):
    for sh in data.get("shards", []):
        if sh.get("id") == sid:
            return sh
    return None


def _finding_by_id(data, fid):
    for f in data.get("findings", []):
        if f.get("id") == fid:
            return f
    return None


def _next_finding_num(data) -> int:
    """Next id from the max recorded, not the count — survives any merge/edit."""
    nums = []
    for f in data.get("findings", []):
        try:
            nums.append(int(f.get("id").lstrip("F")))
        except (ValueError, AttributeError):
            continue
    return max(nums, default=0) + 1


def _refuse_secret_text(text: str) -> bool:
    """True (and prints why) if free text matches a secret signature.

    Defense-in-depth: the ledger is persisted and echoed into reports/chat, so
    a credential pasted into --title/--detail/--note must be rejected at the
    door — findings about secrets reference the file path only.
    """
    hits = common.scan_secrets_in_text(text or "")
    if hits:
        print(f"praxis repo-scan: refusing to record — text matches a secret "
              f"signature ({hits[0]}). Reference the file path only; never store "
              "secret values in the ledger.")
        return True
    return False


def cmd_init(root, args) -> int:
    if _load(root).get("shards") and "--force" not in args:
        print("praxis repo-scan: a scan ledger already exists — resume it "
              "(status/shard/mark), or re-init with --force to discard it.")
        return 1
    # normpath collapses './src', 'src/', 'a/./b' — a git pathspec of './src'
    # would otherwise filter against unprefixed git output and match nothing.
    scope = os.path.normpath((common.cli_opt(args, "--scope", ".") or ".").strip()) or "."
    if os.path.isabs(scope) or scope == ".." or scope.startswith(".." + os.sep):
        print("praxis repo-scan: --scope must be a path inside the repo "
              f"(got '{scope}').")
        return 1
    try:
        shard_files = int(common.cli_opt(args, "--shard-files", 25))
        shard_lines = int(common.cli_opt(args, "--shard-lines", 4000))
        max_files = int(common.cli_opt(args, "--max-files", 20000))
    except ValueError:
        print("praxis repo-scan: --shard-files/--shard-lines/--max-files must be integers.")
        return 1
    if shard_files < 1 or shard_lines < 1 or max_files < 1:
        print("praxis repo-scan: shard caps and --max-files must be >= 1.")
        return 1
    kept, excluded, overflow = _inventory(root, scope, max_files)
    if overflow == "files":
        print(f"praxis repo-scan: more than {max_files} files in scope '{scope}' — "
              "refusing to build a silently-truncated inventory. Narrow the scan "
              "with --scope, or raise --max-files to cover everything.")
        return 1
    if overflow == "dirs":
        print(f"praxis repo-scan: the directory walk hit its cap before listing "
              f"scope '{scope}' completely (non-git fallback) — refusing a "
              "truncated inventory. Narrow the scan with --scope, or initialise "
              "git so the inventory can come from 'git ls-files'.")
        return 1
    if not kept:
        print(f"praxis repo-scan: no auditable files found under scope '{scope}'.")
        return 1
    shards = _make_shards(kept, shard_files, shard_lines)
    total_lines = sum(sh["lines"] for sh in shards)
    _save(root, {
        "opened": time.time(),
        "scope": scope,
        "dimensions": DIMENSIONS,
        "shards": shards,
        "findings": [],
        "excluded": excluded,
        "baseline": {},
    })
    excl = ", ".join(f"{k}={v}" for k, v in sorted(excluded.items())) or "none"
    print(f"praxis repo-scan: initialised — {len(kept)} files / {total_lines} lines "
          f"in {len(shards)} shards (scope '{scope}'). Excluded: {excl}.")
    print(f"Dimensions per shard: {', '.join(DIMENSIONS)}.")
    return 0


def cmd_baseline(root, args) -> int:
    data = _load(root)
    if not data.get("shards"):
        print("praxis repo-scan: no scan ledger — run 'repo_scan.py init' first.")
        return 1
    tests = common.cli_opt(args, "--tests")
    exit_raw = common.cli_opt(args, "--exit")
    if tests is None or exit_raw is None:
        print("usage: repo_scan.py baseline --tests \"CMD\" --exit N")
        return 1
    try:
        code = int(exit_raw)
    except ValueError:
        print("praxis repo-scan: --exit must be an integer exit code.")
        return 1
    if _refuse_secret_text(tests):
        return 1
    data["baseline"] = {"command": tests, "exit": code, "ts": time.time()}
    _save(root, data)
    state = "green" if code == 0 else f"RED (exit {code} — pre-existing failures are findings)"
    print(f"praxis repo-scan: baseline recorded — '{tests}' {state}.")
    return 0


def cmd_status(root, args) -> int:
    data = _load(root)
    if not data.get("shards"):
        print("praxis repo-scan: no scan ledger — run 'repo_scan.py init' first.")
        return 1
    if "--json" in args:
        print(json.dumps(data, indent=2))
        return 0
    shards = data["shards"]
    dims = data["dimensions"]
    dimset = set(dims)
    audited = [s for s in shards if set(s["done"]) >= dimset]
    print(f"praxis repo-scan: {len(audited)}/{len(shards)} shards fully audited "
          f"(scope '{data.get('scope', '.')}').")
    for dim in dims:
        n = sum(1 for s in shards if dim in s["done"])
        print(f"  {dim:<14} {n}/{len(shards)} shards")
    pending = [s["id"] for s in shards if set(s["done"]) < dimset]
    if pending:
        print(f"  pending: {', '.join(pending)}")
    counts = {}
    for f in data.get("findings", []):
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"
    print(f"  findings: {summary}")
    base = data.get("baseline") or {}
    if base:
        print(f"  baseline: '{base.get('command')}' exit {base.get('exit')}")
    return 0


def cmd_shard(root, args) -> int:
    data = _load(root)
    if not data.get("shards"):
        print("praxis repo-scan: no scan ledger — run 'repo_scan.py init' first.")
        return 1
    if not args:
        print("usage: repo_scan.py shard <id>")
        return 1
    sh = _shard_by_id(data, args[0])
    if not sh:
        print(f"praxis repo-scan: unknown shard '{args[0]}'.")
        return 1
    if "--json" in args:
        print(json.dumps(sh, indent=2))
        return 0
    remaining = [d for d in data["dimensions"] if d not in sh["done"]]
    print(f"{sh['id']} ({sh['group']}, {len(sh['files'])} files, {sh['lines']} lines) "
          f"— remaining dimensions: {', '.join(remaining) or 'none'}")
    for f in sh["files"]:
        print(f"  {f}")
    return 0


def cmd_mark(root, args) -> int:
    data = _load(root)
    if not data.get("shards"):
        print("praxis repo-scan: no scan ledger — run 'repo_scan.py init' first.")
        return 1
    if len(args) < 2:
        print("usage: repo_scan.py mark <shard-id> <dimension>")
        return 1
    sh = _shard_by_id(data, args[0])
    if not sh:
        print(f"praxis repo-scan: unknown shard '{args[0]}'.")
        return 1
    dim = args[1]
    if dim not in data["dimensions"]:
        print(f"praxis repo-scan: unknown dimension '{dim}' "
              f"(valid: {', '.join(data['dimensions'])}).")
        return 1
    if dim not in sh["done"]:
        sh["done"].append(dim)
    _save(root, data)
    remaining = [d for d in data["dimensions"] if d not in sh["done"]]
    state = "fully audited" if not remaining else f"remaining: {', '.join(remaining)}"
    print(f"praxis repo-scan: {sh['id']} × {dim} recorded — {state}.")
    return 0


def cmd_finding(root, args) -> int:
    data = _load(root)
    if not data.get("shards"):
        print("praxis repo-scan: no scan ledger — run 'repo_scan.py init' first.")
        return 1
    if not args:
        print("usage: repo_scan.py finding add|verify|fix|defer|list ...")
        return 1
    sub, rest = args[0], args[1:]

    if sub == "add":
        shard, dim = common.cli_opt(rest, "--shard"), common.cli_opt(rest, "--dimension")
        sev, path = common.cli_opt(rest, "--severity"), common.cli_opt(rest, "--file")
        title = common.cli_opt(rest, "--title")
        detail = common.cli_opt(rest, "--detail", "")
        if not all((shard, dim, sev, path, title)):
            print("usage: repo_scan.py finding add --shard <id> --dimension <dim> "
                  "--severity <sev> --file <path> --title \"...\" [--detail \"...\"]")
            return 1
        if not _shard_by_id(data, shard):
            print(f"praxis repo-scan: unknown shard '{shard}'.")
            return 1
        if dim not in data["dimensions"]:
            print(f"praxis repo-scan: unknown dimension '{dim}'.")
            return 1
        if sev not in SEVERITIES:
            print(f"praxis repo-scan: severity must be one of {', '.join(SEVERITIES)}.")
            return 1
        if _refuse_secret_text(f"{title} {detail}"):
            return 1
        fid = f"F{_next_finding_num(data):03d}"
        data["findings"].append({
            "id": fid, "shard": shard, "dimension": dim, "severity": sev,
            "file": path, "title": title, "detail": detail,
            "status": "open", "note": "",
        })
        _save(root, data)
        print(f"praxis repo-scan: finding {fid} recorded ({sev}, {dim}, {path}).")
        return 0

    if sub == "list":
        wanted = common.cli_opt(rest, "--status")
        rows = [f for f in data.get("findings", []) if not wanted or f["status"] == wanted]
        if "--json" in rest:
            print(json.dumps(rows, indent=2))
            return 0
        if not rows:
            print("praxis repo-scan: no findings" + (f" with status '{wanted}'." if wanted else "."))
            return 0
        for f in rows:
            print(f"{f['id']} [{f['status']:<9}] {f['severity']:<8} {f['dimension']:<14} "
                  f"{f['file']} — {f['title']}")
        return 0

    if not rest:
        print(f"usage: repo_scan.py finding {sub} <finding-id> ...")
        return 1
    f = _finding_by_id(data, rest[0])
    if not f:
        print(f"praxis repo-scan: unknown finding '{rest[0]}'.")
        return 1

    if sub == "verify":
        verdict = common.cli_opt(rest, "--verdict")
        note = common.cli_opt(rest, "--note", f.get("note", ""))
        if verdict not in ("confirmed", "refuted", "downgraded"):
            print("usage: repo_scan.py finding verify <fid> "
                  "--verdict confirmed|refuted|downgraded [--severity <sev>] [--note \"...\"]")
            return 1
        if _refuse_secret_text(note):
            return 1
        if verdict == "downgraded":
            sev = common.cli_opt(rest, "--severity")
            if sev not in SEVERITIES:
                print("praxis repo-scan: a downgrade needs --severity "
                      f"(one of {', '.join(SEVERITIES)}).")
                return 1
            f["severity"] = sev
            f["status"] = "confirmed"
        else:
            f["status"] = verdict
        f["note"] = note
    elif sub == "fix":
        note = common.cli_opt(rest, "--note", f.get("note", ""))
        if f["status"] != "confirmed":
            print(f"praxis repo-scan: {f['id']} is '{f['status']}' — only a confirmed "
                  "finding can be fixed (verify it first).")
            return 1
        if _refuse_secret_text(note):
            return 1
        f["status"] = "fixed"
        f["note"] = note
    elif sub == "defer":
        reason = common.cli_opt(rest, "--reason")
        if not reason:
            print("usage: repo_scan.py finding defer <fid> --reason \"...\"")
            return 1
        if f["status"] != "confirmed":
            print(f"praxis repo-scan: {f['id']} is '{f['status']}' — only a confirmed "
                  "finding can be deferred.")
            return 1
        if _refuse_secret_text(reason):
            return 1
        f["status"] = "deferred"
        f["note"] = reason
    else:
        print(f"praxis repo-scan: unknown finding command '{sub}'.")
        return 1
    _save(root, data)
    print(f"praxis repo-scan: {f['id']} → {f['status']}"
          + (f" ({f['note']})" if f.get("note") else "") + ".")
    return 0


def cmd_report(root, args) -> int:
    data = _load(root)
    if not data.get("shards"):
        print("praxis repo-scan: no scan ledger — run 'repo_scan.py init' first.")
        return 1
    if "--json" in args:
        print(json.dumps(data, indent=2))
        return 0
    shards, dims = data["shards"], data["dimensions"]
    dimset = set(dims)
    findings = data.get("findings", [])
    audited = [s for s in shards if set(s["done"]) >= dimset]
    files = sum(len(s["files"]) for s in shards)
    lines = sum(s["lines"] for s in shards)
    print(f"# Repo scan report (scope '{data.get('scope', '.')}')\n")
    print(f"**Coverage:** {len(audited)}/{len(shards)} shards fully audited — "
          f"{files} files, {lines} lines across {len(dims)} dimensions.")
    excl = ", ".join(f"{k}={v}" for k, v in sorted(data.get("excluded", {}).items()))
    print(f"**Excluded from inventory:** {excl or 'none'}.")
    base = data.get("baseline") or {}
    if base:
        print(f"**Test baseline:** '{base.get('command')}' exit {base.get('exit')}.")
    print()
    if len(audited) < len(shards):
        gaps = [s["id"] for s in shards if set(s["done"]) < dimset]
        print(f"**INCOMPLETE — unaudited shards:** {', '.join(gaps)}. "
              "This report does not certify the whole repo.\n")
    print("| Status | Count |\n| --- | --- |")
    order = ("open", "confirmed", "fixed", "deferred", "refuted")
    counts = {s: 0 for s in order}
    for f in findings:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    for s in order:
        print(f"| {s} | {counts.get(s, 0)} |")
    unresolved = [f for f in findings if f["status"] in ("open", "confirmed")]
    if unresolved:
        print("\n**Unresolved findings:**")
        for sev in SEVERITIES:
            for f in unresolved:
                if f["severity"] == sev:
                    print(f"- {f['id']} [{f['severity']}/{f['dimension']}] "
                          f"{f['file']} — {f['title']} ({f['status']})")
    deferred = [f for f in findings if f["status"] == "deferred"]
    if deferred:
        print("\n**Deferred (needs a human decision):**")
        for f in deferred:
            print(f"- {f['id']} [{f['severity']}/{f['dimension']}] "
                  f"{f['file']} — {f['title']}: {f['note']}")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: repo_scan.py init|status|shard|mark|finding|report|clear ...")
        return 1
    root = common.project_dir({})
    cmd, rest = args[0], args[1:]
    if cmd == "init":
        return cmd_init(root, rest)
    if cmd == "baseline":
        return cmd_baseline(root, rest)
    if cmd == "status":
        return cmd_status(root, rest)
    if cmd == "shard":
        return cmd_shard(root, rest)
    if cmd == "mark":
        return cmd_mark(root, rest)
    if cmd == "finding":
        return cmd_finding(root, rest)
    if cmd == "report":
        return cmd_report(root, rest)
    if cmd == "clear":
        try:
            existing = common.read_state_strict(root, NAME)
        except Exception:
            existing = {"shards": "unreadable"}  # corrupt still needs --force
        if (existing.get("shards") or existing.get("findings")) and "--force" not in rest:
            print("praxis repo-scan: a ledger with recorded work exists — clearing "
                  "erases its coverage and findings. Re-run with 'clear --force'.")
            return 1
        common.write_state_strict(root, NAME, {})
        print("praxis repo-scan: ledger cleared.")
        return 0
    print(f"praxis repo-scan: unknown command '{cmd}'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
