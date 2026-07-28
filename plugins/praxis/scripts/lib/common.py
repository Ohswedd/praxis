"""
praxis shared helpers.

Design goals:
- Standard library only (no pip installs); runs anywhere Python 3.8+ exists.
- Never crash a Claude Code session: every public helper is defensive and
  fails open (returns a safe default) rather than raising.
- Offline-safe: no network calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Hook I/O
# --------------------------------------------------------------------------- #
def read_hook_input() -> Dict[str, Any]:
    """Read and parse the JSON object Claude Code sends on stdin.

    Returns an empty dict if stdin is empty or malformed so callers can
    proceed without special-casing.
    """
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def emit_context(text: str) -> None:
    """Print text destined for the model's context.

    For SessionStart hooks, plain stdout on exit 0 is
    injected into Claude's context. Output is capped by Claude Code (~10k
    chars); we truncate defensively.
    """
    if not text:
        return
    if len(text) > 9000:
        text = text[:9000] + "\n\n_(praxis: report truncated)_"
    sys.stdout.write(text)


def block(reason: str) -> None:
    """Block the current tool/turn (exit code 2) with a reason on stderr.

    For PreToolUse this denies the tool; for Stop it forces Claude to keep
    working. stderr is fed back to the model.
    """
    sys.stderr.write(reason.rstrip() + "\n")
    sys.exit(2)


def allow() -> None:
    """Explicitly allow / no-op (exit 0)."""
    sys.exit(0)


# --------------------------------------------------------------------------- #
# Repo / git helpers
# --------------------------------------------------------------------------- #
def project_dir(hook_input: Optional[Dict[str, Any]] = None) -> Path:
    """Best-effort project root.

    Priority: CLAUDE_PROJECT_DIR env -> hook 'cwd' -> git toplevel -> cwd.
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    if hook_input:
        cwd = hook_input.get("cwd")
        if cwd and Path(cwd).is_dir():
            return Path(cwd)
    top = _run(["git", "rev-parse", "--show-toplevel"])
    if top:
        p = Path(top.strip())
        if p.is_dir():
            return p
    return Path.cwd()


def _run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 10) -> str:
    """Run a command, returning stdout (stripped) or '' on any failure."""
    try:
        out = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return out.stdout if out.returncode == 0 else ""
    except Exception:
        return ""


def is_git_repo(root: Path) -> bool:
    return _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root).strip() == "true"


def git_default_branch(root: Path) -> str:
    """The integration branch PRs target.

    Config wins; otherwise infer from origin/HEAD, then fall back to whichever of
    main/master exists locally. Offline-safe, no network probe.
    """
    configured = read_config(root).get("git.default_branch")
    if configured:
        return str(configured)
    ref = _run(["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], cwd=root).strip()
    if ref:
        return ref.rsplit("/", 1)[-1]
    for candidate in ("main", "master"):
        if _run(["git", "rev-parse", "--verify", "--quiet", candidate], cwd=root).strip():
            return candidate
    return "main"


def git_status_porcelain(root: Path) -> List[str]:
    out = _run(["git", "status", "--porcelain"], cwd=root)
    return [ln for ln in out.splitlines() if ln.strip()]


def git_head(root: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], cwd=root).strip()


def working_tree_dirty(root: Path) -> bool:
    return len(git_status_porcelain(root)) > 0


def tracked_files(root: Path, limit: int = 5000, pathspec: str = "") -> List[str]:
    cmd = ["git", "ls-files"]
    if pathspec:
        cmd += ["--", pathspec]
    out = _run(cmd, cwd=root)
    files = [f for f in out.splitlines() if f.strip()]
    return files[:limit]


def untracked_files(root: Path, limit: int = 2000) -> List[str]:
    """New files git does not track yet, honouring .gitignore.

    A file created during a change is untracked until it is staged, so it appears
    in neither `git diff` nor `git diff --staged`. Any scanner that reads only
    those two is blind to brand-new files, which is exactly where unfinished work
    tends to land.
    """
    out = _run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root)
    files = [f for f in out.splitlines() if f.strip() and not _is_praxis_state(f)]
    return files[:limit]


