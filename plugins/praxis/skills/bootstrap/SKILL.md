---
name: bootstrap
description: Prepare any repository for top-tier Claude Code use. Runs automatically as the first step of any session that does real work in a repo praxis has not set up, and on demand via /praxis:bootstrap. Use on a brand-new repo, an existing repo with no Claude Code setup, or an existing repo that already has a CLAUDE.md (legacy or from another tool) that needs reconciling. Detects the project's stack by reasoning (never a fixed language list), generates or migrates a regression-checked brief hierarchy, writes sensible permissions and guardrails, and proposes LSP/MCP wiring. In a repository you only contribute to, every artifact it writes is local and git-excluded. Use whenever the user wants to "set up", "initialise", "onboard", or "prepare" a repo for Claude Code, or when the session audit reports state new/uninitialised/legacy.
---

# Bootstrap

Bring a repository to a top-tier Claude Code setup, whatever state it starts in.
This is language- and framework-agnostic: infer the stack from what is actually
present; do not assume a fixed set of ecosystems.

## Step 0a: Automatic invocation (the normal case)

This skill is not usually asked for. The SessionStart audit and the prompt router
both instruct you to run it whenever `repo_state` is not `managed`, because a repo
with no operating brief, no guardrails and no living knowledge is the state praxis
exists to prevent, and a *recommendation* to fix it was routinely stepped past.

When it fires automatically, it is a step, not a conversation:

- **Write what does not exist**, without asking. Creating a file the repo lacks is
  additive and reversible, and the user asked for the work, not for a setup
  interview.
- **Then carry straight on to the user's actual request, in the same turn.**
  Report the setup in one or two lines under a "Setup" heading in your reply.
  Bootstrap that hijacks the first prompt is worse than bootstrap that never ran.
- **Stop and ask for exactly one thing**: reconciling a `CLAUDE.md` that praxis
  did not author (Step 4). That merge can drop a still-valid instruction, so it
  gets the verifier and the user's eyes. Nothing else here is lossy.
- If the user has turned it off (`/praxis:config bootstrap off`,
  `bootstrap.auto = false`, `PRAXIS_BOOTSTRAP=off`), do not run it and do not
  argue about it.

## Step 0b: Resolve the workspace mode (before writing anything)

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status` names the mode and
where it came from. It decides every path below:

| | `owner` | `contributor` |
| --- | --- | --- |
| Operating brief | `CLAUDE.md` (+ nested) | `CLAUDE.local.md` at the root only |
| Settings | `.claude/settings.json` | `.claude/settings.local.json` |
| praxis config | `.praxis.toml` (committed) | `.claude/.praxis/praxis.toml` (local) |
| `/docs`, `CHANGELOG.md`, `docs/adr/` | created and maintained | updated **only if the repo already has them**; otherwise written under `.claude/.praxis/knowledge/` |
| Ignore rules | add praxis's paths to `.gitignore` | never touch `.gitignore`; praxis maintains `$GIT_COMMON_DIR/info/exclude` itself |
| Capabilities (Step 7) | `.claude/` commands, skills, agents; `.mcp.json` | `.claude/.praxis/capabilities/`; MCP in `.claude/settings.local.json` |

In `contributor` mode the repository is not ours and must end the session
byte-for-byte as it started, apart from the change the user actually asked for.
That means: no `CLAUDE.md`, no `.praxis.toml`, no new `/docs` tree, no new
`CHANGELOG.md`, no `.gitignore` edit, no scaffolded `.claude/` capability, and
nothing praxis authored in any commit. Steps 2, 3, 5, 6 and 7 below all read from
this table rather than assuming ownership.

## Step 1: Classify the starting state
`repo_state` reports it and the session audit prints it:

- **new**: empty or near-empty repo. Full setup from scratch.
- **uninitialised**: real codebase, no brief and no settings. Analyse first,
  then set up.
- **legacy**: a brief exists that praxis did not create (no
  `<!-- praxis:managed -->` marker). Reconcile and migrate; preserve every
  still-valid instruction (Step 4). In `contributor` mode this case cannot
  arise: the brief praxis owns is `CLAUDE.local.md`, which is additive, and the
  project's own `CLAUDE.md` is left exactly as it is.
- **managed**: already praxis-managed. Run `/praxis:doctor` instead; only
  patch drift.

## Step 2: Understand the codebase (read-only)
Dispatch `@praxis:repo-cartographer` (or do it inline) to produce:
- the project's purpose and top-level architecture,
- the real build / test / run / lint commands (derive them from the actual
  build system present, whatever it is),
- directory ownership (which areas are cohesive enough to deserve their own
  nested brief),
- conventions in force (formatting, naming, error handling, commit style),
- external services and integration points.

In `contributor` mode, capture the project's *contribution* conventions too:
`CONTRIBUTING.md`, the PR template, the shape of recent merged commits, and
whether changelog entries are expected. Those are what a contribution has to
match, and they are exactly what praxis must not invent.

## Step 3: Generate the brief
Write a high-signal operating brief (not documentation) into the path Step 0b
gives, using `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.tpl` as the shape. Keep it
lean: every line is context spent every session, and the Claude Code guidance is
to stay under ~200 lines. Include the `<!-- praxis:managed -->` marker so praxis
recognises it later. Cover: purpose, build/test/run commands, conventions,
architecture in a few lines, and "do / don't" rules that matter.

Nested briefs (one per cohesive subsystem, capturing only what differs from the
root) are an `owner`-mode artifact: they are files in the project's tree. In
`contributor` mode keep everything in the single local brief instead.

## Step 4: (legacy, owner mode only) Reconcile the existing CLAUDE.md
Never discard the old file blindly. Instead:
1. Draft the new/merged version.
2. Run the verifier: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/claudemd_check.py <old> <new>`
   and dispatch `@praxis:claudemd-verifier` for semantic judgement.
