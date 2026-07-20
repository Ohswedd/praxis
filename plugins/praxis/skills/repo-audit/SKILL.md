---
name: repo-audit
description: "Audit, reverse-audit, and fix an ENTIRE existing codebase — not a diff. Use when the user asks to scan, audit, review, health-check, or harden a whole repo or directory (\"audit this project\", \"find everything wrong\", \"scan the codebase\"), or runs /praxis:scan. Shards the repo into a deterministic coverage ledger, runs every vertical auditor over every shard, adversarially verifies each finding via the finding-verifier (reverse audit), fixes confirmed findings in audited change-sets, and delivers a starting report and a final coverage-honest report. Scales to large codebases and resumes across sessions."
---

# Repo Audit — the whole-codebase scanner

`/praxis:audit` reviews *a change*. This skill reviews *the repository* — an
already-developed project with no fresh diff to anchor on. It applies the same
praxis doctrine (vertical auditors, adversarial verification, completeness,
no silent scope cuts) to the entire codebase, and it is built around one rule:

**Coverage is claimed by the ledger, never by memory.** Every file is assigned
to a shard; every shard × dimension pass is recorded; every finding has a
tracked lifecycle. If the ledger says a shard wasn't audited, the final report
says so. Laziness is structurally impossible, not just discouraged.

The scan is a pipeline: **inventory → starting report → forward audit →
reverse audit → fix → final report.** Run the phases in order.

---

## Phase 0 — Preflight & inventory