def _is_praxis_state(path: str) -> bool:
    """True for praxis's own state files, which are never part of a change."""
    norm = path.replace("\\", "/").strip().strip('"')
    return norm.startswith(".claude/.praxis") or norm in (".claude", ".claude/")


# Files whose content is not reviewable text: scanning them yields noise, not signal.
_BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".icns", ".bmp", ".tiff",
    ".pdf", ".zip", ".gz", ".tar", ".bz2", ".xz", ".7z", ".jar", ".war",
    ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".mov", ".avi",
    ".wasm", ".so", ".dylib", ".dll", ".exe", ".bin", ".pyc", ".class",
}

# Generated dependency manifests: authored by a tool, so authoring rules do not
# apply and their size would swamp any real finding.
_LOCK_FILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock",
    "Cargo.lock", "Gemfile.lock", "composer.lock", "go.sum", "uv.lock",
}

MAX_SCAN_BYTES = 400_000


def is_scannable(root: Path, rel: str) -> bool:
    p = Path(rel)
    if p.suffix.lower() in _BINARY_SUFFIXES or p.name in _LOCK_FILES:
        return False
    try:
        return (root / rel).stat().st_size <= MAX_SCAN_BYTES
    except Exception:
        return False


# Total bytes of untracked content one scan will read. A repo that has not
# git-ignored its build output can list thousands of untracked files, and the
# scanners run inside a Stop hook with seconds to spare.
MAX_UNTRACKED_BYTES = 4_000_000


def added_line_pairs(root: Path) -> List[tuple]:
    """Every line the current change adds, as (file, lineno, text).

    The union of three sources, because a change is spread across all three and
    auditing only one of them under-reports: the unstaged diff, the staged diff,
    and the whole content of untracked files. Deduplicated, since a hunk edited
    after staging appears in both diffs.
    """
    seen = set()
    pairs: List[tuple] = []

    def add(fname, lineno, text):
        key = (fname, lineno, text)
        if key not in seen:
            seen.add(key)
            pairs.append(key)

    for extra in ([], ["--staged"]):
        diff = _run(["git", "diff", "--unified=0", "--no-color"] + extra, cwd=root, timeout=20)
        for fname, lineno, text in _parse_diff_added(diff):
            if fname and not _is_praxis_state(fname):
                add(fname, lineno, text)

    budget = MAX_UNTRACKED_BYTES
    for rel in untracked_files(root):
        if budget <= 0:
            break
        if not is_scannable(root, rel):
            continue
        try:
            body = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        budget -= len(body)
        for i, line in enumerate(body.splitlines(), 1):
            add(rel, i, line)
    return pairs


def _parse_diff_added(diff: str) -> List[tuple]:
    """(file, new-file lineno, text) for '+' lines in a unified=0 diff."""
    results: List[tuple] = []
    cur_file = None
    new_ln = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur_file = line[6:].strip()
        elif line.startswith("+++ "):
            cur_file = None          # /dev/null: a deletion has no added lines
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            new_ln = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            results.append((cur_file, new_ln, line[1:]))
            new_ln += 1
    return results


_CHANGED_FILES_CACHE: Dict[str, List[str]] = {}


def changed_files(root: Path) -> List[str]:
    """Repo-relative paths this change touches (modified, staged, or untracked).

    Memoised per process: the Stop gate asks the same question from four places
    in one run, and each answer costs three git invocations. A hook process is
    short-lived and never outlives the state it cached.
    """
    key = str(root)
    if key in _CHANGED_FILES_CACHE:
        return _CHANGED_FILES_CACHE[key]
    files = set()
    for extra in ([], ["--staged"]):
        out = _run(["git", "diff", "--name-only", "--no-color"] + extra, cwd=root, timeout=20)
        files.update(f.strip() for f in out.splitlines() if f.strip())
    files.update(untracked_files(root))
    result = sorted(f for f in files if f and not _is_praxis_state(f))
    _CHANGED_FILES_CACHE[key] = result
    return result


