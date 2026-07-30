#!/usr/bin/env python3
"""
praxis PreToolUse guard.

Blocks two categories of action deterministically, and, crucially, keeps
working even under `--dangerously-skip-permissions`, because PreToolUse hooks
run before the permission-mode check:

  1. Access to sensitive files (.env, private keys, credentials, .ssh/ ...).
     Note: a Read deny only blocks the Read tool; `cat .env` in Bash is caught
     by the Bash branch below.
  2. Catastrophic / irreversible shell commands (rm -rf on broad paths,
     disk wipes, forced pushes (any branch), `curl | sh`, fork bombs,
     destructive SQL).
  3. AI attribution in anything published to the project's record: a commit
     message, tag, pull request, release, or issue carrying a
     `Co-Authored-By: Claude` trailer or a "generated with" credit. Unlike the  # praxis:ack
     other two this is a house-style rule rather than a safety one, but it needs
     the same deterministic enforcement: it is stated in the doctrine, complied
     with in the abstract, and forgotten at the moment of committing. Once the
     commit exists the credit is in the history for good.
  4. Staging praxis's own local artifacts (`CLAUDE.local.md`, `.claude/.praxis/`,
     `.claude/settings.local.json`). These describe how one machine works, never
     what the project is, so committing them is wrong in any repository and
     actively harmful in one you are only contributing to. `$GIT_COMMON_DIR/info/exclude`
     already hides them from `git add -A`; this catches the explicit path and the
     `-f` that would override the exclusion.
  5. Creating, in a repository we only contribute to, a file praxis writes for a
     repository we own: `CHANGELOG.md`, a `/docs` skeleton, `CLAUDE.md`,
     `.praxis.toml`. Joining one the project already has is right; introducing
     one is proposing a convention on the maintainers' behalf, inside a pull
     request that was supposed to be about a bug. The rule was stated in prose
     and honoured by the helpers, and a direct write ignored both.

Exit 2 blocks the tool and feeds the reason back to Claude.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


# Interposed global options (git -c k=v push, git -C path push, git --git-dir=… push)
# so a subcommand cannot hide behind them.
#
# Written so the two alternatives cannot both match the same token: a flag starts
# with `-`, a flag's value does not. The obvious form, `(?:\s+-\S+(?:\s+\S+)?)*`,
# is ambiguous with itself, which gives a run of k dash-tokens Fib(k) distinct
# parses and makes a failed match exponential: 40 of them took 27 seconds to
# reject here, against a 15 second hook budget. A PreToolUse hook that times out
# does not deny the tool, so that was not a slow guard, it was a way to switch
# the guard off from inside the command it was meant to inspect.
_GIT_OPTS = r"(?:\s+-\S+|\s+(?![a-z-]*\b(?:push|add|stage|commit)\b)[^-\s]\S*)*"
_GIT_PUSH = r"\bgit\b" + _GIT_OPTS + r"\s+push\b[^|&;#]*"

# Commands that are effectively irreversible and should never run unattended.
DANGEROUS_COMMAND_PATTERNS = [
    (r"\brm\s+(-[a-zA-Z]*\s+)*-?[a-zA-Z]*[rf][a-zA-Z]*\b.*\s(/|~|\$HOME|\.\s*$|\*)",
     "Recursive/forced delete on a broad or root path"),
    (r"\brm\s+-rf?\s+/\b", "rm -rf on filesystem root"),
    (r"\brm\b.*(--recursive|--force).*\s(/|~|\$HOME)(\s|$)",
     "Recursive/forced delete on root or home (long-form flags)"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Fork bomb"),
    (r"\bmkfs\.", "Filesystem format"),
    (r"\bdd\b.*\bof=/dev/(sd|nvme|disk)", "Raw disk overwrite"),
    (r">\s*/dev/(sd|nvme|disk)", "Redirect over a raw disk device"),
    # Force-push in any form: long/bundled flag or the '+refspec' syntax, on any
    # branch, with or without --force-with-lease. It rewrites remote history, so a
    # human runs it; praxis never does it unattended. The leading [\s'"] also catches
    # a quoted flag/refspec (`git push "--force"`, `git push origin '+main'`).
    (_GIT_PUSH + r"""[\s'"](--force|-[a-zA-Z]*f[a-zA-Z]*)\b""",
     "Force-push (irreversible: run it yourself)"),
    (_GIT_PUSH + r"""[\s'"]\+[^\s|&;]""",
     "Force-push via +refspec (irreversible: run it yourself)"),
    (r"\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f)", "Destructive git state reset"),
    (r"\bgh\s+pr\s+merge\b.*\s--admin\b",
     "Merging a PR with --admin (bypasses branch protection)"),
    (r"(curl|wget)\s+[^|]*\|\s*(sudo\s+)?(sh|bash|zsh)\b",
     "Piping a remote script straight into a shell"),
    (r"(?i)\bdrop\s+(table|database|schema)\b", "Destructive SQL (DROP)"),
    (r"(?i)\btruncate\s+table\b", "Destructive SQL (TRUNCATE)"),
    (r"\bchmod\s+-R\s+0?777\s+/", "World-writable recursive chmod on root path"),
    (r"(env|printenv|cat\s+[^|]*\.env[^|]*)\s*\|\s*(curl|wget|nc|ncat|telnet)\b",
     "Piping environment/secrets to the network (exfiltration)"),
    (r">>?\s*\S*\.ssh/authorized_keys", "Writing to an SSH authorized_keys file"),
    (r">\s*/etc/\S+", "Writing into /etc (system configuration)"),
    (r"\bgit\s+config\b.*credential\.helper\s+store", "Persisting credentials in plaintext"),
]