1. **Open a praxis task** so the Stop gate self-drives the scan to completion
   (size `--max` by shard count; a scan is a large task — 40+ turns):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" open "Repo scan: <repo>" \
     --criteria "every shard audited on every dimension" \
     "every finding verified" "confirmed findings fixed or explicitly deferred" \
     "final report delivered" --max 50
   ```
2. **Check for an existing ledger** — `repo_scan.py status`. If a scan is
   already underway, **resume it** (skip to whichever phase has pending work)
   instead of re-initialising.
3. **Initialise the ledger** (inventory + shard plan):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/repo_scan.py" init [--scope <path>]
   ```
   (Every `repo_scan.py …` below is shorthand for
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/repo_scan.py" …`.)
   It inventories tracked files (pruned of vendored/binary/lock/oversize noise,
   each exclusion counted), groups them by subsystem, and splits them into
   shards capped by file/line count. `--shard-files/--shard-lines` tune shard
   size for very large repos.
4. **Baseline.** Note whether the working tree is clean (recommend committing
   first so fixes stay separable). Detect the test command (session audit or
   `common.detect_test_command`), **run it once now**, and record the result in
   the ledger so the final report can show before/after:
   ```bash
   repo_scan.py baseline --tests "<command>" --exit <observed exit code>
   ```
   Pre-existing failures are findings in their own right — record them
   (`regression` dimension) rather than blaming them on later fixes.
5. **Very large repos.** `init` refuses to build a silently-truncated inventory:
   above `--max-files` (default 20000) it stops and asks you to narrow `--scope`
   or raise the cap. Never work around this by scanning "the important parts"
   unstated — split into several scoped scans and say so in the report.

## Phase 1 — Starting report (before any auditing)

Present the scan plan so the user knows exactly what will and won't happen:

```
## Repo scan — plan
- Scope: <path> — N files / M lines in K shards (top groups: …)
- Excluded from inventory: vendored=…, binary=…, lockfile=…, oversize=… (counted, not hidden)
- Dimensions per shard: adversarial, edge-case, regression, duplication,
  performance, doc-reference, completeness
- Reverse audit: every finding is independently re-examined by @praxis:finding-verifier
- Fix policy: confirmed findings fixed in audited change-sets; architectural /
  breaking / irreversible items are deferred with a remediation plan, never auto-applied
- Mode: full (audit + verify + fix) | report-only (--report-only)
- Test baseline: <command> → <pass/fail summary>
- Estimated agent dispatches: K shards × 7 dimensions + 1 per finding
```

For a very large repo (thousands of files), this is a genuine decision point on
cost/scope — offer to narrow `--scope` or raise shard caps. In auto-pilot,
proceed with the full scope and record the decision.

## Phase 2 — Forward audit (vertical, per shard)

For each shard, dispatch **every** dimension to its auditor. The mapping:

| Dimension       | Agent                             | Hunts |
| --------------- | --------------------------------- | ----- |
| `adversarial`   | `@praxis:adversarial-auditor`     | security, injection, authz gaps, unsafe states, resource abuse |
| `edge-case`     | `@praxis:edge-case-hunter`        | real bugs: boundaries, null/empty, concurrency, error paths |
| `regression`    | `@praxis:regression-sentinel`     | contracts vs tests, promised-but-missing behaviour, wrong assertions |
| `duplication`   | `@praxis:duplication-scanner`     | copy-paste, reinvention, over-engineering (maintainability) |
| `performance`   | `@praxis:perf-scalability-analyst`| complexity, hot paths, N+1, growth ceilings |
| `doc-reference` | `@praxis:doc-reference-finder`    | misused APIs, deprecated usage, pattern drift, bad practice |
| `completeness`  | `@praxis:completeness-auditor`    | stubs, TODO debt, dead code, debug leftovers, unwired code |

Dispatch mechanics:
- Get the shard's file list with `repo_scan.py shard <id>` and paste it into
  the agent prompt: *"Your scope is these files (a repo shard, no diff): …
  Report each defect as severity + file:line + one-line claim + evidence."*
- **Batch in parallel** — several shard × dimension agents per message. If the
  session has a workflow-orchestration surface, use it to pipeline shards
  through dimensions; otherwise plain parallel agent batches are fine.
- After each agent returns: record every defect via
  `repo_scan.py finding add --shard <id> --dimension <dim> --severity <sev>
  --file <path> --title "…" --detail "…"`, then record the pass itself:
  `repo_scan.py mark <id> <dim>`. **A clean pass is still marked** — zero
  findings is a result, not a skipped shard.

Anti-laziness rules (non-negotiable):
- Never skip a dimension because a shard "looks simple" or is config/tests —
  config and tests are exactly where stale contracts hide.
- Never sample files within a shard; the agent gets the full list.
- If an agent's report is vague ("looks fine overall"), re-dispatch with a
  sharper prompt; do not mark the dimension until you have a per-file answer.
- Secrets: if an auditor finds a live credential, record the finding by file
  path only — **never** paste the secret value into the ledger or chat; the fix
  is rotation + removal, flagged critical.
- Check progress with `repo_scan.py status` between batches; Phase 2 ends only
  when it reports every shard fully audited.
- The ledger is a single JSON file with one writer: dispatch *agents* in
  parallel, but record their results (`finding add` / `mark`) in **sequential**
  CLI calls — never fire concurrent ledger writes.

## Phase 3 — Reverse audit (verify before you trust)

The forward pass rewards finding things; this pass kills the false positives.

1. **Dedup.** `repo_scan.py finding list` — merge cross-shard duplicates of the
   same root cause (refute the copies with a note pointing at the survivor).
2. **Verify every open finding.** Dispatch `@praxis:finding-verifier` in
   parallel batches (group ~5 related findings per agent). It re-reads the
   cited code and returns CONFIRMED / DOWNGRADED / REFUTED with evidence.
   Record each verdict:
   ```bash
   repo_scan.py finding verify F012 --verdict confirmed
   repo_scan.py finding verify F013 --verdict downgraded --severity low --note "…"
   repo_scan.py finding verify F014 --verdict refuted --note "guarded in caller, x.py:88"
   ```
3. **Contract sweep (outside-in).** The forward pass went code → defects; now
   go promises → code: dispatch `@praxis:regression-sentinel` (README/docs/
   public API/tests as the scope) to find behaviour the project *promises* but
   does not deliver. New findings enter the ledger and are verified like any
   other.

No finding reaches Phase 4 without a `confirmed` status.

## Phase 4 — Fix (skipped in report-only mode)

Work through confirmed findings **by severity, grouped into coherent
change-sets** (same subsystem/root cause together — not one mega-commit, not
one commit per line):

1. For each change-set: implement to code-craft standard, add/update tests that
   pin the fix, and run the test suite — the baseline from Phase 0 tells you
   which failures are yours.
2. Run the **quality-rubric** on the change-set like any praxis change (the
   Stop gate will demand it anyway). A fix that fails its own audit is not a fix.
3. Record each resolved finding: `repo_scan.py finding fix F012 --note "<what/where>"`.
4. **Defer, don't improvise, on the big stuff.** Architectural restructuring,
   breaking public-API changes, dependency major-version jumps, schema
   migrations, and anything irreversible or credential-dependent are **never
   auto-applied** — even in auto-pilot (they are scope changes, not design
   choices). Record them:
   `repo_scan.py finding defer F009 --reason "<remediation plan>"`.
5. Commit change-sets as you go if the user asked for delivery (git-delivery
   skill); otherwise leave a clean working tree story the user can review.

## Phase 5 — Final report & living knowledge

1. **Close the loop in the ledger** — `repo_scan.py report` computes coverage
   and the findings table from recorded state. If it prints an INCOMPLETE
   warning, go back to Phase 2; do not hand-edit the story.
2. **Living knowledge** (docs-living skill): write the scan outcome to
   `docs/audits/<YYYY-MM-DD>-repo-scan.md` in the target repo (the same
   artifact praxis keeps for itself in `docs/AUDIT.md`); add a `CHANGELOG.md`
   `[Unreleased]` entry per fix change-set (`fixed`/`security` types); record
   an ADR for any significant decision the scan forced.
3. **Deliver the final report** to the user:

```
## Repo scan — final report
### Coverage
<repo_scan.py report output: shards, files, lines, exclusions — honest gaps included>
### Findings
| Dimension | Critical | High | Medium | Low | Refuted |
### Fixed
- F0NN [sev/dim] file — what was done, test that pins it
### Deferred (needs your decision)
- F0NN [sev/dim] file — why it wasn't auto-fixed + remediation plan
### Refuted (false positives killed by the reverse audit)
- count per dimension, with notable examples
### Tests
- baseline: <result> → after fixes: <result>
### Docs & knowledge
- docs/audits/<date>-repo-scan.md, CHANGELOG entries, ADRs
```

4. Mark the praxis task `done` only when every criterion holds: full coverage,
   all findings verified, every confirmed finding fixed or deferred-with-plan,
   report delivered.

## Resuming a scan

The ledger survives sessions (`.claude/.praxis/repo_scan.json`). On any new
session: `repo_scan.py status` → continue the first phase with pending work
(unaudited shards → Phase 2; open findings → Phase 3; confirmed findings →
Phase 4). Never re-init over an in-progress scan; `init` refuses without
`--force`, and `clear` refuses to discard recorded work without `--force`.

## Notes

- Language/framework-agnostic: auditors derive idioms from the repo itself.
- Report-only mode (`--report-only` or the user says "just report, don't fix")
  runs Phases 0–3 and 5 and lists confirmed findings as recommendations.
- The scan reads everything but the fix phase touches only what a confirmed
  finding requires — a scan is not a licence to refactor at will.