# --------------------------------------------------------------------------- #
# User-facing interface surface
# --------------------------------------------------------------------------- #
# Suffixes that are markup, styling, or component code: editing one changes what
# a user sees, so the accessibility and design-consistency verticals apply.
UI_SUFFIXES = {
    ".html", ".htm", ".xhtml", ".vue", ".svelte", ".astro", ".jsx", ".tsx",
    ".css", ".scss", ".sass", ".less", ".styl", ".pcss",
    ".njk", ".hbs", ".handlebars", ".ejs", ".pug", ".jade", ".liquid",
    ".erb", ".haml", ".slim", ".twig", ".mustache", ".razor", ".cshtml",
    ".mdx", ".swiftui", ".xaml",
}

# Filenames that configure the visual system even though their suffix is generic.
UI_FILENAME_RE = re.compile(
    r"(^|/)(tailwind\.config\.[a-z]+|postcss\.config\.[a-z]+|theme\.[a-z]+|"
    r"tokens\.[a-z]+|design-tokens\.[a-z]+|globals?\.[a-z]*css)$",
    re.IGNORECASE,
)

# The design artifacts the front-end pipeline writes; a change to them is design work.
UI_PATH_RE = re.compile(r"(^|/)docs/design/", re.IGNORECASE)


def is_ui_path(path: str) -> bool:
    if not path:
        return False
    norm = path.replace("\\", "/")
    if Path(norm).suffix.lower() in UI_SUFFIXES:
        return True
    return bool(UI_FILENAME_RE.search(norm) or UI_PATH_RE.search(norm))


def ui_files_in_change(root: Path) -> List[str]:
    """Files in the current change that render or style user-facing surface."""
    return [f for f in changed_files(root) if is_ui_path(f)]


#: The verticals a user-facing change cannot be green without. The report writer
#: and the Stop gate both enforce this, so the list lives here once.
UI_VERTICALS = ("accessibility", "design-consistency")


def missing_ui_verticals(root: Path, verticals: Dict[str, Any]) -> List[str]:
    """UI verdicts this change owes but `verticals` does not carry.

    Empty when the change touches no user-facing surface, or when the repo has
    turned the requirement off with `require_ui_verticals = false`.
    """
    if not read_config(root).get("gate.require_ui_verticals", True):
        return []
    if not ui_files_in_change(root):
        return []
    recorded = verticals if isinstance(verticals, dict) else {}
    return [v for v in UI_VERTICALS if recorded.get(v) != "pass"]


def detect_test_command(root: Path) -> str:
    """Best-effort primary test command for a repo (empty if none found)."""
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            if "test" in pkg.get("scripts", {}):
                return "npm test"
        except Exception:
            pass
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists() \
            or (root / "tox.ini").exists():
        return "pytest"
    if (root / "go.mod").exists():
        return "go test ./..."
    if (root / "Cargo.toml").exists():
        return "cargo test"
    if (root / "Gemfile").exists():
        return "bundle exec rspec"
    if (root / "Makefile").exists():
        try:
            if re.search(r"^test:", (root / "Makefile").read_text(encoding="utf-8", errors="ignore"),
                         re.MULTILINE):
                return "make test"
        except Exception:
            pass
    return ""


# Workspace / monorepo markers: (kind, detector)
def detect_workspaces(root: Path, limit: int = 200) -> List[Dict[str, str]]:
    """Detect sub-packages in a monorepo. Returns [{path, kind}], root-relative.

    Recognises Node (package.json workspaces / pnpm / lerna / turbo / nx),
    Cargo workspaces, Go multi-module, and Python multi-project layouts.
    Best-effort and shallow; returns [] for a single-package repo.
    """
    pkgs: List[Dict[str, str]] = []
    seen = set()

    def add(rel: str, kind: str):
        rel = rel.strip("/") or "."
        if rel not in seen:
            seen.add(rel)
            pkgs.append({"path": rel, "kind": kind})

    # One pruned walk collects every marker file, instead of four separate walks.
    markers = find_files_multi(
        root, {"package.json", "Cargo.toml", "go.mod", "pyproject.toml"}, limit=limit)

    # Node workspaces
    pj = root / "package.json"
    is_node_ws = False
    if pj.exists():
        try:
            is_node_ws = bool(json.loads(pj.read_text(encoding="utf-8")).get("workspaces"))
        except Exception:
            pass
    if is_node_ws or (root / "pnpm-workspace.yaml").exists() \
            or (root / "lerna.json").exists() or (root / "turbo.json").exists() \
            or (root / "nx.json").exists():
        for p in markers.get("package.json", []):
            if p != pj:
                add(str(p.parent.relative_to(root)), "node")

    # Cargo workspace
    cargo = root / "Cargo.toml"
    if cargo.exists():
        try:
            if "[workspace]" in cargo.read_text(encoding="utf-8", errors="ignore"):
                for p in markers.get("Cargo.toml", []):
                    if p != cargo:
                        add(str(p.parent.relative_to(root)), "cargo")
        except Exception:
            pass

    # Go multi-module
    gomods = markers.get("go.mod", [])
    if len(gomods) > 1:
        for p in gomods:
            add(str(p.parent.relative_to(root)), "go")

    # Python multi-project
    pyprojs = markers.get("pyproject.toml", [])
    if len(pyprojs) > 1:
        for p in pyprojs:
            add(str(p.parent.relative_to(root)), "python")

    return pkgs