_DANGEROUS = [(re.compile(p), why) for p, why in DANGEROUS_COMMAND_PATTERNS]

# Commands that write to the project's permanent record. Text they carry is
# published: rewriting it afterwards means rewriting history or editing a PR that
# reviewers have already read.
_PUBLISHING_RE = re.compile(
    r"\bgit\s+(commit|tag|merge|revert|cherry-pick|notes)\b"
    r"|\bgh\s+(pr|issue|release)\s+(create|edit|comment|merge)\b",
    re.IGNORECASE,
)


def check_attribution(hook_input, command: str) -> None:
    """Refuse to publish an AI co-author or generated-by credit.

    Ordered cheapest-first, and the repo root is resolved only once both regexes
    have already matched: this runs before *every* Bash call, and `project_dir`
    can cost a `git rev-parse`.
    """
    if not _PUBLISHING_RE.search(command):
        return
    found = common.scan_ai_attribution(command)
    if not found:
        return
    if not common.read_config(common.project_dir(hook_input)).get(
            "style.ban_ai_attribution", True):
        return
    common.block(
        f"[praxis] Blocked: this command publishes an AI attribution "
        f"({', '.join(found)}).\n"
        "praxis never credits the tool in a project's record. Remove the "
        "`Co-Authored-By:` trailer, the \"generated with\" footer, and any robot "
        "emoji credit from the message or body, then run it again.\n"
        "Naming the platform in prose is fine (\"praxis is a Claude Code "
        "plugin\"); crediting authorship is not. If the text is genuinely about "
        "the rule itself, put it in a file rather than in a commit message.\n"
        "Opt out for this repo with `ban_ai_attribution = false` under `[style]` "
        "in .praxis.toml."
    )


# Commands that can put a path into the index. `git commit <path>` bypasses the
# index entirely, and `update-index`/`stash`/`apply --cached` write it directly
# without consulting an exclude file at all, so all of them belong here.
_STAGING_RE = re.compile(
    r"\bgit\b" + _GIT_OPTS + r"\s+(?:add|stage|commit|update-index|stash|apply)\b",
    re.IGNORECASE)

#: Any command that reads or writes the index, at which point the authoritative
#: question is what is actually staged rather than what the string looks like.
_INDEX_WRITER_RE = re.compile(
    r"\bgit\b" + _GIT_OPTS + r"\s+(?:commit|stash|push)\b", re.IGNORECASE)