3. Only keep removals the verifier confirms are safe (obsolete, contradicted by
   the code, or genuinely duplicated). Preserve everything else.
4. Show the user the before/after and the verifier's reasoning before writing.
   This is the one place bootstrap waits for an answer.

## Step 5: Guardrails and settings
Propose the settings file from
`${CLAUDE_PLUGIN_ROOT}/templates/settings.suggested.json`, tuned to the detected
stack (allow the real build/test commands; ask on push; deny destructive ops).
The praxis hooks already provide runtime guardrails; settings are the declarative
complement.

- **owner**: write `.claude/settings.json`, ensure `.gitignore` covers
  `.claude/.praxis/`, `.claude/settings.local.json` **and `CLAUDE.local.md`**
  (the guard refuses to stage all three in either mode, so a repo that ignores
  only two leaves the third as permanent `git status` noise nobody is allowed to
  clear), and optionally add a committed `.praxis.toml` (from
  `templates/praxis.toml.tpl`) to tune gate strictness or default auto-pilot per
  repo.
- **contributor**: write `.claude/settings.local.json` and nothing else. praxis
  keeps its own paths out of git through `$GIT_COMMON_DIR/info/exclude`, which it maintains,
  so there is no ignore rule to add and no config file to commit. Verify with
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"`, which reports whether the
  local state is genuinely excluded rather than assuming it.

**A praxis config file is optional in both modes, and a bootstrap that does not
write one has not failed.** praxis runs from its defaults, so a repository with
no config is configured; the file exists to *version a deviation* from them. In
`contributor` mode the committed `.praxis.toml` is not ours to write at all, and
the local `.claude/.praxis/praxis.toml` is written only when there is a per-clone
choice to record. `config.py status` and `doctor.py` name the layers that exist
and the one praxis would write here, so this never has to be guessed.

## Step 6: Living knowledge (/docs, CHANGELOG, ADRs)
In `owner` mode every repo must have a `/docs` tree and a `CHANGELOG.md`. If
missing, scaffold them (use the `docs-living` skill and the templates):
- `docs/README.md` (index), `docs/ARCHITECTURE.md` seeded from what the
  repo-cartographer found (real components/flow, not assumptions), and an empty
  `docs/adr/`.
- `CHANGELOG.md` at the root from `templates/CHANGELOG.md.tpl` (Keep a Changelog).
For a legacy repo that already has docs, reconcile rather than overwrite: index
existing docs in `docs/README.md` and note gaps.

In `contributor` mode, create none of these. Join what the project already has,
following its conventions, and keep anything else under
`.claude/.praxis/knowledge/`, which mirrors the same layout. `changelog.py` and
`adr.py` already resolve this for you: run them and read the path they print.
This is enforced, not advised: the guard refuses to create or commit a
`CHANGELOG.md`, a `/docs` skeleton, a `CLAUDE.md` or a `.praxis.toml` the project
does not have, whether the write comes from the file tool, the shell, or `git
add`. Editing one the project *does* have stays right and is untouched.

## Step 7: Capabilities (propose, don't force)
- **LSP**: if the language has an LSP the user could enable for automatic
  diagnostics, mention it.
- **MCP**: if you detect integration points (a database URL, an issue tracker,
  an error monitor), propose the matching MCP wiring using
  `${CLAUDE_PLUGIN_ROOT}/templates/mcp.suggested.json` as a starting point, but
  never write live credentials: reference environment variables. Route anything
  concrete through the `capability-discovery` skill so an existing server is
  reused before a new one is added.
- **In `contributor` mode**, this step is subject to the Step 0b table like every
  other: a committed `.mcp.json` and a scaffolded `.claude/` command are files the
  project never asked for. Wire MCP through `.claude/settings.local.json` and
  scaffold under `.claude/.praxis/capabilities/`. If the project genuinely needs
  the capability, propose it in the pull request rather than adding it.

## Step 8: Verify the setup
Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"` and confirm every item
reports OK for the mode in force. Summarise what was created in one or two lines,
then get on with the user's request.

## Guarantees
- Idempotent: safe to run repeatedly, and safe to run automatically.
- Additive: it creates what is absent. The only thing it rewrites is a brief it
  authored itself, and the only thing it merges is routed through the verifier
  with the user's confirmation.
- Contained: in `contributor` mode nothing it writes is visible to `git status`,
  reachable by `git add -A`, or eligible to be staged at all. The PreToolUse guard
  refuses the command even if something asks for it explicitly.
