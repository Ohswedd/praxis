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


def _run_out(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 10) -> tuple:
    """(stdout, ok) where `ok` is False if the command did not answer at all.

    `_run` collapses "ran cleanly and printed nothing" and "timed out" into the
    same empty string. Most callers can treat those alike; the workspace detector
    cannot, because reading a timeout as "no commits by you" would move a user's
    own project into contributor mode.
    """
    try:
        out = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                             capture_output=True, text=True, timeout=timeout)
        return (out.stdout, True) if out.returncode == 0 else ("", False)
    except Exception:
        return "", False


def _run_ok(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 10) -> bool:
    """True if `cmd` exits 0. For plumbing whose answer IS the exit code.

    `_run` cannot express this: it returns '' both for a clean run with no output
    and for a failure, which is exactly the pair `git check-ignore -q` needs to
    distinguish.
    """
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
        ).returncode == 0
    except Exception:
        return False


def is_git_repo(root: Path) -> bool:
    return _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root).strip() == "true"


def git_dir(root: Path) -> Optional[Path]:
    """The directory whose `info/exclude` git actually reads, or None outside a repo.

    `--git-common-dir`, not `--git-dir`. gitignore(5) is explicit that per-clone
    patterns live in `$GIT_COMMON_DIR/info/exclude`, and in a linked worktree the
    two differ: `--absolute-git-dir` answers `.git/worktrees/<name>`, whose
    `info/exclude` git never consults. Writing there produces the worst possible
    outcome for contributor mode, an exclusion that reports success and does
    nothing, so the common dir is asked for first and the older flags are only a
    fallback for git before 2.5.
    """
    for args in (["--git-common-dir"], ["--absolute-git-dir"], ["--git-dir"]):
        out = _run(["git", "rev-parse"] + args, cwd=root).strip()
        if not out:
            continue
        # --git-common-dir and --git-dir may answer relatively; resolve against
        # the working tree they were asked about.
        p = Path(out) if os.path.isabs(out) else (root / out)
        try:
            if p.is_dir():
                return p.resolve()
        except Exception:
            continue
    return None


def git_is_ignored(root: Path, rel: str) -> bool:
    """True if git would ignore `rel`, whatever the source of the rule.

    Asks git instead of reading `.gitignore`, so `.git/info/exclude` and a global
    `core.excludesFile` count exactly as much as a committed rule. That matters
    for contributor mode, where the only correct place for praxis's patterns is
    the per-clone exclude file.
    """
    return _run_ok(["git", "check-ignore", "-q", rel], cwd=root)


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


# --------------------------------------------------------------------------- #
# Review scope: the branch, not just the working tree
# --------------------------------------------------------------------------- #
# praxis used to define "the change" as the working tree: unstaged diff, staged
# diff, untracked files. That definition has a hole that gets wider the better
# the delivery discipline gets. The moment work is committed, `git diff` is
# empty, the tree is clean, and every consumer goes blind: the scanners find
# nothing, the auditors review nothing, and the Stop gate opens.
#
# One commit is all it takes, so a task delivered as a series of commits (which
# is the point of one-commit-per-subtask) would switch the entire audit off. The
# scope is therefore the whole branch: every commit since it left its base, plus
# whatever is still uncommitted.
_MERGE_BASE_CACHE: Dict[str, Optional[str]] = {}

#: Commits inspected when describing the branch. A review scope larger than this
#: is not a change under review, it is a history.
MAX_BRANCH_COMMITS = 200


def current_branch(root: Path) -> str:
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root).strip()


def review_base(root: Path) -> Optional[str]:
    """The commit this branch's work should be reviewed against, or None.

    None means "there is no branch range here": praxis is on the integration
    branch itself, or the base cannot be resolved. Callers then fall back to the
    working tree alone, which is exactly the pre-3.1 behaviour, so a repo that
    never branches sees no change at all.
    """
    key = str(root)
    if key in _MERGE_BASE_CACHE:
        return _MERGE_BASE_CACHE[key]
    _MERGE_BASE_CACHE[key] = base = _review_base(root)
    return base