# Directories that are noise/huge and should never be traversed.
PRUNE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "vendor", "target",
    "dist", "build", ".next", "__pycache__", ".mypy_cache", ".pytest_cache",
    "site-packages", ".terraform", "coverage", ".gradle", ".idea", ".cache",
    "bower_components", ".svn", ".hg", "out", "bin", "obj",
}


def _pruned_walk(root: Path, max_dirs: int = 20000):
    """Yield (dirpath, filenames) walking `root`, pruning heavy/noise dirs."""
    visited = 0
    for dirpath, dirnames, filenames in os.walk(root):
        visited += 1
        if visited > max_dirs:
            break
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS and not d.startswith(".praxis")]
        yield dirpath, filenames


def find_files(root: Path, name: str, limit: int = 500, max_dirs: int = 20000) -> List[Path]:
    """Find files named `name`, pruning heavy/noise directories.

    Uses os.walk with in-place dir pruning so huge trees (node_modules, .git,
    build outputs) are never descended: keeping SessionStart fast on large,
    enterprise repos. Bounded by `limit` results and `max_dirs` visited.
    """
    found: List[Path] = []
    for dirpath, filenames in _pruned_walk(root, max_dirs):
        if name in filenames:
            found.append(Path(dirpath) / name)
            if len(found) >= limit:
                break
    return found


def walk_files(root: Path, limit: int = 20000, max_dirs: int = 20000):
    """(relative sorted file paths, dir_cap_hit) under `root`, pruning noise dirs.

    The non-git counterpart of `git ls-files`, used by the repo-scan inventory.
    The boolean reports whether the walk stopped at `max_dirs`: a caller that
    claims coverage (the scan ledger) must treat that as truncation, never as a
    complete listing.
    """
    found: List[str] = []
    visited = 0
    for dirpath, dirnames, filenames in os.walk(root):
        visited += 1
        if visited > max_dirs:
            return sorted(found), True
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS and not d.startswith(".praxis")]
        for name in filenames:
            try:
                found.append(os.path.relpath(os.path.join(dirpath, name), root))
            except Exception:
                continue
            if len(found) >= limit:
                return sorted(found), False
    return sorted(found), False


def list_files(root: Path, limit: int = 20000, max_dirs: int = 20000) -> List[str]:
    """walk_files for callers that don't need the truncation signal."""
    return walk_files(root, limit, max_dirs)[0]


def find_files_multi(root: Path, names: set, limit: int = 500,
                     max_dirs: int = 20000) -> Dict[str, List[Path]]:
    """Like find_files but collects several filenames in a single pruned walk."""
    out: Dict[str, List[Path]] = {n: [] for n in names}
    total = 0
    for dirpath, filenames in _pruned_walk(root, max_dirs):
        for n in names:
            if n in filenames:
                out[n].append(Path(dirpath) / n)
                total += 1
        if total >= limit * max(1, len(names)):
            break
    return out



# --------------------------------------------------------------------------- #
# praxis state directory (per-project, git-ignored)
# --------------------------------------------------------------------------- #
def state_dir(root: Path) -> Path:
    d = root / ".claude" / ".praxis"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def read_state(root: Path, name: str) -> Dict[str, Any]:
    try:
        return read_state_strict(root, name)
    except Exception:
        return {}


