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
│    frontend-pipeline, bootstrap, quality-rubric, repo-audit,        │
│    claudemd-living, docs-living, capability-discovery, git-delivery │
│    Reasoning workflows, auto-invoked when their description matches.│
├─────────────────────────────────────────────────────────────────────┤
│ 3. SUBAGENTS  (read-only, Opus: 10 vertical auditors + verifiers)    │
│    Deep, verbose analysis in isolated context, one concern each.   │
├─────────────────────────────────────────────────────────────────────┤
│ 4. HOOKS  (SessionStart, UserPromptSubmit, PreToolUse,             │
│           PostToolUse, Stop)                                        │
│    Deterministic gates. SessionStart injects the standing directive;│
│    UserPromptSubmit routes each request to the skills it needs;     │
│    the Stop gate runs the task-completion loop + per-change quality │
│    gate. The only layer that can block.                             │
└─────────────────────────────────────────────────────────────────────┘
```

Why four layers rather than one big prompt:

- The **output style** guarantees the mindset without spending a user turn.
- **Skills** carry multi-step reasoning and only load when relevant (progressive
  disclosure keeps context lean).
- **Subagents** keep verbose audit reasoning *out* of the main conversation, each
  has its own context window, and are read-only so an audit can never mutate code.
- **Hooks** are the deterministic backbone: they run whether or not the model
  "remembers" to, and a `PreToolUse` deny even holds under
  `--dangerously-skip-permissions`.

## From prompt to production: the pipeline

A terse prompt is turned into a complete change by the `task-orchestrator`. There
is **no prompt-keyword classifier** deciding whether to engage: the workflow is
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
  Phase 5  Audit         quality-rubric: 8 verticals (incl. completeness) +
                         accessibility & design-consistency on UI changes +
                         horizontal pass; fix every finding; tests green
  Phase 6  Report        canonical structured report; record green report; task done
        │
        ▼
  Stop gate: while a task is open it keeps the session working (turn cap); it also
  refuses to finish while a change is unreviewed. No /goal, no prompt keywords.
```

This is how the session self-drives: the **task-completion loop** in the Stop gate
(state in `task.json`) keeps Claude working until it marks the task done: the
built-in, deterministic replacement for manually running `/goal`. At a genuine
decision point Claude marks the task `waiting_for_user` and the gate lets it stop
to ask.

## Completeness enforcement

"No placeholders, nothing silently out of scope" is enforced at three levels:
- **Deterministic:** `scan_placeholders.py` scans the change for TODO/FIXME/stub/  <!-- praxis:ack: the rule has to name the markers it looks for -->
  NotImplemented/debug markers and for deferral prose, language-agnostically, and  <!-- praxis:ack -->
  feeds the Stop gate's block message and the completeness auditor. "The change"
  is everything this branch has committed since it left its base, plus the
  working tree, plus every untracked file: a file created during the work is
  untracked until it is staged, and work that has been committed appears in no
  diff at all, so a scanner reading only `git diff` sees neither.
- **Semantic:** `@praxis:completeness-auditor` judges each marker, checks every
  acceptance criterion, and flags any scope quietly dropped.
- **Reported:** anything genuinely out of scope must appear in the report's
  "Out of scope / follow-ups", never hidden in a comment. That section is for
  what the user excluded, not for work that was started and abandoned.

## House style, enforced rather than requested

Two rules had been stated in the doctrine for several versions and were still
broken regularly, because a prose instruction is easy to agree with and easy to
forget at the moment it applies. Both are now checked by code:

- **No em dashes.** As a sentence break the em dash is the most recognisable tell
  of unedited generated prose, and a colon, a comma, parentheses, or a full stop
  always says the same thing more precisely. `scan_style.py` scans the change and
  the Stop gate refuses the turn. The spaced en dash goes with it; the unspaced en
  dash of a numeric range is correct typography and is left alone.
- **No AI attribution.** A `Co-Authored-By: Claude` trailer or a "generated with"  <!-- praxis:ack: the rule has to name the shape it refuses -->
  credit hands the project's authorship to the tool that typed it. `guard_paths.py`
  blocks the `git commit`, `git tag`, `gh pr create`, `gh release create` or
  `gh issue` command outright, because a prose reminder fails exactly once and the
  credit is then in the history for good.

`praxis:ack` on a line exempts a genuine case, such as a fixture that must contain
the character. `[style] ban_em_dash` and `[style] ban_ai_attribution` turn each
off per repo. `selfcheck.py` holds praxis's own content to both rules, so the
plugin cannot ship what it refuses elsewhere.

## Self-check: two scopes

