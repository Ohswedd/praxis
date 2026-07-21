#!/usr/bin/env python3
"""
praxis UserPromptSubmit router.

The gap this closes: praxis's discipline used to be announced once, at
SessionStart. Skill selection then depended on the model spontaneously matching
a skill description against the prompt — which works for `/praxis:task` but
degrades badly for a bare prompt like "add rate limiting" ten turns into a long
session, when the SessionStart block is far behind in the context.

This hook runs on *every* user prompt. It classifies the request from its text
and injects a short, explicit routing directive naming the exact skills to
invoke for that request, so the pipeline engages without the user having to type
a command. It is deliberately:

  * silent for conversational prompts (questions, explanations, chit-chat) —
    routing noise on "what does this file do?" would be worse than useless;
  * short (a routing block, not a re-statement of the doctrine) — the output
    style already carries the principles, this only carries the *routing*;
  * additive — it never blocks and never rewrites the prompt.

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
# front-end pipeline's `patch` route on a non-UI change is one skill read.
_UI_RE = re.compile(
    r"\b(ui|ux|front[\s-]?end|frontend|interface|design|redesign|styling|styles?|"
    r"css|tailwind|scss|sass|theme|dark\s*mode|responsive|layout|"
    r"page|pages|landing|homepage|hero|website|site|storefront|shop|checkout|"
    r"dashboard|admin\s*panel|cms|crm|screen|screens|view|"
    r"component|components|button|form|modal|nav|navbar|menu|sidebar|table|card|"
    r"typography|font|fonts|colou?r|colou?rs|palette|spacing|animation|"
    r"react|vue|svelte|next\.?js|nuxt|astro|remix|angular|html)\b",
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
# requests ("can you fix…", "could you add…") are deliberately NOT in this list —
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

# Slash-command prompts route themselves — the command file is the instruction.
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

    decision["ui"] = bool(_UI_RE.search(text))
    decision["docs"] = bool(_DOCS_RE.search(text))
    return decision


# --------------------------------------------------------------------------- #
# Directive rendering
# --------------------------------------------------------------------------- #
_TASK_CMD = ('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" open "<title>" '
             '--criteria "..." --max <N>')


def render(decision: dict, root) -> str:
    route = decision["route"]
    if route == "none":
        return ""

    lines = ["## praxis routing (this request)", ""]

    if route == "implement":
        lines += [
            "This is an **implementation request**. Do not start editing files. Run the "
            "`task-orchestrator` skill — it is mandatory here, not optional:",
            "1. `prompt-architect` → spec (goal, scope, non-goals, acceptance criteria).",
            "2. Investigate: read the affected code and the authoritative docs "
            "(`doc-reference-finder`) before writing anything.",
            "3. Plan mode for anything beyond a one-line edit.",
            "4. Implement with `best-practices` + `code-craft`. **Production-complete, "
            "not an MVP**: no TODOs, no stubs, no \"for now\", no \"in a real "
            "implementation\". If something is genuinely out of scope, say so in the "
            "report — never leave it implied in the code.",
            "5. `quality-rubric` (all verticals) → fix every finding.",
            "6. `docs-living`: /docs + CHANGELOG [Unreleased] + ADR if the decision was "
            "significant or taken autonomously.",
            "7. Record the report LAST — it is keyed to the change signature, so any "
            "file written after it invalidates the audit.",
            f"Open a praxis task first if this is multi-step: `{_TASK_CMD}`.",
        ]
    elif route == "review":
        lines += [
            "This is a **review request**. Run the `quality-rubric` skill in full — "
            "dispatch the vertical auditors as subagents rather than eyeballing the "
            "diff yourself, then the horizontal pass, then record the report.",
        ]
    elif route == "scan":
        lines += [
            "This is a **repo-wide** request. Run the `repo-audit` skill "
            "(`/praxis:scan`): shard the repo into a coverage ledger, audit every shard, "
            "adversarially verify each finding with `@praxis:finding-verifier` before "
            "acting on it, and report coverage honestly — never imply coverage you "
            "did not achieve.",
        ]
    elif route == "deliver":
        lines += [
            "This is a **delivery request**. Run the `git-delivery` skill: Conventional "
            "Commit, branch, PR. Do not merge unless auto-merge is on, and never "
            "without a green audit.",
        ]

    if decision["ui"]:
        lines += [
            "",
            "**This request touches user-facing UI** → the `frontend-pipeline` skill is "
            "mandatory (Phase 0 sizes it: `full` / `feature` / `patch`). Read its "
            "`reference/craft.md` before writing any markup or styles — it is what "
            "separates a designed interface from generic AI output. The audit gains the "
            "`accessibility` and `design-consistency` verticals; the report is not green "
            "without them.",
        ]
    if decision["docs"]:
        lines += [
            "",
            "**Documentation is in scope** → use the `docs-living` skill; read the "
            "existing docs before writing so nothing already documented is lost.",
        ]

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

    return "\n".join(lines)


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
