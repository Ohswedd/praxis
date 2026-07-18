# Changelog

All notable changes to praxis are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Git/GitHub delivery — new `/praxis:ship` command and `git-delivery` skill: write a Conventional Commit, branch, push, and open a PR. Human-in-the-loop merge by default; opt-in `git.auto_merge` (config, `PRAXIS_AUTO_MERGE`, or `git_delivery.py on`) reviews and merges autonomously — never without a green audit or by force-pushing the base branch. Adds `git.auto_merge`/`git.default_branch` config keys and git-delivery status in `/praxis:doctor`.

### Changed
- Compacted and unified every command body; sharpened the `code-craft` comment standard to forbid step-narration and doc-pointer scaffolding.
- Delivery no longer adds AI authorship attribution to commits or PR bodies; the git-delivery skill and CONTRIBUTING.md codify the rule.
- Strengthened simplicity/reuse enforcement: code-craft gains a build-only-what-is-needed section, the duplication auditor now also flags over-engineering (YAGNI), and the orchestrator reinforces it.

### Fixed
- `changelog.py add` now inserts a new `[Unreleased]` section below the document title and keeps subsections in Keep-a-Changelog order. Removed a dead no-op (`emit_context("")`) in `post_edit.py` and step-narration comments in `changelog.py`.

### Security
- Hardened the PreToolUse guard against branch-history rewrites: it now blocks `gh pr merge --admin` (a branch-protection bypass) and every force-push form — flag, bundled `-f`, or `+refspec`, in any argument order, and behind interposed git global options — so autonomous auto-merge can never override branch protection or rewrite a branch. praxis never force-pushes; a human runs it.

## [1.1.2] - 2026-07-18
### Fixed
- Three component manifests had an unquoted `: ` (colon-space) inside their YAML
  `description:`, which made the loader drop the **entire** frontmatter — so
  `best-practices` (skill), `completeness-auditor`, and `repo-cartographer`
  (agents) loaded with empty metadata (name, the `tools: Read, Grep, Glob`
  read-only restriction, and model/effort all silently lost). Quoted the three
  descriptions; `claude plugin validate` now passes clean.
- Hardened `selfcheck.py`: frontmatter whose unquoted scalars contain `: ` is now
  rejected (YAML would silently fail to parse it), so `make check`/CI catch this
  class **before** publish instead of only `claude plugin validate` catching it
  after. Check/test counts unchanged (61 checks, 32 tests).

## [1.1.1] - 2026-07-16
### Changed
- Full delivery audit: verified every script runs cleanly, the end-to-end gate
  lifecycle (dirty → task → done → evidence report → re-arm → config-disable),
  doc-link/reference integrity, CI YAML, and absence of stray placeholders/secrets.
- Optimisation: `detect_workspaces` now uses a single pruned filesystem walk
  (`find_files_multi`) instead of four — faster SessionStart on large repos.
  No behaviour change. Test suite: 32 cases; selfcheck: 61 checks.

## [1.1.0] - 2026-07-16
### Added
- **Per-repo config** `.praxis.toml` (`gate.enabled`, `gate.require_tests`,
  `autopilot.default`, `audit.depth`) — stdlib parser, wired into the gate,
  auto-pilot, and doctor; template + bootstrap proposal; ADR-0004.
- Dev DX / OSS hygiene: `Makefile`, `CODEOWNERS`, PR and issue templates,
  `.editorconfig`.
- selfcheck now validates `@praxis:` agent references and marketplace source paths.

### Changed
- **Performance:** replaced whole-tree `rglob` with a pruning `os.walk`
  (`common.find_files`) that skips `node_modules`/`.git`/build dirs — fast
  SessionStart on large/enterprise repos. Test suite grew to 31 cases; selfcheck
  to 61 checks.

### Security
- Secret-read guard now covers `grep`/`awk`/`sed`/`rg`/`ag`/`source`/`.` and
  detects the sensitive path in any argument position (not just the first).
- Destructive-command guard now also blocks long-form `rm --recursive --force`
  on root/home (fixed a word-boundary regex bug).

## [1.0.0] - 2026-07-16
First stable release. Public surface is now stable under SemVer (see
`docs/STABILITY.md`).