`selfcheck.py` answers two different questions and must not confuse them.

**Plugin scope** is everything that travels inside the installed plugin: the
manifest parses, hooks point at scripts that exist, frontmatter is valid YAML,
every script compiles, every `/praxis:` and `scripts/` reference resolves, and
the shipped text obeys the house style. This is what `/praxis:doctor` asks on a
user's machine.

**Repo scope** adds what exists only in the source checkout: the enclosing
marketplace manifest, its version agreement with the plugin, its source paths,
and the repo prose (README, CONTRIBUTING, `/docs`) held to the same house style.
This is what CI asks before publishing.

Scope is detected from whether a marketplace manifest that *actually publishes
this plugin* sits above it, not from a file merely existing two levels up: a
plugin unpacked inside an unrelated repository must not be cross-checked against
that repository's marketplace. `--require-repo` turns the detection into an
assertion, which is what `make check` and CI use, so the check cannot silently
fall back to the smaller scope and report OK for a tree whose marketplace is
missing, unreadable, or no longer lists the plugin. Both the self-check and the
doctor name the scope they covered, because an unqualified OK would imply
coverage that was never attempted.

## Documentation drift

Documentation rots in one predictable way: it states as a constant something that
is really configuration or code, and then the configuration or the code moves.
The canonical case is a document that says praxis opens a pull request and leaves
the merge to a human, written while `auto_merge` was off and still read as
authoritative long after someone turned it on.

`drift.py` closes that loop mechanically. It compares what a repo's instruction
documents (CLAUDE.md, README, `/docs`) assert against the configuration actually
in force, and checks that every documented command, slash command, and link still
resolves. A sentence that qualifies itself ("with auto-merge off, praxis stops at
the PR") is not drift; only an unqualified claim about the state currently in
force is, which keeps the report small enough to act on. The SessionStart audit
prints the resolved values every session and surfaces any drift, so no turn has
to trust a document at all; `/praxis:doctor` reports the same on demand, and
`/praxis:docs` fixes what it finds.

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

## Repo-wide scan (`/praxis:audit repo`)

The change-audit machinery generalises to whole repositories via the
`repo-audit` skill: `repo_scan.py` builds a deterministic shard ledger
(inventory → shards → per-shard × dimension tracking → finding lifecycle), the
eight vertical auditors run over every shard, and the `finding-verifier`
subagent reverse-audits each finding before anything is fixed. Coverage claims
come from recorded state: an unaudited shard makes the final report print
INCOMPLETE. See `docs/SCAN.md`.

## Front-end pipeline

The same doctrine extends to design work via the `frontend-pipeline` skill:
business research (client call → goals → audience → competitors → positioning
→ messaging) → story-first wireframes → design system → development through
the task-orchestrator → optimization → ship, proportional to task size (full /
feature / patch routing). The design artifacts (`docs/design/BRIEF.md`,
`WIREFRAMES.md`, `DESIGN-SYSTEM.md`) live in the target repo under the
docs-living contract, and UI-touching changes add two vertical auditors:
`accessibility-auditor` (WCAG 2.2 AA) and `design-consistency-auditor`
(tokens, scales, component reuse, states, responsiveness, story fidelity):
to the rubric and the recorded report. See `docs/FRONTEND.md`.

**The trigger is the surface, not the wording.** "Fix the checkout bug" and
"update `Header.tsx`" are front-end work, and relying on the request to announce
itself as design work is how UI changes ended up skipping the pipeline. Two
mechanisms decide it instead of the phrasing: the prompt router matches interface
vocabulary *and* file extensions in the prompt, and the gate resolves the question
from the changed file list (`common.is_ui_path`: markup, styles, component
suffixes, token and theme configs, `docs/design/`). A change touching any of them
is not green without `accessibility=pass` and `design-consistency=pass`, recorded
by `report.py`, which applies the same rule at record time so the failure is
reported where it can still be acted on cheaply.

There is deliberately **no command** for this pipeline. 2.x shipped
`/praxis:frontend`; 3.0 removed it, because a command is a fourth way to start <!-- praxis:ack: naming the removed command is the point of this paragraph -->
something the other three already decide from files, and the only ways it could
differ from them were both wrong: typed after the design decisions had been made,
or not typed at all for a request that never mentioned design. See ADR-0020.

## Workspace modes: owner and contributor

praxis writes real files into a project. In your own repository that is the
point; in a repository you only contribute to, every one of them is a file the
project never asked for, one `git add -A` away from a polluted pull request.

`common.workspace_mode()` resolves the question the same way every other setting
resolves: `PRAXIS_MODE`, then `.claude/.praxis/workspace`, then `.praxis.toml`,
then detection. Detection is offline and asks whether the address configured to
commit here has ever committed here: a repo with a remote, real history, and no
commit from your git email is somebody else's. Every uncertain case (no remote,
no configured email, barely any history, not a repo) resolves to `owner`, which
is the behaviour praxis has always had.