def _review_base(root: Path) -> Optional[str]:
    if not is_git_repo(root):
        return None
    default = git_default_branch(root)
    branch = current_branch(root)
    # On the integration branch there is nothing to compare against: its commits
    # are history, not a change awaiting review.
    if not branch or branch == "HEAD" or branch == default:
        return None
    for ref in (f"origin/{default}", default):
        if not _run(["git", "rev-parse", "--verify", "--quiet", ref], cwd=root).strip():
            continue
        base = _run(["git", "merge-base", ref, "HEAD"], cwd=root).strip()
        if base:
            head = git_head(root)
            # A branch that has not diverged yet has nothing committed to review.
            return None if base == head else base
    return None


def branch_commits(root: Path) -> List[str]:
    """`<sha> <subject>` for each commit on this branch, newest first."""
    base = review_base(root)
    if not base:
        return []
    out = _run(["git", "log", f"-n{MAX_BRANCH_COMMITS}", "--format=%h %s",
                f"{base}..HEAD"], cwd=root, timeout=20)
    return [ln for ln in out.splitlines() if ln.strip()]


def committed_files(root: Path) -> List[str]:
    """Files this branch has already committed, relative to its base."""
    base = review_base(root)
    if not base:
        return []
    out = _run(["git", "diff", "--name-only", "--no-color", f"{base}...HEAD"],
               cwd=root, timeout=20)
    return [f.strip() for f in out.splitlines()
            if f.strip() and not _is_praxis_state(f.strip())]


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
    """True for praxis's own files, which are never part of the user's change.

    Covers every local artifact, not just the state directory. The exclusion in
    `$GIT_COMMON_DIR/info/exclude` normally keeps these out of git's answers
    entirely, but it fails open (a read-only `.git`, a clone that predates
    praxis), and when it does, `CLAUDE.local.md` would otherwise count as an
    unreviewed change: the Stop gate would see a permanently dirty tree and the
    scanners would audit praxis's own brief.
    """
    norm = path.replace("\\", "/").strip().strip('"')
    # A prefix, not a character set: lstrip("./") would eat the leading dot of
    # `.claude` and turn every artifact path into a miss.
    while norm.startswith("./"):
        norm = norm[2:]
    if norm in (".claude", ".claude/"):
        return True
    return any(norm == a.rstrip("/") or norm.startswith(a if a.endswith("/") else a + "/")
               for a in LOCAL_ARTIFACTS)


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

    The union of four sources, because a change is spread across all of them and
    auditing only one under-reports: what this branch has committed since it left
    its base, the unstaged diff, the staged diff, and the whole content of
    untracked files. Deduplicated, since a hunk that is committed and then edited
    again appears more than once.
    """
    seen = set()
    pairs: List[tuple] = []

    def add(fname, lineno, text):
        key = (fname, lineno, text)
        if key not in seen:
            seen.add(key)
            pairs.append(key)

    ranges = []
    base = review_base(root)
    if base:
        ranges.append([f"{base}...HEAD"])
    for extra in ranges + [[], ["--staged"]]:
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
    """Repo-relative paths this change touches: committed on the branch, modified,
    staged, or untracked.

    Committed files are included because a change does not stop being a change by
    being committed. Without them, delivering a task as one commit per subtask
    would empty this list, and everything keyed on it (the UI verticals, the
    scanners, the gate) would silently pass.

    Memoised per process: the Stop gate asks the same question from four places
    in one run, and each answer costs several git invocations. A hook process is
    short-lived and never outlives the state it cached.
    """
    key = str(root)
    if key in _CHANGED_FILES_CACHE:
        return _CHANGED_FILES_CACHE[key]
    files = set(committed_files(root))
    for extra in ([], ["--staged"]):
        out = _run(["git", "diff", "--name-only", "--no-color"] + extra, cwd=root, timeout=20)
        files.update(f.strip() for f in out.splitlines() if f.strip())
    files.update(untracked_files(root))
    result = sorted(f for f in files if f and not _is_praxis_state(f))
    _CHANGED_FILES_CACHE[key] = result
    return result


def review_pending(root: Path) -> bool:
    """True if there is anything to review: uncommitted work, or branch commits.

    The Stop gate's old question was "is the tree dirty". That answered yes to
    unfinished work and no to finished-and-committed work, which is precisely
    backwards for a gate whose job is to see a change before it becomes a pull
    request.
    """
    return bool(working_tree_dirty(root) or committed_files(root))


# --------------------------------------------------------------------------- #
# Workspace mode: whose repository is this?
# --------------------------------------------------------------------------- #
# praxis writes real files into a project: an operating brief, settings, a /docs
# tree, a changelog, ADRs. In your own repository that is the point. In a
# repository you merely contribute to, every one of them is a file the project
# never asked for, one `git add -A` away from a polluted pull request.
#
# So praxis resolves whose repo it is, and in `contributor` mode keeps everything
# it authors on the machine: the locations Claude Code documents for local,
# uncommitted configuration (`CLAUDE.local.md`, `.claude/settings.local.json`),
# plus its own already-local state directory.
OWNER = "owner"
CONTRIBUTOR = "contributor"
AUTO = "auto"
#: Detection ran and could not answer (git failed or timed out). Distinct from
#: `owner`, because "I could not tell" is not evidence that the repo is yours.
UNKNOWN = "unknown"

#: Toggle file holding the chosen mode. Three states are needed (owner,
#: contributor, and "let praxis decide"), so unlike the boolean switches this one
#: records its value rather than its existence.
WORKSPACE_TOGGLE = "workspace"

#: Below this, a repository is too young for its authorship to mean anything: a
#: repo you started yesterday has almost no history to find yourself in.
MIN_HISTORY_FOR_DETECTION = 20

#: Commits inspected when looking for the local author. Bounded because this runs
#: in a SessionStart budget, and an author who has never appeared in the last few
#: hundred commits is not the person maintaining the project.
AUTHOR_SCAN_DEPTH = 500

#: Wall-clock ceiling for the author scan. It has to stay comfortably inside the
#: UserPromptSubmit hook budget (15s), because the prompt router resolves the mode
#: on every actionable prompt and a hook that overruns is a hook that is killed.
AUTHOR_SCAN_TIMEOUT = 5

_DETECTED_MODE_CACHE: Dict[str, tuple] = {}


def _detect_workspace_mode(root: Path) -> tuple:
    """(mode, reason) inferred from git alone. Never touches the network.

    The question "is this repository mine?" has one cheap, honest proxy: whether
    the person configured to commit here has ever actually committed here. A repo
    with a remote, real history, and not one commit from your address is somebody
    else's project that you have cloned.

    Every uncertain case resolves to `owner`, because `owner` is the behaviour
    praxis has always had; a wrong `contributor` verdict would silently withhold
    the setup a user expected in their own project. The one exception is a git
    call that fails or times out rather than answering: "I could not tell" is not
    evidence of ownership, so it is reported as its own state and the caller
    keeps whatever verdict it had.
    """
    if not is_git_repo(root):
        return OWNER, "not a git repository"
    remotes, ok = _run_out(["git", "remote"], cwd=root)
    if not ok:
        return UNKNOWN, "git could not be read here"
    if not remotes.strip():
        return OWNER, "no git remote, so nothing to contribute to"
    email = _run(["git", "config", "user.email"], cwd=root).strip()
    if not email:
        return OWNER, "no git user.email is configured, so authorship cannot be read"

    # Bounded: the only question is "at least MIN_HISTORY_FOR_DETECTION?", and an
    # unbounded rev-list walks the whole history of a repo that may have a million
    # commits, inside a hook budget measured in seconds.
    count, ok = _run_out(["git", "rev-list", "--count",
                          f"--max-count={MIN_HISTORY_FOR_DETECTION}", "HEAD"], cwd=root)
    if not ok:
        return UNKNOWN, "git could not count this repository's history"
    commits = int(count.strip()) if count.strip().isdigit() else 0
    # A shallow clone reports only the commits it fetched, so its count says
    # nothing about the project's age and must not be read as "young repo".
    shallow = _run(["git", "rev-parse", "--is-shallow-repository"],
                   cwd=root).strip() == "true"
    if not shallow and commits < MIN_HISTORY_FOR_DETECTION:
        return OWNER, f"only {commits} commit(s) of history"

    log, ok = _run_out(["git", "log", f"-n{AUTHOR_SCAN_DEPTH}", "--format=%ae"],
                       cwd=root, timeout=AUTHOR_SCAN_TIMEOUT)
    if not ok:
        # Without this, a timed-out author scan reads as "your address appears
        # nowhere", which is the harmful direction: it would relocate praxis's
        # files in a repository that is in fact yours.
        return UNKNOWN, "the author scan did not complete"
    authors = log.lower().split()
    if email.lower() in authors:
        return OWNER, "you have commits in this repository"
    return CONTRIBUTOR, (f"a remote, {len(authors)} commit(s) examined, none "
                         f"authored by {email}")


def _detected_mode(root: Path) -> tuple:
    """`_detect_workspace_mode` memoised per root (it costs five git calls).

    Only the *detection* is cached, never the resolved mode: a toggle flipped
    mid-session must take effect on the next call, while a repository's authorship
    cannot meaningfully change inside one hook process.
    """
    key = str(root)
    if key not in _DETECTED_MODE_CACHE:
        try:
            _DETECTED_MODE_CACHE[key] = _detect_workspace_mode(root)
        except Exception:
            _DETECTED_MODE_CACHE[key] = (OWNER, "detection failed")
    return _DETECTED_MODE_CACHE[key]


def workspace_mode_reason(root: Path) -> tuple:
    """(mode, source) in force here, most specific source first.

    env PRAXIS_MODE -> .claude/.praxis/workspace -> .praxis.toml -> detection.
    The source is returned with the value so a surprising verdict can always be
    traced to the thing that produced it.

    One asymmetry, and it is a trust boundary rather than a preference: a
    *committed* `.praxis.toml` belongs to the repository, and a repository does
    not get to tell praxis that it is ours. It may declare `contributor`, which
    only ever withholds writes, and its `owner` is ignored in favour of
    detection. Local sources (the env var, the toggle, the git-excluded config)
    are the user's own and may say either.
    """
    env = os.environ.get("PRAXIS_MODE", "").strip().lower()
    if env in (OWNER, CONTRIBUTOR):
        return env, f"env PRAXIS_MODE={env}"

    try:
        toggle = state_path(root, WORKSPACE_TOGGLE).read_text(
            encoding="utf-8").strip().lower()
    except Exception:
        toggle = ""
    if toggle in (OWNER, CONTRIBUTOR):
        return toggle, f".claude/.praxis/{WORKSPACE_TOGGLE}"

    cfg, sources = read_config_sources(root)
    configured = str(cfg.get("workspace.mode", AUTO)).strip().lower()
    layer = sources.get("workspace.mode", "")
    if configured in (OWNER, CONTRIBUTOR):
        if configured == CONTRIBUTOR or layer != ".praxis.toml":
            return configured, f"{layer} [workspace] mode"
        # A committed `owner` is the one value a cloned repo could use to make
        # praxis treat it as ours. Say so rather than silently ignoring it.
        mode, why = _detected_mode(root)
        if mode != UNKNOWN:
            return mode, (f"detected: {why} (the committed .praxis.toml asks for "
                          "owner; only a local setting may grant that)")

    mode, why = _detected_mode(root)
    if mode == UNKNOWN:
        # Detection could not answer. Keep praxis's historical behaviour rather
        # than guessing, but do not dress the guess up as a finding.
        return OWNER, f"undetermined ({why}), defaulting to owner"
    return mode, f"detected: {why}"


def persist_workspace_mode(root: Path, mode: str) -> bool:
    """Pin a detected mode so a later commit of your own cannot flip it.

    This exists for one specific, entirely normal sequence: you clone someone's
    project (detected `contributor`), praxis sets up locally, you fix the bug and
    commit it. On the next session your address is in `git log`, detection says
    `owner`, and praxis would start writing a CLAUDE.md and a /docs tree into
    their repository, with nothing excluding any of it. Pinning the verdict the
    first time it is reached makes the contribution workflow safe.

    Only `contributor` is pinned. `owner` is the default and needs no memory, and
    pinning it would be the direction that causes harm when wrong.
    """
    if mode != CONTRIBUTOR:
        return False
    target = state_dir(root) / WORKSPACE_TOGGLE
    if target.exists():
        return False
    try:
        target.write_text(mode + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def workspace_mode(root: Path) -> str:
    return workspace_mode_reason(root)[0]


def is_contributor(root: Path) -> bool:
    """True when praxis must leave no trace in the repository itself."""
    try:
        return workspace_mode(root) == CONTRIBUTOR
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Where praxis writes, per mode
# --------------------------------------------------------------------------- #
#: Everything praxis authors that belongs to the machine rather than to the
#: project. Committing any of these is wrong in either mode, so the guard and the
#: exclude block both read this one list.
LOCAL_ARTIFACTS = (
    ".claude/.praxis/",
    ".claude/settings.local.json",
    "CLAUDE.local.md",
)

#: Local knowledge root, under the state directory so it inherits its exclusion.
#: It mirrors the repo layout (`docs/`, `docs/adr/`, `CHANGELOG.md`) so a skill's
#: instructions differ only in where the tree is rooted.
KNOWLEDGE_DIR = "knowledge"


def brief_path(root: Path) -> Path:
    """The operating brief praxis maintains.

    In contributor mode this is `CLAUDE.local.md`, which Claude Code loads
    alongside the project's own `CLAUDE.md` and appends after it. praxis therefore
    adds its brief without editing, replacing, or reconciling a file the project
    owns.
    """
    return root / ("CLAUDE.local.md" if is_contributor(root) else "CLAUDE.md")


def settings_path(root: Path) -> Path:
    """The settings file praxis proposes: the local one when the repo is not ours."""
    name = "settings.local.json" if is_contributor(root) else "settings.json"
    return root / ".claude" / name


def knowledge_root(root: Path) -> Path:
    return (state_dir(root) / KNOWLEDGE_DIR) if is_contributor(root) else root


def staged_local_artifacts(root: Path) -> List[str]:
    """praxis artifacts currently in the index, asked of git rather than inferred.

    `git add -f` overrides an exclude file by design, and a shell expands a glob
    after a PreToolUse hook has already read the command, so no amount of string
    matching can answer this. The index can.
    """
    out = _run(["git", "diff", "--cached", "--name-only"], cwd=root, timeout=15)
    return sorted({f.strip() for f in out.splitlines()
                   if f.strip() and _is_praxis_state(f.strip())})


def tracked_local_artifacts(root: Path) -> List[str]:
    """praxis artifacts this repo already tracks.

    `git check-ignore` says nothing about a tracked path, so without this the
    guard would diagnose an already-committed artifact as a broken exclude file
    and send the user to fix something that is not wrong.
    """
    out = _run(["git", "ls-files", "--"] + [a.rstrip("/") for a in LOCAL_ARTIFACTS],
               cwd=root, timeout=15)
    return sorted({f.strip() for f in out.splitlines() if f.strip()})


def bootstrap_targets(root: Path) -> str:
    """What bootstrap will write here, named from the paths it will actually use.

    Both hooks that instruct a session to bootstrap have to state this, and a
    hand-written copy in each would re-hardcode exactly what the path helpers
    above exist to centralise: rename the knowledge directory and the two
    directives would confidently keep naming the old one.
    """
    if is_contributor(root):
        return (f"`{brief_path(root).name}` + "
                f"`{settings_path(root).relative_to(root)}` + "
                f"`{knowledge_root(root).relative_to(root)}/`, all git-excluded")
    return (f"`{brief_path(root).name}` + "
            f"`{settings_path(root).relative_to(root)}` + `/docs` + `CHANGELOG.md`")


def knowledge_path(root: Path, rel: str) -> Path:
    """Where a living-knowledge artifact (`CHANGELOG.md`, `docs/adr`) belongs.

    In a repository that is not ours the rule is: join what already exists, create
    nothing new. A project with a `CHANGELOG.md` expects a contribution to update
    it, and a pull request that skipped it is a worse pull request. A project
    without one did not ask praxis to introduce the convention, so that record is
    kept locally instead.
    """
    if is_contributor(root) and not (root / rel).exists():
        return knowledge_root(root) / rel
    return root / rel


# The block praxis manages inside the per-clone exclude file. Marked at both ends
# so it can be rewritten or removed without disturbing anything else in there.
LOCAL_EXCLUDE_BEGIN = "# >>> praxis local-only (managed) >>>"
LOCAL_EXCLUDE_END = "# <<< praxis local-only (managed) <<<"

_LOCAL_EXCLUDE_NOTE = (
    "# praxis is running in contributor mode in this clone: the paths below are\n"
    "# yours, not the repository's, and must never reach a commit or a pull\n"
    "# request. Remove this block by running: /praxis:config mode owner\n"
)


def _exclude_block() -> str:
    # Leading '/' anchors each pattern to the repository root, so an unrelated
    # CLAUDE.local.md deep in the tree is not silently hidden from its owner.
    patterns = "".join(f"/{p}\n" for p in LOCAL_ARTIFACTS)
    return f"{LOCAL_EXCLUDE_BEGIN}\n{_LOCAL_EXCLUDE_NOTE}{patterns}{LOCAL_EXCLUDE_END}\n"


def _strip_exclude_block(text: str) -> str:
    """Remove every complete praxis block, leaving everything else untouched.

    A block whose END marker is missing is left exactly as it is. The file
    belongs to the user, praxis only rents a marked region of it, and the
    alternative (treating everything after an unterminated BEGIN as ours) would
    silently delete the patterns below it: the precise harm this module exists to
    prevent, inflicted by it, on the user's own data.
    """
    while True:
        start = text.find(LOCAL_EXCLUDE_BEGIN)
        if start == -1:
            return text
        end = text.find(LOCAL_EXCLUDE_END, start)
        if end == -1:
            return text
        text = text[:start] + text[end + len(LOCAL_EXCLUDE_END):].lstrip("\n")


def ensure_local_exclusions(root: Path, enabled: bool) -> bool:
    """Add or remove praxis's block in `$GIT_COMMON_DIR/info/exclude`. True if changed.

    `info/exclude` is the file gitignore(5) reserves for patterns "specific to a
    particular repository but which do not need to be shared": it is never
    committed and never appears in a diff, which is precisely the guarantee
    contributor mode needs. Claude Code likewise arranges for git to ignore
    `.claude/settings.local.json` when it creates it; its documentation states the
    effect rather than the mechanism, so praxis picks the one git documents for
    exactly this purpose instead of editing a committed `.gitignore`.

    The effect is not cosmetic: once excluded, praxis's own files are invisible to
    `git status`, to `git add -A`, and to praxis's `untracked_files()`, so they can
    neither be swept into a commit nor make the Stop gate see a dirty tree.

    Fails open, returning False: a clone where the exclude file cannot be written
    (a read-only .git, a permission problem) must not break the session. The
    PreToolUse guard still refuses to stage these paths.
    """
    gd = git_dir(root)
    if gd is None:
        return False
    info = gd / "info"
    exclude = info / "exclude"
    try:
        current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    except Exception:
        return False

    stripped = _strip_exclude_block(current)
    if enabled:
        desired = stripped + ("\n" if stripped and not stripped.endswith("\n") else "")
        desired += _exclude_block()
    else:
        desired = stripped
    if desired == current:
        return False
    try:
        info.mkdir(parents=True, exist_ok=True)
        # Written the way praxis writes its own state: temp file plus os.replace.
        # This is the user's file, two Claude Code windows on one clone both fire
        # SessionStart, and a torn write here loses the project's own patterns.
        tmp = exclude.with_name(exclude.name + ".praxis.tmp")
        try:
            tmp.write_text(desired, encoding="utf-8")
            os.replace(tmp, exclude)
        except Exception:
            try:
                tmp.unlink()
            except Exception:
                pass
            raise
        return True
    except Exception:
        return False


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
    """The state directory, created if absent. For writers."""
    d = state_path(root, "")
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def state_path(root: Path, name: str) -> Path:
    """A path inside the state directory, without creating anything.

    For readers. Resolving a setting must not leave a directory behind in a
    repository praxis may not even be set up in, and in contributor mode that
    directory would exist before the exclusions that hide it were written.
    """
    base = root / ".claude" / ".praxis"
    return base / name if name else base


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


# --------------------------------------------------------------------------- #
# Switches: one ladder, resolved in one place
# --------------------------------------------------------------------------- #
# switch -> (toggle filename, env var, config key, inverted?)
#
# Two switches are inverted: their toggle files (`skip-gate`, `no-bootstrap`)
# record the OFF state by existing, so turning the feature off is an explicit act
# rather than the absence of one. Encoding that here keeps one code path instead
# of special-casing them at every call site.
#
# This table lives in `common` rather than in `config.py` because `config.py`
# imports `common` and not the other way round, and because every reader of a
# switch is a hook. Hand-rolled copies of this ladder had already drifted: the
# same `PRAXIS_GATE=on` could be reported ON by the settings command and treated
# as OFF by the gate that enforces it.
SWITCHES = {
    "autopilot": ("autopilot", "PRAXIS_AUTOPILOT", "autopilot.default", False),
    "auto-merge": ("auto-merge", "PRAXIS_AUTO_MERGE", "git.auto_merge", False),
    "bootstrap": ("no-bootstrap", "PRAXIS_BOOTSTRAP", "bootstrap.auto", True),
    "gate": ("skip-gate", "PRAXIS_GATE", "gate.enabled", True),
}

ON_WORDS = ("on", "1", "true", "yes", "enable", "enabled")
OFF_WORDS = ("off", "0", "false", "no", "disable", "disabled")


def resolve_switch(root: Path, switch: str):
    """(value, source) for one switch, most specific source first.

    Only the toggle *file* is inverted. `PRAXIS_GATE=off` disables the gate and
    `gate.enabled = true` enables it, both read the natural way round; it is
    solely the file that records the off state by existing. Applying the
    inversion to all three sources would make `PRAXIS_GATE=on` report the gate as
    disabled, which is the opposite of what the hook does with it.
    """
    toggle, env_var, key, inverted = SWITCHES[switch]
    env = os.environ.get(env_var, "").strip().lower()
    if env in ON_WORDS:
        return True, f"env {env_var}={env}"
    if env in OFF_WORDS:
        return False, f"env {env_var}={env}"
    if state_path(root, toggle).exists():
        return (False if inverted else True), f".claude/.praxis/{toggle}"
    cfg = read_config(root)
    return bool(cfg.get(key)), (".praxis.toml" if (root / ".praxis.toml").exists()
                                else "default")


def switch_on(root: Path, switch: str) -> bool:
    try:
        return bool(resolve_switch(root, switch)[0])
    except Exception:
        # A switch that cannot be resolved falls back to its default rather than
        # breaking the hook that asked.
        return bool(_CONFIG_DEFAULTS.get(SWITCHES[switch][2], False))


def autopilot_on(root: Path) -> bool:
    """True if auto-pilot is enabled.

    In auto-pilot praxis does not ask the user design/approach questions; it
    decides by best-practice and logs the decision instead.
    """
    return switch_on(root, "autopilot")


def auto_merge_on(root: Path) -> bool:
    """True if autonomous review-and-merge is enabled.

    When on, praxis may merge its own PRs after a green audit. When off (default),
    it opens the PR and stops for a human to review and merge.
    """
    return switch_on(root, "auto-merge")


def gate_enabled(root: Path) -> bool:
    """True if the Stop gate holds a turn open until the change is audited."""
    return switch_on(root, "gate")


_CONFIG_DEFAULTS = {
    "gate.enabled": True,             # master switch for the Stop gate
    "gate.require_tests": True,       # require passing test evidence in the green report
    "gate.require_ui_verticals": True,  # UI diffs need the a11y + design verdicts
    "autopilot.default": False,       # start sessions in auto-pilot
    "audit.depth": "high",            # informational hint for the auditors
    "bootstrap.auto": True,           # set the repo up on its own, before any work
    "workspace.mode": AUTO,           # "auto" | "owner" | "contributor"
    "git.auto_merge": False,          # auto-review and merge PRs; off = PR only, human merges
    "git.default_branch": "",         # PR base branch ("" = auto-detect)
    "style.ban_em_dash": True,        # refuse em dashes in authored text
    "style.ban_ai_attribution": True,  # refuse AI co-author / generated-by credits
}

#: A second, git-excluded config layer inside the state directory, read after
#: `.praxis.toml` and overriding it. It is what lets a contributor hold local
#: preferences without editing (or fighting) a `.praxis.toml` the upstream
#: project committed.
LOCAL_CONFIG = "praxis.toml"


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


#: The size above which a config file is not a config file. Read unconditionally
#: on every prompt and before every publishing command, and a repository we may
#: not own supplies it.
MAX_CONFIG_BYTES = 256_000


def _apply_toml(f: Path, cfg: Dict[str, Any]) -> tuple:
    """Overlay one config file onto `cfg`. Returns (ok, keys it set).

    A small, flat subset of TOML ([section] + key = value), parsed by hand so
    praxis stays stdlib-only on Python 3.8 (tomllib arrived in 3.11). Unknown keys
    are ignored rather than rejected: a newer praxis writing a key this one does
    not know must not invalidate the whole file.

    The key list is what lets a caller say which layer a value came from, which
    is the whole point of reporting a source at all.
    """
    if not f.exists():
        return True, ()
    keys = []
    try:
        if f.stat().st_size > MAX_CONFIG_BYTES:
            return False, ()
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
                    keys.append(key)
    except Exception:
        return False, tuple(keys)
    return True, tuple(keys)


def config_layers(root: Path) -> list:
    """(label, path) for each config layer, least specific first."""
    return [(".praxis.toml", root / ".praxis.toml"),
            # state_dir() would mkdir, and a plain read must not create
            # directories in a repository praxis may not even be set up in.
            (f".claude/.praxis/{LOCAL_CONFIG}",
             root / ".claude" / ".praxis" / LOCAL_CONFIG)]


def read_config_sources(root: Path) -> tuple:
    """(config, {key: the layer that last set it}).

    Two layers, least specific first: the committed `.praxis.toml` the team
    shares, then `.claude/.praxis/praxis.toml`, which is git-excluded and yours
    alone. A malformed file falls back to the defaults rather than raising, since
    every caller is a hook that must not break the session.
    """
    cfg = dict(_CONFIG_DEFAULTS)
    sources: Dict[str, str] = {}
    for label, path in config_layers(root):
        ok, keys = _apply_toml(path, cfg)
        if not ok:
            # A half-parsed file leaves half its values behind, so drop what it
            # set rather than keeping an arbitrary prefix of it. The other layer
            # still applies: one corrupt file is not a reason to discard both.
            for key in keys:
                cfg[key] = _CONFIG_DEFAULTS[key]
                sources.pop(key, None)
            continue
        for key in keys:
            sources[key] = label
    return cfg, sources


def read_config(root: Path) -> Dict[str, Any]:
    """The resolved praxis configuration for a repo.

    Not memoised on purpose: `config.py` writes a value and re-reads it in the
    same process to report what actually took effect.
    """
    return read_config_sources(root)[0]


# --------------------------------------------------------------------------- #
# Repo state: is praxis set up here?
# --------------------------------------------------------------------------- #
#: Marker praxis writes into the brief it manages, so it recognises its own work
#: on the next session instead of proposing the setup again.
PRAXIS_MARK = "<!-- praxis:managed -->"

#: Build-system markers. Their presence means "there is a real project here",
#: which separates an empty directory from a codebase with no Claude Code setup.
_SOURCE_MARKERS = (
    "package.json", "pyproject.toml", "setup.py", "requirements.txt",
    "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile",
    "composer.json", "mix.exs", "pubspec.yaml", "CMakeLists.txt",
    "Makefile", "*.sln",
)


def has_source(root: Path) -> bool:
    for marker in _SOURCE_MARKERS:
        try:
            if any(root.glob(marker)) if "*" in marker else (root / marker).exists():
                return True
        except Exception:
            continue
    return False


def repo_state(root: Path) -> str:
    """One of new | uninitialised | legacy | partial | managed.

    Lives here rather than in the session audit because three callers now need
    the same verdict (the audit, the prompt router, and the doctor), and a second
    copy of this ladder would be a second place for it to drift.

    In contributor mode the brief is `CLAUDE.local.md`, so a clone praxis has
    already set up reads as `managed` even though the repository's own
    `CLAUDE.md` (if any) was never touched.
    """
    brief = brief_path(root)
    settings = settings_path(root)

    if not has_source(root) and not (root / ".git").exists():
        return "new"
    if not brief.exists() and not settings.exists():
        return "uninitialised"
    if brief.exists():
        try:
            body = brief.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            body = ""
        return "managed" if PRAXIS_MARK in body else "legacy"
    return "partial"


def bootstrap_auto(root: Path) -> bool:
    """True if praxis may set an unmanaged repo up on its own."""
    return switch_on(root, "bootstrap")


def bootstrap_required(root: Path) -> bool:
    """True when this repo has no praxis setup and praxis is allowed to add one."""
    try:
        return repo_state(root) != "managed" and bootstrap_auto(root)
    except Exception:
        return False


def change_signature(root: Path) -> str:
    """A stable hash of the current change set (HEAD + dirty file list + sizes).

    Used to key the quality-gate: a green audit is valid only for the exact
    state it was produced against. Recomputed on every call (two git
    subprocesses); callers that need it more than once should hold the value.
    """
    # The branch's base as well as its head: HEAD alone moves on every commit,
    # which correctly invalidates a report, but says nothing about how much of
    # the branch the report covered. Keying on the range means a report recorded
    # against three commits is still valid for those three and not for a fourth.
    parts = [git_head(root), review_base(root) or ""]
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