### Added
- **Evidence-backed quality report** (`report.py`): records test command + exit
  code and per-vertical verdicts. The Stop gate now requires a passing test run
  (when the repo has a test command) before accepting a green report — no longer
  trust-based. (ADR-0003.)
- **Monorepo / workspace awareness** (`common.detect_workspaces`, `workspaces.py`):
  session_audit reports packages; the orchestrator and regression-sentinel run the
  changed package's tests, not just the root.
- `docs/STABILITY.md` (stable surface), `docs/ROADMAP.md`, uninstall/cleanup notes,
  `.editorconfig`, and ADR-0003.

### Fixed
- **Change signature excludes Praxis's own `.claude/.praxis/` state**, so recording
  a report can't perturb it in repos that haven't git-ignored the state dir yet
  (found by the new evidence tests).

### Changed
- quality-rubric records the report via `report.py`; test suite expanded to 20
  cases (evidence gate + workspace detection); selfcheck now covers 51 checks.

## [0.7.0] - 2026-07-16
### Added
- **Test suite** (`tests/`, 16 stdlib unittest cases) covering the deterministic
  core; runs in CI.
- **`selfcheck.py`** — plugin self-integrity validation (manifests, version
  agreement, hook→script references, frontmatter, compilation); in CI and doctor.
- **`SECURITY.md`** (threat model & posture) and **`CONTRIBUTING.md`**.
- **`/praxis:release`** command — SemVer from Conventional Commits + changelog
  finalize.
- **`docs/AUDIT.md`** (self-audit) and **ADR-0002** (self-testing decision);
  Requirements & compatibility section in the README.

### Fixed
- PostToolUse now formats a file only with a formatter the project actually adopts
  (config/adoption signal), instead of any formatter on `PATH` — prevents fighting
  the project's real conventions.
- Placeholder scanner no longer flags prose comments as commented-out code
  (tighter pattern, fewer false positives).

### Security
- Destructive-command guard now also blocks env/secret exfiltration to the network,
  writes to SSH `authorized_keys` and `/etc`, and plaintext credential persistence.

## [0.6.0] - 2026-07-16
### Changed
- **Renamed the project to Praxis** (was cc-forge): plugin/marketplace name,
  command namespace `/praxis:*`, env vars `PRAXIS_*`, state dir `.claude/.praxis/`,
  managed marker `<!-- praxis:managed -->`, output style `praxis-quality`.

### Added
- **Living knowledge** as a first-class, enforced concern:
  - `docs-living` skill: read → update/create `/docs` → CHANGELOG → ADR for every
    change, with no-regression discipline; every repo must have a `/docs`.
  - `changelog.py` (Keep a Changelog maintainer) and `adr.py` (Architecture
    Decision Records) operating on the target project.
  - `/praxis:docs` command; CHANGELOG/ADR/docs templates.
  - Orchestrator gained a mandatory "update living knowledge" phase and report
    rows; completeness-auditor now fails changes with stale/missing docs;
    bootstrap scaffolds `/docs` + `CHANGELOG.md`; session_audit and doctor report
    their presence.
- Improved Praxis's own documentation: `docs/README.md` index, `docs/KNOWLEDGE.md`,
  and an example ADR modelling the standard.

## [0.5.0] - 2026-07-16
### Added
- **Auto-pilot mode** (`/praxis:autopilot on|off`, env `PRAXIS_AUTOPILOT`,
  `autopilot.py`): zero user-facing questions. praxis does its own QA and
  resolves every design decision by the best-practice that fits, logging each under
  a new report section "Decisions taken autonomously". Safety guards and the
  quality/task gate stay active; it stops only for a hard external blocker.
- **best-practices skill + catalog** (`skills/best-practices/`): selects and applies
  the minimal relevant engineering best-practices for the change's domains (SOLID,
  DDD, REST, ACID/CAP, OWASP, testing, clean code, performance, concurrency,
  functional) from a curated, need-indexed catalog; respects KISS/YAGNI.