def read_state_strict(root: Path, name: str) -> Dict[str, Any]:
    """Like read_state, but distinguishes 'missing' ({}) from 'corrupt' (raises).

    Hooks want the forgiving variant; the scan ledger must not mistake a
    damaged file for an empty one (init would then clobber a real scan).
    """
    f = state_dir(root) / name
    if not f.exists():
        return {}
    data = json.loads(f.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_state(root: Path, name: str, data: Dict[str, Any]) -> None:
    try:
        write_state_strict(root, name, data)
    except Exception:
        pass


def write_state_strict(root: Path, name: str, data: Dict[str, Any]) -> None:
    """Atomic state write (temp file + os.replace) that propagates failure.

    Atomic so a crash mid-write can never corrupt existing state; strict so a
    caller that must not lie about persistence (the scan ledger) fails loudly
    instead of reporting success with nothing on disk. Hook callers use the
    fail-open write_state wrapper instead.
    """
    f = state_dir(root) / name
    tmp = f.with_name(f.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, f)
    except Exception:
        try:
            tmp.unlink()
        except Exception:
            pass
        raise


def run_scanner(script: str, root: Path, timeout: int = 25) -> List[Dict[str, Any]]:
    """Findings from a sibling `--json` scanner (empty list on any failure).

    Every praxis scanner takes `--json` and prints `{"count": n, "findings": [...]}`,
    so the hooks that consume them share one runner. Failing open is deliberate:
    a scanner that crashes must never wedge a session or a Stop gate.
    """
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), script)
        out = subprocess.run(
            [sys.executable, path, "--json"],
            capture_output=True, text=True, timeout=timeout, cwd=str(root),
        )
        findings = json.loads(out.stdout or "{}").get("findings", [])
        return findings if isinstance(findings, list) else []
    except Exception:
        return []


def cli_opt(args: List[str], name: str, default=None):
    """Value following `name` in a hand-parsed argv list (praxis CLI idiom)."""
    if name in args and args.index(name) + 1 < len(args):
        return args[args.index(name) + 1]
    return default


def autopilot_on(root: Path) -> bool:
    """True if auto-pilot is enabled (env PRAXIS_AUTOPILOT or the toggle file).

    In auto-pilot praxis does not ask the user design/approach questions; it
    decides by best-practice and logs the decision instead.
    """
    if os.environ.get("PRAXIS_AUTOPILOT", "").lower() in ("on", "1", "true"):
        return True
    if (state_dir(root) / "autopilot").exists():
        return True
    return bool(read_config(root).get("autopilot.default", False))


def auto_merge_on(root: Path) -> bool:
    """True if autonomous review-and-merge is enabled (env, toggle file, or config).

    When on, praxis may merge its own PRs after a green audit. When off (default),
    it opens the PR and stops for a human to review and merge.
    """
    if os.environ.get("PRAXIS_AUTO_MERGE", "").lower() in ("on", "1", "true"):
        return True
    if (state_dir(root) / "auto-merge").exists():
        return True
    return bool(read_config(root).get("git.auto_merge", False))


_CONFIG_DEFAULTS = {
    "gate.enabled": True,             # master switch for the Stop gate
    "gate.require_tests": True,       # require passing test evidence in the green report
    "gate.require_ui_verticals": True,  # UI diffs need the a11y + design verdicts
    "autopilot.default": False,       # start sessions in auto-pilot
    "audit.depth": "high",            # informational hint for the auditors
    "git.auto_merge": False,          # auto-review and merge PRs; off = PR only, human merges
    "git.default_branch": "",         # PR base branch ("" = auto-detect)
    "style.ban_em_dash": True,        # refuse em dashes in authored text
    "style.ban_ai_attribution": True,  # refuse AI co-author / generated-by credits
}