# `-m "…"`, `-F file`, and quoted runs. Stripped before the artifact search so a
# commit *about* these files is not mistaken for a commit *of* them: praxis's own
# history is full of messages naming CLAUDE.local.md, and blocking the one command
# a user cannot cheaply retry, for a false positive, with no escape, is worse than
# the miss it would prevent (the index check below catches the real case anyway).
_QUOTED_RE = re.compile(r"""(-m|-F|--message|--file)(\s*=\s*|\s+)("[^"]*"|'[^']*'|\S+)"""
                        r"""|"[^"]*"|'[^']*'""")

# The artifact names, matched on the raw command before anything is resolved.
# Cheap enough to run before every Bash call, and specific enough that a match is
# always about a real praxis file. Derived from the canonical list rather than
# restated, so a fourth artifact cannot be added to common and silently left
# unguarded here.
_LOCAL_ARTIFACT_RE = re.compile(
    "|".join(re.escape(p.rstrip("/")) for p in common.LOCAL_ARTIFACTS))


_WHY_NOT_COMMITTED = (
    "`CLAUDE.local.md`, `.claude/.praxis/` and `.claude/settings.local.json` "
    "hold how *your machine* is set up, not what the project is. They are "
    "git-excluded on purpose; committing one puts your local setup into "
    "someone else's history, and in a repo you are contributing to it puts it "
    "into their pull request."
)


def check_local_artifacts(command: str) -> None:
    """Refuse to stage a file that describes this machine rather than the project.

    Ordered cheapest-first: the artifact names are rarer than `git add`, so they
    are tested first and the staging regex only runs on a hit. Quoted text is
    removed first, so this fires on a path argument and not on a commit message
    that happens to mention one.
    """
    bare = _QUOTED_RE.sub(" ", command)
    if not _LOCAL_ARTIFACT_RE.search(bare) or not _STAGING_RE.search(bare):
        return
    common.block(
        "[praxis] Blocked: this command would stage a praxis local artifact.\n"
        f"Command: {command.strip()[:400]}\n"
        + _WHY_NOT_COMMITTED + "\n"
        "Stage the files your change actually touches instead. If a project "
        "genuinely wants one of these committed, that is a decision for its "
        "maintainers to make and to run themselves."
    )


_WHY_NOT_INTRODUCED = (
    "praxis joins the conventions a project already has and introduces none it "
    "does not. Adopting a changelog, a /docs tree or an operating brief is a "
    "maintainer's decision, not a contributor's, and a pull request carrying one "
    "asks reviewers to accept a policy they never discussed alongside the fix "
    "they did.\n"
    "praxis keeps its own copy under `.claude/.praxis/knowledge/`, which mirrors "
    "the same layout and is git-excluded. `changelog.py`, `adr.py` and `debt.py` "
    "already resolve this: run them and read the path they print.\n"
    "If the user genuinely asked for this file, `/praxis:config "
    "project-artifacts on` (or `PRAXIS_PROJECT_ARTIFACTS=on`) lifts the rule for "
    "this repository. Propose it in the pull request rather than slipping it in."
)


def check_project_artifact(hook_input, path: str) -> None:
    """Refuse to create, in someone else's repo, a file praxis writes in ours.

    The rule prose has always stated, made deterministic. Prose held for the
    helpers (`changelog.py` routes itself correctly) and failed for the direct
    write, which is how a `CHANGELOG.md` the maintainers never asked for reached
    a pull request whose subject was a bug fix.
    """
    if not path:
        return
    root = common.project_dir(hook_input)
    reason = common.project_artifact_reason(root, path)
    if not reason:
        return
    common.block(
        f"[praxis] Blocked: creating `{common.repo_relative(root, path) or path}` "
        f"in a repository we only contribute to.\n{reason}.\n"
        + _WHY_NOT_INTRODUCED
    )


#: A command that writes a file, as opposed to reading or naming one.
_WRITE_CMD_RE = re.compile(
    r">>?\s*\S|\b(tee|cp|mv|touch|mkdir|install|rsync|ln)\b"
    r"|\b(curl|wget)\b[^|&;#]*\s-[oO]\b"
    r"|\b(sed|perl|awk)\b[^|&;#]*-i", re.IGNORECASE)

_PROJECT_ARTIFACT_RE = re.compile(
    "|".join(re.escape(p.rstrip("/")) for p in
             common.PROJECT_ARTIFACTS + common.PROJECT_ARTIFACT_DIRS))


