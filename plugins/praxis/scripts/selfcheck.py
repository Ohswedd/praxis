#!/usr/bin/env python3
"""
Praxis self-check: validates the plugin's own integrity.

Two scopes, because the plugin is checked from two very different places.

  * **plugin scope** covers everything that travels inside the installed plugin:
    the plugin manifest parses, hooks point at scripts that exist, frontmatter is
    valid YAML, every script compiles, every `/praxis:<command>` and
    `scripts/<name>.py` reference resolves, and the shipped text obeys the house
    style praxis enforces on everyone else. This is what `/praxis:doctor` asks on
    a user's machine.
  * **repo scope** adds what exists only in the source checkout: the enclosing
    marketplace manifest, its version agreement with the plugin, its source
    paths, and the repo prose (README, CONTRIBUTING, `/docs`) held to the same
    house style. This is what CI asks before publishing.

The distinction is not cosmetic. An installed plugin has no marketplace beside
it, so demanding one made `/praxis:doctor` report PROBLEM on every healthy
install. A permanent false alarm is worse than no check at all: it teaches the
reader to ignore the one line that would matter when something really is broken.

Scope is detected from whether a marketplace manifest that actually publishes
THIS plugin sits above it, rather than from a file merely existing two levels up:
a plugin unpacked inside some unrelated repository must not be cross-checked
against that repository's marketplace. `--require-repo` turns the detection into
an assertion, so CI cannot silently fall back to the smaller scope and report OK
for a tree whose marketplace is missing, unreadable, or no longer lists the
plugin.

Usage:
    selfcheck.py                 # detect the scope and report it
    selfcheck.py --require-repo  # fail unless the full repo scope is available

Exit code 0 if healthy, 1 if any problem, so it can gate CI. Run it directly, or
via `/praxis:doctor`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent   # .../plugins/praxis

sys.path.insert(0, str(PLUGIN / "scripts" / "lib"))
import common  # noqa: E402

#: Content that carries instructions, and so must not contain stale references.
CONTENT_AREAS = ("skills", "commands", "output-styles", "agents")

#: Repo-level prose held to the same house style as the plugin's own content.
#: These live beside the plugin in the source tree and are absent from an install.
#: `CLAUDE.md` is included because it is the repo's most-read instruction file and
#: it claims, in its own text, that this check covers it.
REPO_TEXT = ("README.md", "CONTRIBUTING.md", "SECURITY.md", "PRIVACY.md", "CLAUDE.md")

SCOPE_REPO = "repo"
SCOPE_PLUGIN = "plugin"


def enclosing_marketplace(plugin: Path):
    """(root, manifest, parsed) for the marketplace that publishes `plugin`.

    None when the plugin stands alone, which is exactly how it is installed: the
    cache holds the plugin directory and nothing above it.

    A manifest that exists but cannot be parsed returns `parsed=None` rather than
    None, because in a source repo an unreadable marketplace is a failure to
    report, not a reason to quietly check less.
    """
    root = plugin.parent.parent
    manifest = root / ".claude-plugin" / "marketplace.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return root, manifest, None
    # A manifest can parse and still not be a marketplace: a bare list, a string,
    # a `plugins` key holding a number. Treat any of those as "does not publish
    # this plugin" rather than letting the checker die on a traceback.
    entries = data.get("plugins") if isinstance(data, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        try:
            if (root / str(entry.get("source", ""))).resolve() == plugin:
                return root, manifest, data
        except Exception:
            continue
    return None


def _rel(path: Path, base: Path) -> str:
    """`path` relative to `base`, or its absolute form when it lies outside."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


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
        if "\t" in line:
            return None  # a tab in YAML indentation drops the whole frontmatter
        mm = re.match(r"^([A-Za-z0-9_-]+):(.*)$", line)
        if not mm:
            continue
        keys.add(mm.group(1))
        value = mm.group(2).strip()
        if value[:1] not in ("", '"', "'") and ": " in value:
            return None  # unquoted scalar with ': ', YAML would drop the frontmatter
    return keys