def _coerce(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(v)
    except ValueError:
        return v


def read_config(root: Path) -> Dict[str, Any]:
    """Read `.praxis.toml` (a small, flat subset: [section] + key = value).

    Stdlib-only (works on 3.8+; no tomllib dependency). Returns defaults merged
    with any values found; unknown keys are ignored; malformed files fall back to
    defaults rather than raising.
    """
    cfg = dict(_CONFIG_DEFAULTS)
    f = root / ".praxis.toml"
    if not f.exists():
        return cfg
    try:
        section = ""
        for raw in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip()
                continue
            if "=" in line:
                k, _, val = line.partition("=")
                key = f"{section}.{k.strip()}" if section else k.strip()
                if key in _CONFIG_DEFAULTS:
                    cfg[key] = _coerce(val)
    except Exception:
        return dict(_CONFIG_DEFAULTS)
    return cfg


def change_signature(root: Path) -> str:
    """A stable hash of the current change set (HEAD + dirty file list + sizes).

    Used to key the quality-gate: a green audit is valid only for the exact
    state it was produced against. Recomputed on every call (two git
    subprocesses); callers that need it more than once should hold the value.
    """
    parts = [git_head(root)]
    for ln in git_status_porcelain(root):
        # Praxis's own state dir must never affect the code-change signature,
        # even when the repo hasn't git-ignored it yet.
        path_part = ln[3:].strip().strip('"')
        if _is_praxis_state(path_part):
            continue
        parts.append(ln)
        # include mtime/size so edits to the same path re-key the signature
        path = path_part
        fp = root / path
        try:
            st = fp.stat()
            parts.append(f"{path}:{st.st_size}:{int(st.st_mtime)}")
        except Exception:
            parts.append(f"{path}:missing")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


# --------------------------------------------------------------------------- #
# Sensitive-path / secret detection
# --------------------------------------------------------------------------- #
SENSITIVE_PATH_PATTERNS = [
    r"(^|/)\.env($|\.|/)",
    r"(^|/)\.env\.[a-z]+$",
    r"\.pem$",
    r"\.key$",
    r"(^|/)id_rsa($|\.)",
    r"(^|/)id_ed25519($|\.)",
    r"(^|/)\.npmrc$",
    r"(^|/)\.pypirc$",
    r"(^|/)\.aws/credentials",
    r"(^|/)\.ssh/",
    r"(^|/)secrets?\.(ya?ml|json|toml)$",
    r"(^|/)credentials(\.json)?$",
    r"(^|/)serviceaccount.*\.json$",
]

_SENSITIVE_RE = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATH_PATTERNS]

# Allow reading obvious templates/examples.
_SENSITIVE_ALLOW_RE = re.compile(
    r"(\.env\.(example|sample|template|dist)$)|(\.example$)|(\.sample$)", re.IGNORECASE
)


def is_sensitive_path(path: str) -> bool:
    if not path:
        return False
    norm = path.replace("\\", "/")
    if _SENSITIVE_ALLOW_RE.search(norm):
        return False
    return any(rx.search(norm) for rx in _SENSITIVE_RE)


# Secret content signatures (high-signal, low false-positive).
SECRET_CONTENT_PATTERNS = {
    "AWS access key id": r"AKIA[0-9A-Z]{16}",
    "AWS secret access key": r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}",
    "Private key block": r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
    "Google API key": r"AIza[0-9A-Za-z_\-]{35}",
    "Slack token": r"xox[baprs]-[0-9A-Za-z-]{10,}",
    "GitHub token": r"gh[pousr]_[0-9A-Za-z]{36,}",
    "Generic bearer secret": r"(?i)(api[_-]?key|secret|token|passwd|password)\s*[=:]\s*['\"][^'\"\s]{16,}['\"]",
    "Stripe live key": r"sk_live_[0-9A-Za-z]{16,}",
}

_SECRET_RE = {name: re.compile(pat) for name, pat in SECRET_CONTENT_PATTERNS.items()}


def scan_secrets_in_text(text: str) -> List[str]:
    findings = []
    for name, rx in _SECRET_RE.items():
        if rx.search(text):
            findings.append(name)
    return findings


def scan_file_for_secrets(fp: Path, max_bytes: int = MAX_SCAN_BYTES) -> List[str]:
    try:
        if fp.stat().st_size > max_bytes:
            return []
        text = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return scan_secrets_in_text(text)


