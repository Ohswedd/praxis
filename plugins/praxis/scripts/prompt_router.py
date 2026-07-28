#!/usr/bin/env python3
"""
praxis UserPromptSubmit router.

The gap this closes: praxis's discipline used to be announced once, at
SessionStart. Skill selection then depended on the model spontaneously matching
a skill description against the prompt, which works for `/praxis:task` but
degrades badly for a bare prompt like "add rate limiting" ten turns into a long
session, when the SessionStart block is far behind in the context.

This hook runs on *every* user prompt. It classifies the request from its text
and injects a short, explicit routing directive naming the exact skills to
invoke for that request, so the pipeline engages without the user having to type
a command. Two facts ride along with the routing because both expire from context
and both change what a turn may do: that praxis has not been set up here yet, and
that this repository is somebody else's. It is deliberately:

  * silent for conversational prompts (questions, explanations, chit-chat):
    routing noise on "what does this file do?" would be worse than useless;
  * short (a routing block, not a re-statement of the doctrine): the output
    style already carries the principles, this only carries the *routing*;
  * additive: it never blocks and never rewrites the prompt.

Classification is keyword/shape based and errs toward routing: a false positive
costs a few lines of context, a false negative costs the whole pipeline.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import common  # noqa: E402


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
# Verbs that mean "change the code-base". Matched as whole words on the prompt.
_IMPLEMENT_VERBS = r"""
add|create|build|implement|write|introduce|scaffold|generate|
fix|repair|resolve|debug|patch|solve|
change|update|modify|edit|adjust|tweak|rename|replace|
refactor|restructure|rewrite|clean\s*up|simplify|extract|
design|redesign|restyle|document|
integrate|connect|wire|hook\s*up|set\s*up|configure|install|
migrate|port|upgrade|bump|convert|
optimi[sz]e|speed\s*up|harden|secure|
remove|delete|drop|deprecate|
enable|disable|
improve|enhance|extend|finish|complete|make
"""

_IMPLEMENT_RE = re.compile(r"\b(" + _IMPLEMENT_VERBS + r")\b", re.IGNORECASE | re.VERBOSE)

# User-facing interface surface. Deliberately broad: the cost of running the
# front-end pipeline's `patch` route on a non-UI change is one skill read, while
# the cost of missing a UI change is a page that was built without a brief, a
# story, or a design system, which is exactly how generic output happens.
_UI_RE = re.compile(
    r"\b(ui|ux|front[\s-]?end|frontend|interface|design|redesign|restyle|styling|styles?|"
    r"css|tailwind|scss|sass|less|styled[\s-]?components|shadcn|mui|chakra|bootstrap|"
    r"theme|dark\s*mode|light\s*mode|responsive|layout|breakpoints?|viewport|mobile|"
    r"page|pages|landing|homepage|hero|website|site|web\s*app|storefront|shop|store|"
    r"checkout|cart|pricing|portfolio|blog|marketing|lead\s*(page|form)|onboarding|"
    r"dashboard|admin\s*panel|back[\s-]?office|cms|crm|screen|screens|view|views|"
    r"component|components|widget|button|buttons|form|forms|input|modal|dialog|drawer|"
    r"nav|navbar|navigation|menu|sidebar|header|footer|table|card|cards|tabs?|toast|"
    r"tooltip|carousel|accordion|banner|badge|avatar|skeleton|spinner|empty\s*state|"
    r"typography|font|fonts|colou?r|colou?rs|palette|spacing|icon|icons|logo|favicon|"
    r"animation|transition|micro[\s-]?interaction|chart|charts|graph|visuali[sz]ation|"
    r"accessibility|a11y|wcag|aria|contrast|keyboard\s*nav|screen\s*reader|"
    r"design\s*system|design\s*tokens?|style\s*guide|wireframes?|mockups?|figma|brand|"
    r"react|vue|svelte|next\.?js|nuxt|astro|remix|angular|solid[\s-]?js|qwik|htmx|"
    r"storybook|html|jsx|tsx)\b",
    re.IGNORECASE,
)

# A file the prompt names directly. "fix src/components/Header.tsx" is UI work no
# matter which words surround it, and this catches the case where the prompt
# carries a path instead of a noun.
_UI_PATH_RE = re.compile(
    r"[\w./-]+\.(html?|css|s[ca]ss|less|jsx|tsx|vue|svelte|astro|mdx|"
    r"njk|hbs|ejs|pug|liquid|erb|twig)\b",
    re.IGNORECASE,
)

_REVIEW_RE = re.compile(
    r"\b(review|audit|check|verify|validate|inspect|assess|critique|"
    r"code[\s-]?review|quality\s*(check|pass)|is\s+this\s+(ok|correct|safe|good))\b",
    re.IGNORECASE,
)

_SCAN_RE = re.compile(
    r"\b(whole|entire|all\s+the|across\s+the|repo[\s-]?wide|code[\s-]?base[\s-]?wide)\b"
    r".{0,40}\b(repo|repository|code[\s-]?base|project|files)\b"
    r"|\b(scan|sweep|health[\s-]?check)\b.{0,30}\b(repo|repository|code[\s-]?base|project)\b",
    re.IGNORECASE,
)

_DELIVER_RE = re.compile(
    r"\b(commit|push|open\s+a?\s*pr|pull\s+request|ship|release|merge|tag|publish)\b",
    re.IGNORECASE,
)

_DOCS_RE = re.compile(
    r"\b(document|documentation|docs|readme|changelog|adr|comment\s+the)\b",
    re.IGNORECASE,
)

# Prompts that ask for information rather than for work. An opening
# interrogative wins over any verb in the sentence: "how do I add caching?" is a
# question about adding caching, not an instruction to add it. Polite-modal
# requests ("can you fix…", "could you add…") are deliberately NOT in this list:
# they are ordinary requests wearing a question mark.
_INFO_QUESTION_RE = re.compile(
    # An optional politeness/vocative opener, so "please explain how X works" is
    # still recognised as a question rather than falling through to the verbs in
    # its own explanation and being routed as an implementation request.
    r"^\s*(please|pls|hey|hi|hello|ok|okay|so|and|but|quick\s+question|question)?[\s,:]*"
    r"(can\s+you\s+|could\s+you\s+|would\s+you\s+)?"
    r"(what|what's|whats|why|how|who|whom|when|where|which|whose|"
    r"explain|describe|clarify|tell\s+me|show\s+me|walk\s+me|summari[sz]e|compare|"
    r"help\s+me\s+understand|any\s+idea|thoughts\s+on|do\s+you\s+(know|think))\b",
    re.IGNORECASE,
)

# An explicit "look, don't touch" instruction outranks every verb in the prompt.
_READ_ONLY_RE = re.compile(
    r"\b(don'?t|do\s+not|no\s+need\s+to|without)\s+(change|changing|modify|modifying|"
    r"edit|editing|implement|implementing|touch|touching|writ(e|ing))\b"
    r"|\b(read[\s-]only|just\s+(look|read|check)|no\s+changes)\b",
    re.IGNORECASE,
)

# Slash-command prompts route themselves: the command file is the instruction.
_SLASH_RE = re.compile(r"^\s*/\S")

# Trivially short acknowledgements ("yes", "go ahead", "thanks").
_ACK_RE = re.compile(
    r"^\s*(y|yes|yep|yeah|ok|okay|sure|go|go\s+ahead|continue|proceed|do\s+it|"
    r"thanks|thank\s+you|ty|no|nope|stop|wait)\b[\s.!]*$",
    re.IGNORECASE,
)


def classify(prompt: str) -> dict:
    """Return the routing decision for a prompt.

    Keys: `route` (implement | review | scan | deliver | none), plus the
    booleans `ui` and `docs` that add skills on top of the base route.
    """
    text = (prompt or "").strip()
    decision = {"route": "none", "ui": False, "docs": False}
    if not text or _SLASH_RE.match(text) or _ACK_RE.match(text):
        return decision
    if _INFO_QUESTION_RE.match(text) or _READ_ONLY_RE.search(text):
        return decision  # asking about the code, not asking for a change

    implements = bool(_IMPLEMENT_RE.search(text))

    if _SCAN_RE.search(text) and (implements or _REVIEW_RE.search(text)):
        decision["route"] = "scan"
    elif implements:
        decision["route"] = "implement"
    elif _REVIEW_RE.search(text):
        decision["route"] = "review"
    elif _DELIVER_RE.search(text):
        decision["route"] = "deliver"
    else:
        return decision

    decision["ui"] = bool(_UI_RE.search(text) or _UI_PATH_RE.search(text))
    decision["docs"] = bool(_DOCS_RE.search(text))
    return decision


# --------------------------------------------------------------------------- #
# Directive rendering
# --------------------------------------------------------------------------- #
_TASK_CMD = ('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" open "<title>" '
             '--criteria "..." --max <N>')


def _bootstrap_directive(root) -> list:
    """Set the repo up before working in it, restated on every actionable prompt.

    SessionStart already says this, but by the tenth turn that block is far behind
    in the context and the instruction has effectively expired. It is repeated
    here, on the prompts that are about to change something, and deliberately not
    on conversational ones: answering "what does this file do?" does not require
    writing a CLAUDE.md first, and the router's silence on questions is a property
    worth keeping.
    """
    try:
        if not common.bootstrap_required(root):
            return []
        where = common.bootstrap_targets(root)
    except Exception:
        return []
    return [
        "**praxis is not set up in this repository. Run the `bootstrap` skill "
        "FIRST, in this turn, before touching the request below.** Map the repo "
        f"read-only, then write {where}. Write what does not exist without asking "
        "and carry straight on to the request; the only thing worth stopping for "
        "is reconciling an existing non-praxis `CLAUDE.md`, which goes through "
        "`@praxis:claudemd-verifier`.",
        "",
    ]


def _contributor_directive(root) -> list:
    """Where this turn is allowed to write when the repository is not ours."""
    try:
        if not common.is_contributor(root):
            return []
    except Exception:
        return []
    return [
        "",
        "**Workspace is `contributor`: this repository is not ours.** Everything "
        "praxis authors stays local and git-excluded: the brief is "
        "`CLAUDE.local.md`, settings are `.claude/settings.local.json`, and "
        "`/docs`, `CHANGELOG.md`, `docs/adr/` and `docs/design/` are updated only "
        "if the repo already has them (following its conventions), otherwise "
        "written under `.claude/.praxis/knowledge/`. Do not create a `CLAUDE.md`, "
        "a `.praxis.toml`, a `/docs` tree or a `CHANGELOG.md` here, do not edit "
        "`.gitignore`, and never stage a praxis artifact: the commit carries the "
        "user's change and nothing else.",
    ]


def render(decision: dict, root) -> str:
    route = decision["route"]
    if route == "none":
        return ""

    lines = ["## praxis routing (this request)", ""]
    lines += _bootstrap_directive(root)

    if route == "implement":
        lines += [
            "This is an **implementation request**. Do not start editing files. Run the "
            "`task-orchestrator` skill: it is mandatory here, not optional:",
            "1. `prompt-architect` → spec (goal, scope, non-goals, acceptance "
            "criteria), and, if this request has more than one deliverable, an "
            "ordered plan: one subtask per commit, in dependency order.",
            "2. Investigate: read the affected code and the authoritative docs "
            "(`doc-reference-finder`) before writing anything.",
            "3. Plan mode for anything beyond a one-line edit.",
            "4. Implement with `best-practices` + `code-craft`. **Production-complete, "
            "not an MVP**: no TODOs, no stubs, no \"for now\", no \"in a real "
            "implementation\". If something is genuinely out of scope, say so in the "
            "report, never leave it implied in the code.",
            "5. `quality-rubric` (all verticals, including `debt`: what this change "
            "costs later, and whether any of it was recorded). Scope it with "
            "`scope.py`, never `git diff` alone: on a branch that has committed "
            "anything `git diff` is empty and every auditor passes on nothing. "
            "Fix every finding.",
            "6. `docs-living`: /docs + CHANGELOG [Unreleased] + ADR if the decision was "
            "significant or taken autonomously.",
            "7. Record the report LAST: it is keyed to the change signature, so any "
            "file written after it invalidates the audit.",
            f"Open a praxis task first if this is multi-step: `{_TASK_CMD}` (use "
            "`--subtasks` for the plan). Deliver it as one branch and one pull "
            "request, each subtask its own commit.",
        ]
    elif route == "review":
        lines += [
            "This is a **review request**. Run the `quality-rubric` skill in full: "
            "dispatch the vertical auditors as subagents rather than eyeballing the "
            "diff yourself, then the horizontal pass, then record the report.",
        ]
    elif route == "scan":
        lines += [
            "This is a **repo-wide** request. Run the `repo-audit` skill "
            "(`/praxis:audit repo`): shard the repo into a coverage ledger, audit every "
            "shard, adversarially verify each finding with `@praxis:finding-verifier` "
            "before acting on it, and report coverage honestly, never imply coverage you "
            "did not achieve.",
        ]
    elif route == "deliver":
        lines += [
            "This is a **delivery request**. Run the `git-delivery` skill: Conventional "
            "Commit, branch, PR.",
            _delivery_policy(root),
        ]

    if decision["ui"]:
        lines += [
            "",
            "**This request touches user-facing UI** → the `frontend-pipeline` skill is "
            "mandatory (Phase 0 sizes it: `full` / `feature` / `patch`). Read its "
            "`reference/craft.md` before writing any markup or styles: it is what "
            "separates a designed interface from generic AI output: name the focal "
            "element of each screen, derive every token from the brief, write real copy, "
            "and design the empty/loading/error states. The gate enforces the rest: the "
            "report is not green without `accessibility=pass` and "
            "`design-consistency=pass`.",
        ]
    if decision["docs"]:
        lines += [
            "",
            "**Documentation is in scope** → use the `docs-living` skill; read the "
            "existing docs before writing so nothing already documented is lost.",
        ]

    lines += _contributor_directive(root)

    try:
        if common.autopilot_on(root):
            lines += [
                "",
                "**Auto-pilot is ON:** resolve every design/approach decision yourself "
                "via `best-practices` and record it under \"Decisions taken "
                "autonomously\". Stop only for a hard external blocker.",
            ]
    except Exception:
        pass

    lines += [
        "",
        "**House style:** no em dashes in anything you write, including this reply "
        "(use a colon, a comma, parentheses, or two sentences); no AI co-author "
        "trailer or \"generated with\" credit in any commit, PR, tag, or release. "
        "Both are checked deterministically, not by trust.",
    ]
    return "\n".join(lines)


def _delivery_policy(root) -> str:
    """The merge policy actually in force, resolved rather than recalled.

    The router states this instead of the model inferring it from a doc, because
    documentation of a toggle goes stale the moment the toggle is flipped and the
    resulting confident-but-wrong statement is exactly what this closes.
    """
    try:
        if common.is_contributor(root):
            # Merging is not ours to do in someone else's project, whatever the
            # local toggle says: the maintainers review and merge.
            return ("This repository is **not ours** (`contributor` mode): deliver a "
                    "clean topic branch and a pull request that matches the project's "
                    "own commit, PR and changelog conventions, and stop there. Never "
                    "merge, and never let a praxis artifact "
                    "(`CLAUDE.local.md`, `.claude/.praxis/`, "
                    "`.claude/settings.local.json`) into the commit.")
        if common.auto_merge_on(root):
            return ("Auto-merge is **ON** for this repo: after a green audit and passing "
                    "checks, self-review the diff and merge with "
                    "`gh pr merge --squash --delete-branch` (or `--auto` while checks "
                    "run). Never bypass branch protection.")
        return ("Auto-merge is **OFF** for this repo: open the PR, report its URL, and "
                "leave the merge to a human. Do not merge.")
    except Exception:
        return ("Check the merge policy with `config.py status` before merging "
                "anything; never merge without a green audit.")


def main() -> None:
    data = common.read_hook_input()
    prompt = data.get("prompt", "") or ""
    root = common.project_dir(data)
    try:
        directive = render(classify(prompt), root)
    except Exception:
        directive = ""
    if directive:
        common.emit_context(directive)
    common.allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        common.allow()