### Changed
- Orchestrator, prompt-architect, quality-rubric, output style, and SessionStart
  directives now apply best-practices by need and honour auto-pilot (decide-don't-ask
  with a correctness→best-practice→consistency→simplicity→reversibility procedure).
- Report template gained "Best-practices applied" and "Decisions taken autonomously".
- doctor now reports auto-pilot state.

## [0.4.0] - 2026-07-16
### Changed (design simplification per user feedback)
- **Removed the keyword-based intake router** (`intake_router.py` + the
  `UserPromptSubmit` hook). No prompt-text classifier decides behaviour anymore;
  the workflow directive is always injected at SessionStart and enforcement is
  change-based — deterministic regardless of phrasing.
- **praxis now runs the completion loop itself** via the Stop gate + a
  `task.json` state file (`task_state.py`), so the user never runs `/goal`. The
  loop keeps the session working until the task is marked done, lets Claude stop
  to ask at genuine decision points (`waiting`), and is bounded by a hard turn cap
  and the usual escapes. `/goal` is now documented as an optional power-tool only.
- Reframed docs (MODES/FLOWS/ARCHITECTURE/USAGE/README) around: "you write the
  prompt and pick the effort; praxis handles goals/workflows/subagents." Made
  the effort-agnostic guarantee explicit (identical at high ↔ ultracode).

### Added
- `task_state.py` (open/resume/waiting/done/clear/status) driving the loop.

## [0.3.0] - 2026-07-16
### Added
- **Autonomous task sizing:** the `UserPromptSubmit` router now classifies each
  implementation prompt as trivial / standard / substantial and injects the
  matching workflow, so the user states the macro idea and Claude self-drives.
- **Auto `/goal` proposal** for substantial tasks: praxis builds a completion
  condition from the spec (phrased around transcript-visible proof incl. the
  praxis audit) and offers to pair it with auto mode.
- **docs/MODES.md**: effort / `ultrathink` / `ultracode` / `/goal` / auto-mode
  recipes and how praxis composes with them.

### Changed
- Output style, task-orchestrator, quality-rubric, and SessionStart directives now
  express end-to-end autonomy ("own the task; interrupt only at real decision
  points") and clarify that praxis's Stop gate is its own persistence loop while
  `/goal` is the optional layer for multi-step tasks.

## [0.2.0] - 2026-07-16
### Added
- **task-orchestrator** skill: end-to-end pipeline (restructure → investigate →
  plan → implement → audit → report) for any implementation request.
- **prompt-architect** skill: restructures vague prompts into explicit specs
  (goal, scope, non-goals, acceptance criteria, assumptions, open questions).
- **code-craft** skill: professional comment discipline and code craftsmanship
  standards.
- **completeness-auditor** subagent + **scan_placeholders.py**: deterministic +
  semantic enforcement of "no placeholders/stubs and no silently narrowed scope".
- **UserPromptSubmit** intake router (`intake_router.py`): auto-detects
  implementation intent (English + Italian) and routes terse prompts into the
  full pipeline.
- Commands `/praxis:task` and `/praxis:spec`.
- Plan-first, completeness, and structured-reporting doctrine added to the
  `praxis-quality` output style.

### Changed
- `quality-rubric` now includes the completeness vertical and emits the canonical
  structured report.
- Stop gate now lists deterministic placeholder findings in its block message.
- `SessionStart` standing directives updated for the end-to-end workflow.

## [0.1.0] - 2026-07-16
### Added
- Initial release.
- `praxis-quality` output style (always-on quality doctrine).
- Skills: `bootstrap`, `quality-rubric`, `claudemd-living`, `capability-discovery`.
- Read-only vertical subagents: `repo-cartographer`, `doc-reference-finder`,
  `duplication-scanner`, `regression-sentinel`, `adversarial-auditor`,
  `edge-case-hunter`, `perf-scalability-analyst`, `claudemd-verifier`.
- Hooks: SessionStart audit, PreToolUse secret/destructive guard, PostToolUse
  auto-format, Stop quality gate.
- Commands: `/praxis:bootstrap`, `/praxis:audit`, `/praxis:sync`,
  `/praxis:discover`, `/praxis:doctor`.
- Templates for CLAUDE.md, settings, and MCP wiring.
