# Architecture

praxis is a single Claude Code plugin, distributed through a one-plugin
marketplace. Its design principle: **checks belong in the lifecycle, not in your
prompts.** Everything you would otherwise retype ("audit for regressions,
duplication, edge cases, follow the docs, don't reinvent…") is compiled into four
layers that fire automatically.

## The four layers

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. OUTPUT STYLE  (praxis-quality)                                   │
│    Modifies the system prompt every turn → mindset always on:       │
│    plan-first, doc-first, complete, structured reporting.           │
├─────────────────────────────────────────────────────────────────────┤
│ 2. SKILLS                                                           │
│    task-orchestrator, prompt-architect, best-practices, code-craft, │
│    bootstrap, quality-rubric, repo-audit, claudemd-living,          │
│    docs-living, capability-discovery, git-delivery                  │
│    Reasoning workflows, auto-invoked when their description matches.│
├─────────────────────────────────────────────────────────────────────┤
│ 3. SUBAGENTS  (read-only, Opus: 7 vertical auditors + verifiers)    │
│    Deep, verbose analysis in isolated context — one concern each.   │
├─────────────────────────────────────────────────────────────────────┤
│ 4. HOOKS  (SessionStart, PreToolUse, PostToolUse, Stop)             │
│    Deterministic gates. SessionStart injects the standing directive;│
│    the Stop gate runs the task-completion loop + per-change quality │
│    gate. The only layer that can block.                             │
└─────────────────────────────────────────────────────────────────────┘
```

Why four layers rather than one big prompt:

- The **output style** guarantees the mindset without spending a user turn.
- **Skills** carry multi-step reasoning and only load when relevant (progressive
  disclosure keeps context lean).
- **Subagents** keep verbose audit reasoning *out* of the main conversation — each
  has its own context window — and are read-only so an audit can never mutate code.
- **Hooks** are the deterministic backbone: they run whether or not the model
  "remembers" to, and a `PreToolUse` deny even holds under
  `--dangerously-skip-permissions`.

## From prompt to production: the pipeline

A terse prompt is turned into a complete change by the `task-orchestrator`. There
is **no prompt-keyword classifier** deciding whether to engage — the workflow is
carried by the always-injected SessionStart directive (and the output style), and
enforced by change-based gates, so it applies regardless of phrasing:

```
user: "fix the pagination bug" + chosen effort
        │  (SessionStart directive + output style already active)
        ▼
  Phase 1  Restructure   prompt-architect → spec (goal/scope/non-goals/criteria)
                         for a multi-step task: task_state.py open (criteria, cap)
  Phase 2  Investigate   read code; repo-cartographer + doc-reference-finder;
                         ensure CLAUDE.md is right (bootstrap/sync)
  Phase 3  Plan          plan mode; no edits until the plan is set
  Phase 4  Implement     to the plan, code-craft standards, reuse over reinvent
  Phase 5  Audit         quality-rubric: 7 verticals (incl. completeness) +
                         horizontal pass; fix every finding; tests green
  Phase 6  Report        canonical structured report; record green report; task done
        │
        ▼
  Stop gate: while a task is open it keeps the session working (turn cap); it also
  refuses to finish while a change is unreviewed. No /goal, no prompt keywords.
```

This is how the session self-drives: the **task-completion loop** in the Stop gate
(state in `task.json`) keeps Claude working until it marks the task done — the
built-in, deterministic replacement for manually running `/goal`. At a genuine
decision point Claude marks the task `waiting_for_user` and the gate lets it stop
to ask.

## Completeness enforcement

"No placeholders, nothing silently out of scope" is enforced at three levels:
- **Deterministic:** `scan_placeholders.py` greps the diff for TODO/FIXME/stub/
  NotImplemented/debug markers (language-agnostic) and feeds the Stop gate's block
  message and the completeness auditor.
- **Semantic:** `@praxis:completeness-auditor` judges each marker, checks every
  acceptance criterion, and flags any scope quietly dropped.
- **Reported:** anything genuinely out of scope must appear in the report's
  "Out of scope / follow-ups" — never hidden in a comment.

## Living knowledge (/docs, CHANGELOG, ADRs)

Praxis keeps a project's knowledge current with every change, enforced as part of
"done":
- **`docs-living` skill** runs read → update/create → changelog → ADR for each
  change; **bootstrap** scaffolds `/docs` + `CHANGELOG.md` + `docs/adr/` when
  missing.
- **`changelog.py`** maintains a Keep-a-Changelog `[Unreleased]` section;
  **`adr.py`** records Architecture Decision Records (auto-pilot persists its
  autonomous decisions here).
- The **completeness-auditor** fails a change whose docs/changelog weren't updated;
  **session_audit** and **doctor** report when `/docs` or `CHANGELOG.md` is absent.

See `docs/KNOWLEDGE.md` for the full model.

## Repo-wide scan (`/praxis:scan`)

The change-audit machinery generalises to whole repositories via the
`repo-audit` skill: `repo_scan.py` builds a deterministic shard ledger
(inventory → shards → per-shard × dimension tracking → finding lifecycle), the
seven vertical auditors run over every shard, and the `finding-verifier`
subagent reverse-audits each finding before anything is fixed. Coverage claims
come from recorded state — an unaudited shard makes the final report print
INCOMPLETE. See `docs/SCAN.md`.

## Vertical vs horizontal

- **Vertical analysis** = one subagent per concern, deep and isolated:
  `adversarial`, `regression`, `duplication`, `performance`, `edge-case`,
  `doc-reference`, `completeness`. Each returns `PASS / PASS WITH NOTES / FAIL`.
- **Horizontal analysis** = the `quality-rubric` skill's cross-cutting pass over
  the whole change for consistency, use-case coverage, and guideline compliance,
  looping until every vertical is green.

## The quality gate loop

```
edit code ──▶ PostToolUse: auto-format + secret tripwire
   │
   ▼
turn ends ──▶ Stop hook (quality_gate.py):
              dirty tree AND no green report for this exact change signature?
                 ├─ yes → exit 2 → Claude keeps working → runs quality-rubric
                 │                    │
                 │                    ▼
                 │            dispatch vertical auditors → fix FAILs → re-run
                 │                    │
                 │                    ▼
                 │            all green → write quality_report.json (signed)
                 │                    │
                 │                    ▼
                 │            next Stop → report matches signature → allow
                 └─ no  → allow
```

The **change signature** (`common.change_signature`) hashes HEAD + the dirty file
set + sizes/mtimes, so a green report is valid only for the exact state it was
produced against. Editing again re-keys the signature and re-arms the gate.

Loop safety: the gate prompts at most once per signature per session
(`gate_notified.json`), so it enforces review without trapping the agent, and it
honours the `skip-gate` file and `PRAXIS_GATE=off` escapes.

## Universal onboarding

`session_audit.py` classifies the repo on every `SessionStart` and injects the
verdict into context:

| State | Meaning | Route |
| --- | --- | --- |
| `new` | empty/near-empty | full bootstrap |
| `uninitialised` | real code, no Claude setup | analyse then bootstrap |
| `legacy` | CLAUDE.md without the praxis marker | reconcile + migrate via verifier |
| `partial` | some `.claude/` config | doctor reconcile |
| `managed` | praxis marker present | gates active, patch drift only |

## Language-agnostic by construction

praxis ships **workflow and rubric**, not language rules. Skills and agents are
written as *reasoning* ("derive the build system from what's present", "check
against the authoritative docs for the version in use"), so the same
`regression-sentinel` reasons about Rust, Elixir, or COBOL — the model supplies
the language specifics at runtime. The only place concrete tools appear is
`post_edit.py`'s formatter table, and that degrades silently when a tool is
absent.

## File map

```
.claude-plugin/marketplace.json      one-plugin marketplace catalog
plugins/praxis/
  .claude-plugin/plugin.json         plugin manifest
  output-styles/praxis-quality.md     always-on doctrine
  skills/*/SKILL.md                  task-orchestrator, prompt-architect, code-craft,
                                     bootstrap, quality-rubric, claudemd-living,
                                     capability-discovery
  agents/*.md                        ten read-only subagents (7 verticals +
                                     finding-verifier + repo-cartographer +
                                     claudemd-verifier)
  hooks/hooks.json                   lifecycle wiring (command hooks)
  scripts/*.py                       hook implementations + utilities (stdlib only)
  scripts/lib/common.py              shared, defensive helpers
  templates/*                        CLAUDE.md, settings, MCP starting points
```

## Swapping in native LLM hooks (optional)

praxis drives its LLM review through skills + subagents and enforces it with a
deterministic `command` Stop hook — a design that only uses documented,
universally-available hook mechanics. If your Claude Code version exposes `prompt`
or `agent` hook handler types, you can wire an LLM verdict *directly* into the
Stop event instead of via the marker file. That is a drop-in change to
`hooks/hooks.json`; the rest of the harness is unaffected.