The mode moves the paths rather than adding a code path at each call site:
`brief_path`, `settings_path`, `knowledge_root` and `knowledge_path` are the
single place the decision is made, and `repo_state`, `bootstrap`, `changelog.py`,
`adr.py`, the doctor and the skills all read through them.

`knowledge_path` carries the one rule that is not a straight substitution: in
`contributor` mode, praxis joins a `/docs`, `CHANGELOG.md` or `docs/adr/` the
project already has (a pull request that skipped the project's changelog is a
worse pull request), and creates none that it does not, keeping those records
under `.claude/.praxis/knowledge/` instead.

Containment is three layers, because directives alone had already proved
insufficient for the house style:

1. `ensure_local_exclusions` writes a marked block into `$GIT_COMMON_DIR/info/exclude`,
   the file gitignore(5) reserves for per-clone patterns that are never shared.
   Excluded artifacts are invisible to `git status`, unreachable by `git add -A`,
   and absent from `changed_files()`, so they cannot be committed and cannot make
   the Stop gate see a dirty tree.
2. `guard_paths.py` refuses any command that stages `CLAUDE.local.md`,
   `.claude/.praxis/` or `.claude/settings.local.json` (in either mode: they are
   never the project's), refuses to write a praxis path into a `.gitignore` that
   is not ours, and verifies rather than assumes on a stage-everything command,
   repairing a missing exclusion and blocking only if the repair fails.
3. The session audit, the prompt router and the skills state the mode and the
   artifact map, so the correct path is used first rather than caught last.

## Review scope: the branch, not the working tree

praxis used to define "the change" as the working tree: the unstaged diff, the
staged diff, and untracked files. That definition has a hole that widens as the
delivery discipline improves. One `git commit` empties every diff it reads, so
the scanners find nothing, the auditors review nothing, and the Stop gate opens.
With one commit per subtask, most of a task's life is spent in that state.

`common.review_base()` resolves the merge-base with the integration branch, and
`changed_files`, `added_line_pairs`, `change_signature` and `review_pending` all
cover the range from there to HEAD as well as the working tree. Every existing
consumer therefore sees committed work without knowing anything new. On the
integration branch there is no range, and the behaviour is exactly as before.

`scope.py` prints the base, the commits, the files and the diff commands, so the
rubric and each subagent work from one resolved answer rather than each guessing.
The regression auditor reads the commits **in order**, because its question is
about differences between states: a signature changed in one commit with its
callers updated in another is fine, and the same change with the callers never
updated is a regression that a squashed diff makes no easier to see.

## Vertical vs horizontal

- **Vertical analysis** = one subagent per concern, deep and isolated:
  `adversarial`, `regression`, `duplication`, `performance`, `edge-case`,
  `doc-reference`, `debt`, `completeness`, plus `accessibility` and
  `design-consistency` when the change touches UI surface. Each returns
  `PASS / PASS WITH NOTES / FAIL`. The `debt` vertical is the only one that asks
  about later rather than now: what the change will cost to live with, and
  whether the shortcuts it took were recorded in `docs/DEBT.md` or left silent.
- **How they are scoped** is defined once, in the `review-scope` skill, which
  every review auditor preloads through the `skills` frontmatter field: the field
  injects a skill's full content into a subagent at startup, which is the include
  mechanism agent bodies lack. Each brief keeps only a byte-checked pointer, so a
  preload that silently did not happen still leaves the auditor able to read the
  rules. `selfcheck.py` fails if the skill goes missing, if an auditor stops
  preloading it, or if a pointer drifts.
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

Refusals **escalate**. A single generic reminder is trivially acknowledged and
stepped past, so each successive refusal names something more concrete: first the
workflow, then the specific evidence that is missing (which vertical failed, why
the existing report doesn't count), then a direct instruction to execute rather
than restate the plan. Escalation is keyed on the session's refusal total, not on
the change signature: Claude normally edits between two Stops, which re-keys the
signature, so a per-change counter would restart at 1 every turn and never
sharpen.

When a cap is reached the gate spends one final turn on a **disclosure**: it
instructs Claude either to finish the audit or to tell the user plainly that the
change is going out unaudited, which verticals are unverified, and what to check.
Only the turn after that does it release. Releasing silently would skip the one
message that matters most.

Unfinished markers found in the change's **own diff** lead the message at every
attempt. A `TODO`, a stub, or deferral prose in a comment ("for now", "in a real  <!-- praxis:ack -->
implementation", "you can extend this") is the signature of an MVP-shaped
delivery, so the gate names each one with its file:line and requires it to be
either implemented or removed and reported as out of scope. `scan_placeholders.py`
supplies that signal; a line carrying `praxis:ack` is exempt.

House-style violations lead the message alongside them, on the same reasoning:
an em dash or an AI credit that reached the diff is a rule the doctrine stated
and the writing ignored, and naming the file:line is what turns it into a fix.
The gate also names any UI vertical the change owes but the report does not
carry, with the changed files that made it a UI change, so the requirement never
looks arbitrary.

Loop safety, in layers:

- Two caps bound the escalation: `MAX_NUDGES` (3) per change signature and
  `SESSION_NUDGE_CAP` (12) per session, so a change set that keeps mutating
  cannot loop indefinitely.
- Each session owns its own entry in `gate_notified.json`. A single shared record
  would let two Claude windows on one repo wipe each other's counters every turn,
  and the caps would then never be reached.
- If the counter **cannot be persisted** (unwritable `.claude/`, full disk), the
  gate fails open. The caps depend on that write; blocking while unable to record
  the block would trap the session forever.
- A tree that is byte-for-byte as the session found it is never gated. A repo can
  be dirty from work that predates the session, and demanding an audit of someone
  else's diff, while attributing their unfinished markers to "this change", is
  worse than not gating at all.
- The `skip-gate` file and `PRAXIS_GATE=off` escapes always apply.

## Per-prompt routing

`prompt_router.py` runs on every `UserPromptSubmit`. It closes praxis's oldest
gap: the pipeline used to be announced once at `SessionStart`, after which skill
selection depended on the model spontaneously matching a skill description, which
works for `/praxis:task` but degrades for a bare "add rate limiting" many turns
into a session, when the SessionStart block is far behind in the context.

The router classifies the prompt's *shape* (not its keywords-as-commands) and
injects a short directive naming the exact skills that request requires:

| Route | Trigger | Injected directive |
| --- | --- | --- |
| `implement` | a change verb (add/fix/refactor/migrate/…) | `task-orchestrator` pipeline, production-complete standard, open a task if multi-step |
| `review` | review/audit/verify wording | `quality-rubric` with the auditors dispatched as subagents |
| `scan` | repo-wide wording | `repo-audit` with adversarial verification and honest coverage |
| `deliver` | commit/push/PR/ship | `git-delivery` |
| `none` | an information question, a slash command, an acknowledgement | nothing: silence beats noise |

Two modifiers stack on any route: UI wording **or a UI file path in the prompt**
adds the `frontend-pipeline` skill (and its `reference/craft.md`) plus the two UI
verticals; documentation wording adds `docs-living`. Auto-pilot appends its
decide-don't-ask directive. Every routed prompt also carries the house-style line,
because the two rules it names apply to the reply as much as to the files.

The UI vocabulary is deliberately broad and the path match deliberately literal:
a false positive costs one skill read, while a false negative costs a page built
with no brief, no story, and no design system. "Update `Header.tsx`" routes to the
front-end pipeline on the file extension alone.

The `deliver` route resolves the **live** merge policy rather than describing it,
so the directive says what this repo will actually do instead of restating a
default the repo may have overridden.

An opening interrogative ("what…", "how…", "why…") wins over any verb in the
sentence, so "how do I add caching?" is answered rather than implemented. The
hook never blocks and never rewrites the prompt.

## Universal onboarding, and why it stopped being a suggestion

`common.repo_state()` classifies the repo, and `session_audit.py` injects the
verdict into context on every `SessionStart`:

| State | Meaning | Route |
| --- | --- | --- |
| `new` | empty/near-empty | full bootstrap |
| `uninitialised` | real code, no Claude setup | analyse then bootstrap |
| `legacy` | a brief without the praxis marker | reconcile + migrate via verifier |
| `partial` | some `.claude/` config | doctor reconcile |
| `managed` | praxis marker present | gates active, patch drift only |

Through 2.x each of the first four printed a *recommendation* to run
`/praxis:bootstrap`, and that recommendation was routinely stepped past: the
session then worked with no operating brief, no guardrails and no living
knowledge, which is the state praxis exists to prevent. From 3.0 the same verdict
produces an **instruction** to run the skill first and continue in the same turn,
repeated by the prompt router on every actionable prompt (the SessionStart block
has effectively expired by the tenth turn). It stays silent on conversational
prompts: answering a question does not require writing a brief first.

The classifier is mode-aware, so a bootstrapped contributor clone reads as
`managed` from its `CLAUDE.local.md` while the project's own `CLAUDE.md`, if it
has one, is untouched and uncounted. `bootstrap.auto` turns the whole thing off
per repo. See ADR-0018.

Alongside the verdict it injects the repo's **live configuration**: the workspace
mode with the source that decided it, the gate, the test-evidence and UI-vertical
requirements, auto-pilot, auto-bootstrap, auto-merge with the PR base branch, the
house-style switches, and the detected test command. Each is resolved at that
moment from environment, toggle file, and `.praxis.toml`, so a session never has
to infer a policy from a document that may have gone stale, and any drift found in
the repo's own docs is listed right below it.

## Settings, resolved in one place

`config.py` reads and toggles the four switches a user actually flips
(auto-pilot, auto-merge, auto-bootstrap, the Stop gate) and prints every resolved
value **with the source it came from**: environment variable, then repo toggle
file, then `.praxis.toml`, then the default. Naming the source matters more than
the value: a user who clears a toggle that an environment variable still forces
would otherwise believe the policy changed, and every later turn would act on the
old one. Asking for a state that a higher-precedence source overrides prints a
warning and exits non-zero rather than reporting success.

Two switches are inverted (`skip-gate` and `no-bootstrap` record the OFF state by
existing) and that inversion is encoded once in the switch table rather than
special-cased at each call site.

`mode` is the one setting that is not a switch, because it has three states:
`owner`, `contributor`, and `auto`, which hands the decision to detection. It
therefore records a value rather than an existence, and setting it also adds or
removes the exclude block, so the files on disk always match the verdict.

`.praxis.toml` is read in two layers: the committed file the team shares, then
`.claude/.praxis/praxis.toml`, which is git-excluded and overrides it. That is
what lets a contributor hold local preferences without editing a config file the
upstream project owns. A malformed shared file falls back to the defaults without
discarding the local layer.

## Language-agnostic by construction

praxis ships **workflow and rubric**, not language rules. Skills and agents are
written as *reasoning* ("derive the build system from what's present", "check
against the authoritative docs for the version in use"), so the same
`regression-sentinel` reasons about Rust, Elixir, or COBOL: the model supplies
the language specifics at runtime. The only place concrete tools appear is
`post_edit.py`'s formatter table, and that degrades silently when a tool is
absent.

## File map

```
.claude-plugin/marketplace.json      one-plugin marketplace catalog
plugins/praxis/
  .claude-plugin/plugin.json         plugin manifest
  output-styles/praxis-quality.md     always-on doctrine
  commands/*.md                      eight entry points (task, audit, docs, ship,
                                     bootstrap, doctor, config, discover)
  skills/*/SKILL.md                  twelve reasoning workflows: task-orchestrator,
                                     prompt-architect, best-practices, code-craft,
                                     quality-rubric, docs-living, claudemd-living,
                                     frontend-pipeline, repo-audit, git-delivery,
                                     bootstrap, capability-discovery
  agents/*.md                        thirteen read-only subagents (10 verticals
                                     + finding-verifier + repo-cartographer +
                                     claudemd-verifier)
  hooks/hooks.json                   lifecycle wiring (command hooks)
  scripts/
    session_audit.py                 SessionStart: workspace mode, state, the
                                     bootstrap instruction, live config, drift
    prompt_router.py                 UserPromptSubmit: per-prompt skill routing
    guard_paths.py                   PreToolUse: secrets, destructive commands,
                                     AI attribution in the project's record,
                                     staging a praxis local artifact
    post_edit.py                     PostToolUse: format + secret tripwire
    quality_gate.py                  Stop: task loop and per-change gate
    scan_placeholders.py             unfinished work in the whole change
    scan_style.py                    em dashes and AI credits in the whole change
    drift.py                         docs versus live config, and stale references
    scope.py                         what is under review: base, commits, files
    report.py  config.py  doctor.py  selfcheck.py  repo_scan.py
    task_state.py  changelog.py  adr.py  debt.py  workspaces.py
    claudemd_check.py
    lib/common.py                    shared, defensive helpers
  templates/*                        CLAUDE.md, settings, MCP starting points
```

## Swapping in native LLM hooks (optional)

praxis drives its LLM review through skills + subagents and enforces it with a
deterministic `command` Stop hook: a design that only uses documented,
universally-available hook mechanics. If your Claude Code version exposes `prompt`
or `agent` hook handler types, you can wire an LLM verdict *directly* into the
Stop event instead of via the marker file. That is a drop-in change to
`hooks/hooks.json`; the rest of the harness is unaffected.