def check_project_artifact_shell(hook_input, command: str) -> None:
    """The same rule as `check_project_artifact`, for the shell route into it.

    A rule that holds for Write and not for `printf ... > CHANGELOG.md` is not a
    rule. Quoted text is stripped first, so a command that merely *mentions* one
    of these files is not mistaken for one that writes it.
    """
    bare = _QUOTED_RE.sub(" ", command)
    if not _PROJECT_ARTIFACT_RE.search(bare) or not _WRITE_CMD_RE.search(bare):
        return
    root = common.project_dir(hook_input)
    for token in re.split(r"[\s;|&<>()]+", bare):
        token = token.strip("'\"")
        if not token or not _PROJECT_ARTIFACT_RE.search(token):
            continue
        reason = common.project_artifact_reason(root, token)
        if reason:
            common.block(
                "[praxis] Blocked: this command would create "
                f"`{token}` in a repository we only contribute to.\n"
                f"Command: {command.strip()[:400]}\n"
                f"{reason}.\n" + _WHY_NOT_INTRODUCED
            )


def check_staged_project_artifacts(hook_input, command: str) -> None:
    """Refuse to commit an index that would introduce one of these files.

    The index is the fact, the command string only a proxy, exactly as for
    praxis's local artifacts: whatever wrote the file, it becomes part of the
    project by being committed, and that is the moment worth refusing.
    """
    if not _INDEX_WRITER_RE.search(command):
        return
    staged = common.staged_project_artifacts(common.project_dir(hook_input))
    if not staged:
        return
    common.block(
        "[praxis] Blocked: this commit would add "
        f"{', '.join(staged)} to a repository we only contribute to, which does "
        "not have "
        + ("them" if len(staged) > 1 else "it") + ".\n"
        + _WHY_NOT_INTRODUCED + "\n"
        "Unstage and delete what the project did not ask for:\n"
        f"  git restore --staged {' '.join(staged)}"
    )


def check_staged_index(hook_input, command: str) -> None:
    """Refuse to commit an index that already contains a praxis artifact.

    The command string is a proxy; the index is the fact. Every string-level check
    can be walked around (`git -C .claude add -f settings.local.json`, a glob that
    the shell expands after the hook has read the command, `--pathspec-from-file`,
    `git update-index --add`), and none of that matters if the thing that
    publishes the index refuses to run while an artifact is in it.

    So this asks git, at the last moment before the content becomes permanent.
    It is the layer that actually holds.
    """
    if not _INDEX_WRITER_RE.search(command):
        return
    root = common.project_dir(hook_input)
    staged = common.staged_local_artifacts(root)
    if not staged:
        return
    common.block(
        "[praxis] Blocked: a praxis local artifact is staged, so this command "
        "would publish it.\n"
        f"Staged: {', '.join(staged)}\n"
        + _WHY_NOT_COMMITTED + "\n"
        "Unstage it and run the command again:\n"
        f"  git restore --staged {' '.join(staged)}\n"
        "(if the path is already tracked in this repo, `git rm --cached "
        "<path>` removes it from the index without deleting your copy)."
    )


# `git add` over everything rather than over named paths. Quoting and a trailing
# slash are both ordinary (`git add "."`, `git add ./`), so the pathspec is
# matched with its optional quote and separator rather than assumed bare.
_BROAD_STAGE_RE = re.compile(
    r"\bgit\b" + _GIT_OPTS + r"\s+(?:add|stage)\b[^|&;#]*?"
    r"(\s-{1,2}[Aa]\b|\s--all\b|\s--no-ignore-removal\b|\s--pathspec-from-file\b"
    r"|\s['\"]?\.[/\\]?['\"]?(?:\s|$)|\s['\"]?:/|\s['\"]?\*)")

#: `--force` on a stage-everything command. `git add -f` exists precisely to
#: override an exclude file, so the exclusion cannot answer for this case and
#: `git check-ignore` is the wrong question to ask about it.
_FORCED_RE = re.compile(r"\s(?:-{1,2}f\b|--force\b|-[a-zA-Z]*f[a-zA-Z]*\b)")


