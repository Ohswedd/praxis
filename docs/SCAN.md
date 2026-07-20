# The Repo-Wide Scanner (`/praxis:scan`)

`/praxis:audit` reviews a *change*; `/praxis:scan` reviews a *repository* — an
already-developed, "solid" project with no fresh diff. It finds security
issues, real bugs, broken contracts, duplication, performance hazards, bad
practice, and debt across the whole codebase; adversarially verifies every
finding; fixes what is confirmed; and reports with coverage honesty.

## The pipeline

```
Phase 0  Inventory      repo_scan.py init → every auditable file assigned to a
                        shard (grouped by subsystem, capped by files/lines);
                        exclusions counted; test baseline recorded
Phase 1  Starting report scope, shard plan, dimensions, fix policy, baseline,
                        estimated dispatches — before any auditing
Phase 2  Forward audit  every shard × every vertical dimension, dispatched to
                        the praxis auditor subagents; findings + passes recorded
Phase 3  Reverse audit  dedup → @praxis:finding-verifier tries to REFUTE each
                        finding (confirmed / downgraded / refuted, with
                        evidence) → outside-in contract sweep (promises → code)
Phase 4  Fix            confirmed findings only, grouped into change-sets, each
                        with tests + the normal quality rubric; architectural /
                        breaking / irreversible items deferred with a plan
Phase 5  Final report   computed from the ledger; docs/audits/<date> artifact,
                        CHANGELOG entries, ADRs
```

The protocol lives in the `repo-audit` skill; the command is a thin dispatcher.

## Why a ledger

On a large codebase the failure mode of an LLM audit is *silent sampling*: it
reads the interesting 20 files and reports the repo as reviewed. The scanner
makes that impossible mechanically, not aspirationally:

- **Inventory is deterministic.** `repo_scan.py init` enumerates tracked files
  (pruned of vendored/binary/lockfile/oversize noise — every exclusion counted
  and reported, never hidden).
- **Coverage is recorded, not remembered.** A shard counts as audited only when
  all seven dimensions were marked (`repo_scan.py mark <shard> <dim>`), and a
  clean pass is still a recorded pass.
- **The report is computed.** `repo_scan.py report` derives coverage and the
  findings table from state; if any shard × dimension never ran, the report
  prints an INCOMPLETE warning that cannot be prose-papered over.
- **Findings have a lifecycle.** `open → confirmed | refuted → fixed | deferred`
  (a `downgraded` verdict records as `confirmed` at the lower severity) —
  nothing is fixed unverified, and nothing confirmed can quietly disappear.
- **No silent inventory caps.** `init` fetches one file beyond `--max-files`
  (default 20000) and refuses to proceed if the scope exceeds it — you narrow
  `--scope` or raise the cap explicitly; the tail is never dropped quietly. In
  git repos a `--scope` is applied as a git pathspec, so scoping a huge repo
  stays exact; the non-git fallback walk likewise *refuses* (rather than
  truncates) when a pathological tree exhausts its directory budget.
- **The ledger cannot lie about persistence.** Unlike praxis's fail-open hook
  scripts, `repo_scan.py` propagates I/O errors (atomic temp-file writes, loud
  failure on a corrupt ledger) — `mark`/`finding` never report success without
  the state actually on disk, and `init`/`clear` refuse to destroy recorded
  work without `--force`.

## The dimensions

Each shard is audited on all seven praxis verticals, by the same read-only
Opus subagents the change-audit uses (their scope generalises from "the diff"
to "these files"): `adversarial` (security), `edge-case` (correctness bugs),
`regression` (contracts vs tests), `duplication` (maintainability/reinvention),
`performance`, `doc-reference` (API misuse, pattern drift), `completeness`
(stubs, dead code, debt).

## The reverse audit

Forward auditors are rewarded for *finding* things, so a scan without a
counterweight over-reports. Every finding is handed to
`@praxis:finding-verifier` — a skeptic that re-reads the cited code trying to
**refute** the claim — and only `confirmed` findings reach the fix phase.
Severity gets re-graded against realistic impact (`downgraded`), and false
positives die with cited evidence (`refuted`). The sweep then inverts
direction: from the project's promises (README, docs, public API, tests) back
into the code, catching behaviour that is promised but not delivered — the
half of an audit a code-first pass structurally misses.

## Fix policy

- Confirmed findings are fixed in coherent change-sets (same subsystem/root
  cause), each with tests and its own green quality rubric.
- **Never auto-applied**, even in auto-pilot: architectural restructuring,
  breaking public-API changes, dependency major upgrades, schema migrations,
  anything irreversible or credential-dependent. These are deferred with a
  remediation plan in the final report — a scope decision belongs to you.
- Live secrets found in the repo are flagged critical by path only (the value
  is never echoed); the remedy is rotation + removal.
- `--report-only` skips fixing entirely and delivers recommendations.

## Scale & resumability

- Shard caps (`--shard-files`, `--shard-lines`) keep each dispatch within what
  an auditor can genuinely read; `--scope <path>` narrows a scan to a subtree.
- State lives in `.claude/.praxis/repo_scan.json` (git-ignored), so a scan on a
  large codebase spans sessions: `repo_scan.py status` says exactly which
  shards, dimensions, and findings are pending, and the skill resumes there.
  `init` refuses to clobber an in-progress scan without `--force`.
- Auditor context stays lean: agents receive file lists, read what they need in
  their own context window, and return findings — the main conversation only
  carries the ledger.

## CLI reference

```
repo_scan.py init [--scope PATH] [--shard-files N] [--shard-lines N] \
             [--max-files N] [--force]
repo_scan.py baseline --tests "CMD" --exit N   # record the pre-scan test result
repo_scan.py status [--json]              # coverage + findings summary
repo_scan.py shard <id> [--json]          # file list + remaining dimensions
repo_scan.py mark <shard-id> <dimension>  # record a completed audit pass
repo_scan.py finding add --shard <id> --dimension <dim> --severity <sev> \
             --file <path> --title "…" [--detail "…"]
repo_scan.py finding verify <fid> --verdict confirmed|refuted|downgraded \
             [--severity <sev>] [--note "…"]
repo_scan.py finding fix <fid> [--note "…"]
repo_scan.py finding defer <fid> --reason "…"
repo_scan.py finding list [--status S] [--json]
repo_scan.py report [--json]              # coverage-honest final report
repo_scan.py clear [--force]
```

Severities: `critical`, `high`, `medium`, `low`. Free text recorded into the
ledger (`--title`/`--detail`/`--note`/`--reason`) is screened against praxis's
secret signatures and rejected if it looks like a credential — findings about
secrets reference the file path only.
