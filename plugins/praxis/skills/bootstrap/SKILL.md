---
name: bootstrap
description: Prepare any repository for top-tier Claude Code use. Use this on a brand-new repo, an existing repo with no Claude Code setup, or an existing repo that already has a CLAUDE.md (legacy or from another tool) that needs reconciling. Detects the project's stack by reasoning (never a fixed language list), generates or migrates a regression-checked CLAUDE.md hierarchy, writes sensible permissions and guardrails, and proposes LSP/MCP wiring. Use whenever the user wants to "set up", "initialise", "onboard", or "prepare" a repo for Claude Code, or when the session audit reports state new/uninitialised/legacy.
---

# Bootstrap

Bring a repository to a top-tier Claude Code setup, whatever state it starts in.
Everything is **proposed and shown as a diff before writing** — never a silent
overwrite. This is language- and framework-agnostic: infer the stack from what
is actually present; do not assume a fixed set of ecosystems.

## Step 0 — Classify the starting state
Determine which case you are in (the session audit may already have told you):

- **new** — empty or near-empty repo. Full setup from scratch.
- **uninitialised** — real codebase, no `CLAUDE.md` / `.claude/`. Analyse first,
  then set up.
- **legacy** — a `CLAUDE.md` exists that praxis did not create (no
  `<!-- praxis:managed -->` marker). Reconcile and migrate; preserve every
  still-valid instruction (see Step 4).
- **managed** — already praxis-managed. Run `/praxis:doctor` instead; only
  patch drift.

## Step 1 — Understand the codebase (read-only)
Dispatch `@praxis:repo-cartographer` (or do it inline) to produce:
- the project's purpose and top-level architecture,
- the real build / test / run / lint commands (derive them from the actual
  build system present, whatever it is),
- directory ownership (which areas are cohesive enough to deserve their own
  nested `CLAUDE.md`),
- conventions in force (formatting, naming, error handling, commit style),
- external services and integration points.

## Step 2 — Generate the root CLAUDE.md
Write a high-signal operating brief (not documentation) using
`${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.tpl` as the shape. Keep it lean —
every line is context spent every session. Include the `<!-- praxis:managed -->`
marker so praxis recognises it later. Cover: purpose, build/test/run commands,
conventions, architecture in a few lines, and "do / don't" rules that matter.

## Step 3 — Generate nested CLAUDE.md files
For each cohesive subsystem the cartographer identified (e.g. a service, a
package, a domain module), create a short nested `CLAUDE.md` capturing only what
differs from the root. These load automatically when Claude works there. Do not
duplicate the root file.

## Step 4 — (legacy only) Reconcile the existing CLAUDE.md
Never discard the old file blindly. Instead:
1. Draft the new/merged version.
2. Run the verifier: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/claudemd_check.py <old> <new>`
   and dispatch `@praxis:claudemd-verifier` for semantic judgement.
3. Only keep removals the verifier confirms are safe (obsolete, contradicted by
   the code, or genuinely duplicated). Preserve everything else.
4. Show the user the before/after and the verifier's reasoning before writing.

## Step 5 — Guardrails and settings
Propose `.claude/settings.json` from
`${CLAUDE_PLUGIN_ROOT}/templates/settings.suggested.json`, tuned to the detected
stack (allow the real build/test commands; ask on push; deny destructive ops).
Ensure `.gitignore` covers `.claude/.praxis/` and `.claude/settings.local.json`.
The praxis hooks already provide runtime guardrails; settings are the
declarative complement. Optionally add a committed `.praxis.toml` (from
`templates/praxis.toml.tpl`) to tune gate strictness or default auto-pilot per repo.

## Step 6 — Living knowledge (/docs, CHANGELOG, ADRs)
Every repo must have a `/docs` tree and a `CHANGELOG.md`. If missing, scaffold
them (use the `docs-living` skill and the templates):
- `docs/README.md` (index), `docs/ARCHITECTURE.md` seeded from what the
  repo-cartographer found (real components/flow, not assumptions), and an empty
  `docs/adr/`.
- `CHANGELOG.md` at the root from `templates/CHANGELOG.md.tpl` (Keep a Changelog).
For a legacy repo that already has docs, reconcile rather than overwrite — index
existing docs in `docs/README.md` and note gaps. From now on, every change keeps
these current.

## Step 7 — Capabilities (propose, don't force)
- **LSP**: if the language has an LSP the user could enable for automatic
  diagnostics, mention it.
- **MCP**: if you detect integration points (a database URL, an issue tracker,
  an error monitor), propose the matching MCP wiring using
  `${CLAUDE_PLUGIN_ROOT}/templates/mcp.suggested.json` as a starting point, but
  never write live credentials — reference environment variables. Route anything
  concrete through the `capability-discovery` skill so an existing server is
  reused before a new one is added.

## Step 8 — Verify the setup
Run `/praxis:doctor` and confirm all items report OK. Summarise what was
created/changed for the user.

## Guarantees
- Idempotent: safe to run repeatedly.
- Non-destructive: proposes diffs; asks before writing; never deletes valid
  instructions or user files without explicit confirmation.