def check_broad_staging(hook_input, command: str) -> None:
    """Stage-everything is only safe while praxis's files are actually excluded.

    `ensure_local_exclusions` fails open, so a read-only `.git`, a clone made
    before praxis ran, or a hand-deleted block all leave contributor artifacts
    visible to `git add -A`. Rather than assume, ask git; and rather than refuse
    outright, repair the exclusion first and only block if the repair did not take.

    With `--force` there is nothing to verify: the flag's entire purpose is to
    add ignored files, so a present artifact will be staged no matter how good
    the exclusion is, and the only correct answer is no.
    """
    if not _BROAD_STAGE_RE.search(command):
        return
    root = common.project_dir(hook_input)
    if not common.is_contributor(root):
        return
    present = [p for p in common.LOCAL_ARTIFACTS if (root / p).exists()]
    if not present:
        return
    if _FORCED_RE.search(command):
        common.block(
            "[praxis] Blocked: `git add --force` over everything would stage "
            "praxis's local files, because --force exists to override exactly "
            "the exclusion that normally hides them.\n"
            f"Present here: {', '.join(present)}\n"
            + _WHY_NOT_COMMITTED + "\n"
            "Name the paths you actually want to force-add instead."
        )

    exposed = [p for p in present if not common.git_is_ignored(root, p)]
    if exposed:
        common.ensure_local_exclusions(root, True)
        exposed = [p for p in exposed if not common.git_is_ignored(root, p)]
    if not exposed:
        return

    # `git check-ignore` never reports a tracked path as ignored, so an artifact
    # some earlier commit captured looks identical to a broken exclude file.
    # Sending the user to repair a file that is not broken is worse than not
    # blocking at all.
    tracked = set(common.tracked_local_artifacts(root))
    if tracked:
        common.block(
            "[praxis] Blocked: this repository already tracks a praxis local "
            f"artifact ({', '.join(sorted(tracked))}), so no exclusion can hide "
            "it and staging everything will keep committing it.\n"
            + _WHY_NOT_COMMITTED + "\n"
            "Remove it from the index (your copy on disk is kept):\n"
            f"  git rm --cached {' '.join(sorted(tracked))}"
        )
    common.block(
        "[praxis] Blocked: staging everything would commit praxis's local files "
        "into a repository that is not ours.\n"
        f"Not excluded: {', '.join(exposed)}\n"
        "praxis keeps these out of git through the per-clone exclude file and "
        "could not write or repair it here (a read-only .git, or a permission "
        "problem).\n"
        "Stage the paths your change actually touches instead "
        "(`git add <path> ...`), or fix the exclude file and try again."
    )


def check_bash(hook_input, command: str) -> None:
    if not command:
        common.allow()
    # Safety before style: a command that is both destructive and badly credited
    # should be refused for the destructive part, which is the reason that matters.
    for rx, why in _DANGEROUS:
        if rx.search(command):
            common.block(
                f"[praxis] Blocked a high-risk command: {why}.\n"
                f"Command: {command.strip()[:400]}\n"
                "If this is genuinely intended, run it yourself in a terminal, "
                "or narrow the command. praxis will not run irreversible "
                "operations unattended."
            )
    check_attribution(hook_input, command)
    check_local_artifacts(command)
    check_broad_staging(hook_input, command)
    check_staged_index(hook_input, command)
    check_staged_project_artifacts(hook_input, command)
    check_gitignore_shell(hook_input, command)
    check_project_artifact_shell(hook_input, command)
    # Catch reads of sensitive files via shell readers. The sensitive path may be
    # any argument (e.g. `grep SECRET .env` has it last), so scan all tokens of
    # each command segment whose first word is a known reader.
    readers = {"cat", "less", "more", "head", "tail", "xxd", "strings", "nl", "od",
               "grep", "egrep", "fgrep", "rg", "ag", "awk", "sed", "dotenv",
               "source", "."}
    for segment in re.split(r"[;|&]+|&&|\|\|", command):
        toks = segment.strip().split()
        if not toks:
            continue
        if toks[0] in readers:
            for t in toks[1:]:
                if common.is_sensitive_path(t):
                    common.block(
                        f"[praxis] Blocked shell access to a sensitive file: {t}.\n"
                        "Secrets should not enter the model context / shell environment. "
                        "Use a placeholder or a *.env.example instead."
                    )
    common.allow()