# --------------------------------------------------------------------------- #
# House style: AI attribution and banned typography
# --------------------------------------------------------------------------- #
# Credits that hand a project's authorship to the tool that typed it. The history,
# the pull request, and the release notes belong to the project; a co-author
# trailer or a "generated with" footer is noise the maintainers did not ask for.
# Naming the platform ("praxis is a Claude Code plugin") is description, not
# attribution, so only the credit shapes below are matched.
AI_ATTRIBUTION_PATTERNS = {
    "AI co-author trailer": r"(?i)co[-\s]?authored[-\s]?by:\s*[^\n]*\b("
                            r"claude|anthropic|copilot|chatgpt|openai|gpt-|gemini|"
                            r"cursor|codex|devin|noreply@anthropic\.com)",
    # A credit, not a mention. Two shapes: the footer, which sits at the start of
    # its own line (optionally behind an emoji, a bullet, or a comment marker),
    # and the inline form, which is only matched when the vendor is named as a
    # product ("Claude Code", "Claude Opus") or linked. Without that qualifier a
    # sentence like "handle files created by claude sessions" would block the one
    # command a user cannot cheaply retry.
    "generated-by credit": r"(?im)(^[\s>*_#/-]*[\U0001F300-\U0001FAFF\s]*"
                           r"(generated|written|created|authored|co[-\s]?written)\s+"
                           r"(with|by|using)\s+\[?\s*"
                           r"(claude|anthropic|chatgpt|openai|copilot|gemini|cursor|codex)\b"
                           r"|(generated|written|created|authored|co[-\s]?written)\s+"
                           r"(with|by|using)\s+\[?\s*"
                           r"(claude\s*(code|opus|sonnet|haiku|ai)\b|anthropic\b|chatgpt\b|"
                           r"openai\b|copilot\b|codex\b|"
                           r"claude\.(ai|com)|anthropic\.com|openai\.com))",
    "AI assistance footer": r"(?im)^[\s>*_#/-]*[\U0001F300-\U0001FAFF\s]*"
                            r"(with\s+(help|assistance)\s+from|powered\s+by)\s+"
                            r"(claude|chatgpt|copilot|gemini)\b",
    "robot attribution emoji": r"(?i)\U0001F916\s*(generated|created|made|built|with|by)",
}

_AI_ATTRIBUTION_RE = {n: re.compile(p) for n, p in AI_ATTRIBUTION_PATTERNS.items()}


#: The one escape hatch every praxis scanner honours, and part of the stable
#: public surface: a line carrying it is exempt from the placeholder scan, the
#: house-style scan, and the drift check alike. It lives here so the three cannot
#: drift apart on what the annotation looks like.
ACK_RE = re.compile(r"praxis:ack\b")


def is_acked(text: str) -> bool:
    """True if this line records a deliberate, accepted exception."""
    return bool(text) and bool(ACK_RE.search(text))


def scan_ai_attribution(text: str) -> List[str]:
    """Names of the AI-attribution shapes present in `text` (empty if none)."""
    if not text:
        return []
    return [name for name, rx in _AI_ATTRIBUTION_RE.items() if rx.search(text)]


# Dashes praxis does not author. Built from code points rather than literals so
# this module, the scanners that import it, and the tests can all be searched for
# a stray dash without matching the definition itself.
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
HORIZONTAL_BAR = chr(0x2015)

# The em dash and its look-alikes are banned outright: as a sentence break they
# are the single most recognisable tell of unedited generated prose, and a colon,
# a comma, parentheses, or a full stop always says the same thing more precisely.
# The en dash is banned only when spaced as a sentence dash; between numbers it is
# correct typography for a range and is left alone. The ASCII "--" is deliberately
# not matched: in a repository it is far more often a command-line separator
# (`git ls-files -- path`, `npm test -- --watch`) than a punctuation mark.
BANNED_DASH_PATTERNS = {
    "em dash": f"[{EM_DASH}{HORIZONTAL_BAR}]",
    "spaced en dash": rf"(?<=\s){EN_DASH}(?=\s)",
}

_BANNED_DASH_RE = {n: re.compile(p) for n, p in BANNED_DASH_PATTERNS.items()}


def scan_banned_dashes(text: str) -> List[str]:
    """Names of the banned dash forms present in `text` (empty if none)."""
    if not text:
        return []
    return [name for name, rx in _BANNED_DASH_RE.items() if rx.search(text)]