def check(require_repo: bool = False):
    """Run every applicable check. Returns (scope, checks_run, errors)."""
    errors, checks = [], 0

    def need(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            errors.append(msg)

    def fail(msg):
        """A check that has already been decided against."""
        need(False, msg)

    market = enclosing_marketplace(PLUGIN)
    scope = SCOPE_REPO if market else SCOPE_PLUGIN
    root = market[0] if market else PLUGIN

    if require_repo and not market:
        fail("--require-repo was given but no marketplace manifest publishing this "
             f"plugin was found above {PLUGIN}. Run this from the source checkout.")

    # ----- plugin scope: everything that ships inside the plugin --------------
    pj = {}
    try:
        pj = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        need("name" in pj and "version" in pj, "plugin.json missing name/version")
    except Exception as e:
        fail(f"plugin.json invalid: {e}")

    try:
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
        for ref in re.findall(r"scripts/([A-Za-z0-9_]+\.py)", json.dumps(hooks)):
            need((PLUGIN / "scripts" / ref).exists(),
                 f"hook references missing script: {ref}")
    except Exception as e:
        fail(f"hooks.json invalid: {e}")

    for md in sorted((PLUGIN / "agents").glob("*.md")):
        k = _frontmatter_keys(md)
        need(k and {"name", "description"} <= k, f"agent {md.name}: bad/missing frontmatter")
    checks += _review_scope_wiring(PLUGIN, errors)
    for skill in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        k = _frontmatter_keys(skill)
        need(k and {"name", "description"} <= k,
             f"skill {skill.parent.name}: bad/missing frontmatter")
    for cmd in sorted((PLUGIN / "commands").glob("*.md")):
        k = _frontmatter_keys(cmd)
        need(k and "description" in k, f"command {cmd.name}: missing description frontmatter")
    for style in sorted((PLUGIN / "output-styles").glob("*.md")):
        k = _frontmatter_keys(style)
        need(k and {"name", "description"} <= k, f"output-style {style.name}: bad frontmatter")

    for py in sorted((PLUGIN / "scripts").rglob("*.py")):
        checks += 1
        try:
            compile(py.read_text(encoding="utf-8"), str(py), "exec")
        except Exception as e:
            errors.append(f"compile error in {py.name}: {e}")

    # Agent references (@praxis:name) must resolve to a real agent.
    agent_names = set()
    for md in sorted((PLUGIN / "agents").glob("*.md")):
        try:
            for line in md.read_text(encoding="utf-8").splitlines():
                mm = re.match(r"^name:\s*(\S+)", line)
                if mm:
                    agent_names.add(mm.group(1))
                    break
        except Exception:
            continue
    referenced = set()
    for area in ("skills", "commands", "output-styles"):
        for md in (PLUGIN / area).rglob("*.md"):
            try:
                referenced |= set(re.findall(r"@praxis:([a-z0-9-]+)",
                                             md.read_text(encoding="utf-8")))
            except Exception:
                continue
    for ref in sorted(referenced):
        need(ref in agent_names, f"dangling agent reference @praxis:{ref}")

    # Instructions that point at a command or script which no longer exists are
    # worse than missing instructions: they read as authoritative and send the
    # session somewhere that cannot work. Merging or renaming a command must
    # therefore fail until every reference follows.
    commands = {p.stem for p in (PLUGIN / "commands").glob("*.md")}
    for md, text in plugin_content():
        rel = _rel(md, root)
        for ref in sorted(set(re.findall(r"/praxis:([a-z0-9-]+)", text))):
            need(ref in commands, f"{rel}: references /praxis:{ref}, which does not exist")
        for script in sorted(set(re.findall(r"scripts/([A-Za-z0-9_]+\.py)", text))):
            need((PLUGIN / "scripts" / script).exists(),
                 f"{rel}: references scripts/{script}, which does not exist")

    # praxis bans em dashes and AI attribution in every project it touches; its
    # own shipped text is the first place that has to hold.
    checks += _house_style(plugin_content(), root, errors)

    # ----- repo scope: the source checkout only -------------------------------
    if market:
        _, manifest, mj = market
        if mj is None:
            fail(f"marketplace.json invalid: {_rel(manifest, root)} does not parse")
        else:
            need(mj.get("metadata", {}).get("version") == pj.get("version"),
                 f"version mismatch: plugin={pj.get('version')} "
                 f"marketplace={mj.get('metadata', {}).get('version')}")
            for entry in mj.get("plugins", []):
                src = (root / str(entry.get("source", ""))).resolve()
                need((src / ".claude-plugin" / "plugin.json").exists(),
                     f"marketplace source has no plugin.json: {entry.get('source')}")
        checks += _house_style(repo_prose(root), root, errors)

    return scope, checks, errors


# --------------------------------------------------------------------------- #
# The shared review scope
# --------------------------------------------------------------------------- #
#: The skill that holds the scoping rules, once. Agent bodies never restate them.
REVIEW_SCOPE_SKILL = "review-scope"

#: Agents that are handed a file list rather than a change, so they have no base
#: to resolve and the scoping rules do not apply to them.
NON_REVIEW_AGENTS = {"repo-cartographer", "claudemd-verifier", "finding-verifier"}

#: The pointer every review agent carries, byte for byte. It is a *pointer*, not
#: a copy: the rules live in the skill, and this exists only so a preload that
#: silently did not happen cannot leave an auditor with no scoping at all. Agent
#: files have no include directive, so this line is the smallest thing that has
#: to be repeated, and asserting it exactly is what stops it drifting.
REVIEW_SCOPE_BLOCK = """<!-- praxis:review-scope begin (generated, do not edit; see skills/review-scope/SKILL.md) -->
**Scope the change before you judge it.** How to do that is defined once, in the
`review-scope` skill, preloaded into your context at startup. If it is not there,
read `${CLAUDE_PLUGIN_ROOT}/skills/review-scope/SKILL.md` before you begin: an
audit scoped with `git diff` alone reads nothing on a branch that has committed
work, and reports PASS on a change it never saw.
<!-- praxis:review-scope end -->"""


def _preloads_skill(body: str, skill: str) -> bool:
    """True if the frontmatter's `skills:` list really contains `skill`.

    Parsed rather than substring-matched: `# - praxis:review-scope` contains the
    name and preloads nothing, and a check that accepted it would report the
    wiring as present on an agent that has none.
    """
    if body.count("---") < 2:
        return False
    front = body.split("---")[1]
    in_list = False
    for raw in front.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^skills:\s*$", line):
            in_list = True
            continue
        if in_list:
            item = re.match(r"^\s+-\s*(.+?)\s*$", line)
            if not item:
                in_list = False          # the list ended at the next key
                continue
            if item.group(1).strip("'\"") == skill:
                return True
    return False


def _review_scope_wiring(plugin: Path, errors: list) -> int:
    """Assert the scoping rules exist once and reach every auditor. Returns checks.

    Three failures are possible and all of them are silent at runtime, which is
    why they are asserted here rather than trusted:
      * the skill goes missing, and every preload is skipped with only a debug-log
        warning;
      * an agent stops preloading it, or never did;
      * an agent's pointer drifts from the canonical one, so the two disagree
        about where the rules live.
    Any of them ends with an auditor scoping to `git diff`, reading nothing on a
    branch that has committed work, and reporting PASS.
    """
    checks = 0
    skill = plugin / "skills" / REVIEW_SCOPE_SKILL / "SKILL.md"

    checks += 1
    if not skill.is_file():
        errors.append(f"the {REVIEW_SCOPE_SKILL} skill is missing: every agent that "
                      "preloads it would be skipped with only a debug-log warning")
        return checks

    try:
        text = skill.read_text(encoding="utf-8")
    except Exception as exc:
        checks += 1
        errors.append(f"skill {REVIEW_SCOPE_SKILL}: unreadable ({exc})")
        return checks
    front = text.split("---")[1] if text.count("---") >= 2 else ""

    # A skill that cannot be invoked by the model cannot be preloaded either.
    # Matched as a key with a truthy value rather than one exact string, since
    # `True` and `yes` are equally truthy to a YAML loader and equally invisible
    # to a substring test.
    checks += 1
    if re.search(r"(?im)^\s*[\"']?disable-model-invocation[\"']?\s*:\s*(true|yes|on)\b",
                 front):
        errors.append(f"skill {REVIEW_SCOPE_SKILL}: sets disable-model-invocation, "
                      "which makes it impossible to preload into an agent")

    # The name the agents reference, not the directory they happen to sit in. A
    # half-done rename leaves `skills: [praxis:review-scope]` resolving to
    # nothing in all ten agents, skipped with only a debug-log warning.
    checks += 1
    declared_name = re.search(r"(?m)^name:\s*(\S+)\s*$", front)
    if not declared_name or declared_name.group(1).strip("'\"") != REVIEW_SCOPE_SKILL:
        errors.append(f"skill {REVIEW_SCOPE_SKILL}: its frontmatter name is "
                      f"{declared_name.group(1) if declared_name else 'missing'}, so "
                      "every `praxis:review-scope` preload would resolve to nothing")

    # The rules themselves. Concentrating ten copies into one file and then not
    # asserting the file says anything would trade drift for a single silent
    # point of failure: a truncated write leaves ten auditors preloading nothing.
    checks += 1
    body = text.split("---", 2)[-1]
    missing = [phrase for phrase in ("scope.py", "base", "untracked")
               if phrase not in body]
    if missing or len(body.split()) < 120:
        errors.append(f"skill {REVIEW_SCOPE_SKILL}: its body no longer carries the "
                      f"scoping rules (missing: {', '.join(missing) or 'too short'}), "
                      "so every agent preloads an empty instruction")

    for md in sorted((plugin / "agents").rglob("*.md")):
        try:
            body = md.read_text(encoding="utf-8")
        except Exception:
            body = ""
        declared = _preloads_skill(body, f"praxis:{REVIEW_SCOPE_SKILL}")
        # Immediately after the frontmatter, not merely somewhere in the file: a
        # pointer demoted into an example, a code fence, or the tail of the brief
        # is a pointer the agent reads last or not at all.
        has_block = body.split("---", 2)[-1].lstrip("\n").startswith(REVIEW_SCOPE_BLOCK)

        if md.stem in NON_REVIEW_AGENTS:
            checks += 1
            if declared or has_block:
                errors.append(f"agent {md.name}: is handed a file list, not a change, "
                              "so the review-scope wiring does not belong to it")
            continue

        checks += 2
        if not declared:
            errors.append(f"agent {md.name}: reviews a change but does not preload "
                          f"the {REVIEW_SCOPE_SKILL} skill, so it would scope to "
                          "`git diff` and audit an empty diff on a branch")
        if not has_block:
            errors.append(f"agent {md.name}: its review-scope pointer is missing or "
                          "has drifted from the canonical block in selfcheck.py; "
                          "replace it verbatim rather than rewording it")
    return checks


def _house_style(files, root: Path, errors: list) -> int:
    """Append a house-style error per offending line. Returns the files checked."""
    seen = 0
    for path, text in files:
        seen += 1
        rel = _rel(path, root)
        for lineno, line in enumerate(text.splitlines(), 1):
            if common.is_acked(line):
                continue
            for name in common.scan_banned_dashes(line) + common.scan_ai_attribution(line):
                errors.append(f"{rel}:{lineno}: house style, {name}")
    return seen


def _read(paths):
    for p in paths:
        try:
            yield p, p.read_text(encoding="utf-8")
        except Exception:
            continue


def plugin_content():
    """(path, text) for the instruction content and templates that ship."""
    paths = []
    for area in CONTENT_AREAS:
        paths.extend(sorted((PLUGIN / area).rglob("*.md")))
    paths.extend(sorted((PLUGIN / "templates").glob("*.tpl")))
    return _read(paths)


def repo_prose(root: Path):
    """(path, text) for the source-tree prose that never ships with the plugin."""
    paths = [root / name for name in REPO_TEXT]
    paths.extend(sorted((root / "docs").rglob("*.md")))
    return _read(paths)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    require_repo = "--require-repo" in argv
    unknown = [a for a in argv if a != "--require-repo"]
    if unknown:
        print(f"praxis selfcheck: unknown argument(s): {' '.join(unknown)}")
        print("usage: selfcheck.py [--require-repo]")
        return 2

    scope, checks, errors = check(require_repo)
    detail = ("repo scope: the plugin, its marketplace, and the repo prose"
              if scope == SCOPE_REPO else
              "installed-plugin scope: the marketplace and repo prose are not part "
              "of an installed plugin, so they are not checked here")
    if errors:
        print(f"praxis selfcheck: {len(errors)} problem(s) across {checks} checks "
              f"({detail}):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print(f"praxis selfcheck: OK ({checks} checks passed, {detail}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