_GITIGNORE_RE = re.compile(r"(^|/)\.gitignore$")

_GITIGNORE_REMEDY = (
    "praxis keeps its own artifacts out of git through the per-clone exclude "
    "file (`$GIT_COMMON_DIR/info/exclude`), which is never shared and never "
    "appears in a diff, and it maintains that block itself: nothing is needed "
    "in `.gitignore`.\n"
    "If the rule is genuinely the project's (a build output, a local tool "
    "everyone uses), write it without the praxis paths and say in the PR why "
    "the project needs it."
)


def _mentions_praxis_path(text: str) -> bool:
    return bool(_LOCAL_ARTIFACT_RE.search(text) or ".praxis" in text)


def check_gitignore(hook_input, path: str, tool_input: dict) -> None:
    """In someone else's repo, praxis's paths do not go in their `.gitignore`.

    `.gitignore` is a committed file: adding `.claude/.praxis/` to it is proposing
    praxis's setup to the whole project, which is exactly what contributor mode
    exists to avoid.

    Narrow on purpose, twice over. Only an edit that carries a praxis path is
    refused, so an ordinary ignore rule still goes through. And only an edit that
    *introduces* one: a repo whose `.gitignore` already lists these paths must
    stay editable, and removing a praxis path is the correct cleanup rather than
    a violation, so what the file already says is subtracted first.
    """
    if not _GITIGNORE_RE.search(path.replace("\\", "/")):
        return
    added = " ".join(str(tool_input.get(k, "")) for k in
                     ("content", "new_string", "new_str", "edits"))
    if not _mentions_praxis_path(added):
        return
    try:
        existing = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        existing = ""
    # Lines the file already had are not this edit's doing.
    novel = [ln for ln in added.splitlines()
             if _mentions_praxis_path(ln) and ln.strip() not in existing]
    if not novel:
        return
    if not common.is_contributor(common.project_dir(hook_input)):
        return
    common.block(
        f"[praxis] Blocked: this would add a praxis path to {path}, which is a "
        "committed file in a repository that is not ours.\n"
        f"Adding: {'; '.join(ln.strip() for ln in novel[:5])}\n"
        + _GITIGNORE_REMEDY
    )


#: A shell write into a `.gitignore`: redirection, or an in-place editor.
_GITIGNORE_WRITE_RE = re.compile(
    r">>?\s*\S*\.gitignore\b|\b(?:sed|perl|awk)\b[^|&;#]*-i[^|&;#]*\.gitignore\b"
    r"|\btee\b[^|&;#]*\.gitignore\b", re.IGNORECASE)


def check_gitignore_shell(hook_input, command: str) -> None:
    """The same rule as `check_gitignore`, for the shell route into the file.

    `check_gitignore` only sees Edit/Write. `echo '.claude/.praxis/' >>
    .gitignore` reaches the identical outcome through Bash, and a rule that holds
    for one tool and not the other is not a rule.
    """
    if not _GITIGNORE_WRITE_RE.search(command):
        return
    if not _mentions_praxis_path(command):
        return
    if not common.is_contributor(common.project_dir(hook_input)):
        return
    common.block(
        "[praxis] Blocked: this would add a praxis path to a `.gitignore` that "
        "belongs to a repository we do not own.\n"
        f"Command: {command.strip()[:400]}\n"
        + _GITIGNORE_REMEDY
    )


def check_file_tool(hook_input, tool_input: dict) -> None:
    path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("notebook_path")
        or ""
    )
    if common.is_sensitive_path(path):
        common.block(
            f"[praxis] Blocked access to a sensitive file: {path}.\n"
            "Reading or editing secrets risks leaking them into context or git. "
            "Work against a redacted template (e.g. .env.example) instead."
        )
    check_gitignore(hook_input, path, tool_input)
    check_project_artifact(hook_input, path)
    common.allow()


def main() -> None:
    data = common.read_hook_input()
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool == "Bash":
        check_bash(data, tool_input.get("command", ""))
    elif tool in ("Read", "Edit", "Write", "MultiEdit"):
        check_file_tool(data, tool_input)
    common.allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Never break a session because the guard itself errored.
        common.allow()
