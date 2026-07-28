# Changelog

All notable changes to praxis are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- debt.py paid <n> --by "<how>" records how an entry was settled. An entry that says only repaid cannot tell the next reader whether the principal was paid, the debt was designed away, or the premise turned out to be wrong.

### Changed
- The auditors' scoping rules live in one place. They were copied into ten agent briefs on the belief that agent files have no include mechanism; they do, the skills frontmatter field, which preloads a skill's full content into a subagent at startup. The rules are now the review-scope skill, each brief keeps only a byte-checked pointer for the case where a preload is silently skipped, and selfcheck fails on all five ways the wiring can break. Debt entry 1 is repaid, with the false premise corrected in the register rather than quietly dropped.

### Fixed
- debt.py paid --by flattens the note it records. The removal that replaces a previous note is line-anchored, so a note spanning lines left its own tail orphaned in the entry when it was later replaced.
- The review-scope wiring check parses the skills list rather than substring-matching it. A commented-out entry contains the skill name and preloads nothing, so it would have been reported as wired when it was not.

## [3.1.0] - 2026-07-28

### Added
- The technical-debt vertical. @praxis:debt-auditor asks what a change will cost later rather than whether it is correct now: shortcuts and workarounds, coupling and duplication something will have to keep in sync by hand, abstractions the change has made wrong, deprecated or pinned dependencies, and tests that lock in implementation rather than behaviour. It runs in the quality rubric and as a repo-scan dimension.
- debt.py and docs/DEBT.md, the debt register. Debt taken for a stated reason and written down is a decision; the same shortcut taken silently is the defect, because the next person meets the consequence without the reason. Entries carry the interest (what it costs, and how often) and the principal (what the real fix is), and an entry without both is refused, since a register of complaints stops being read. The debt-auditor does not re-report what is listed there, and treats what it finds that is not listed as a finding.
- scope.py: the review scope in one place. It prints the base, the commits on the branch, the files under review and the exact diff commands, so the rubric and every subagent work from one resolved answer instead of each guessing.
- task_state.py carries a plan and a delivery binding: --subtasks at open time, plan to re-declare, subtask start|done to track progress, and delivery --pr to bind the task to its pull request. A task cannot close while a subtask is unfinished, subtask done records the commit each one landed on, and it warns when a subtask shares a commit with the previous one, which is the moment the tracking disappears.
- docs/DEBT.md, and a self-check that no auditor can silently lose its review scoping. The scoping preamble is repeated in each agent brief because agent files have no include mechanism; the check catches an omission, and the remaining wording drift is recorded as debt entry 1 rather than left implicit.

### Changed
- Every auditor resolves the review scope before judging, and states the base it used. The regression sentinel reads the commits in order rather than as one squashed diff: a signature changed in one commit with its callers updated in another is fine, and the same change with the callers never updated is a regression a combined diff makes no easier to see. It also hunts what a branch did to itself (a later commit undoing an earlier one usually means the same mistake survives elsewhere), follows renames, and treats every deletion as a behaviour that no longer happens.
- prompt-architect splits any request with more than one deliverable into ordered subtasks, each independently completable and worth exactly one commit, with dependencies stated rather than pretended away. Where one change forces another it stays a single subtask, because splitting it produces a commit that does not work on its own.
- One task is one branch is one pull request, with each subtask its own commit, so the version history matches the work rather than being reconstructed from it. Two unrelated tasks never share a branch. task-orchestrator, git-delivery and the prompt router all state it, and the canonical report gains a Delivery section.
- The session audit reports a branch's unaudited commits, not just its uncommitted files, so a session resumed on a branch mid-task is told what is under review. scope.py reports an unresolved base and a truncated commit listing rather than printing a confident count, and labels a file that was committed and then edited again as both.

### Fixed
- A change stopped being reviewable the moment it was committed. git diff, git diff --staged and the dirty-tree check all go empty on the first commit, so the scanners found nothing, the auditors reviewed nothing, and the Stop gate opened. The review scope is now the branch: every commit since it left its base, plus the working tree and untracked files, covered by changed_files, added_line_pairs, the change signature and the gate alike. The better the delivery discipline, the worse this got, which made it a blocker for one-commit-per-subtask.
- debt.py paid <n> could close a different entry. A regex spanning the named heading to the next open status line backtracks past an already-repaid entry into the following one, retiring a debt nobody decided to retire and reporting success for the number the user asked for. Repayment is now bounded to the entry's own block, list parses block by block so one malformed entry cannot hide the next, a title is flattened so it cannot inject a heading or skew the numbering, and list and paid no longer create the register as a side effect of reading it.
- An unresolvable review base meant 'review nothing'. A stale origin/HEAD left by an upstream branch rename, or a committed .praxis.toml naming a branch that does not exist, was enough to make praxis declare a branch full of unreviewed commits empty and release the gate. 'No base' and 'could not resolve a base' are now separate answers, the built-in branch names are always tried so a repository cannot switch the audit off through its own config, and an unresolved base falls back to asking whether this branch carries commits no other ref has.
- The review base is now the nearest of the candidates rather than the first that resolves. A stale origin/main dragged unpushed commits from the local default branch into the review, so the gate reported unfinished markers in files the branch never touched.
- A malformed subtask plan released the Stop gate. task.json is read straight off disk, and a plan that was a string or a list of strings raised inside the refusal message, which reached the fail-open handler: an open, unfinished task with unreviewed work ended the turn cleanly. The plan is now coerced rather than trusted.
- A repo-scan ledger created before a dimension existed refused to record it and went on certifying full coverage from the shorter list. Ledgers now adopt dimensions praxis knows and they did not, which correctly reports the affected shards as incomplete instead of claiming coverage that never happened.
- task_state.py read the first digit anywhere in argv as the subtask number, so 'subtask done --commit 3' marked subtask 3; plan turned a flag's value into a phantom subtask that could never be finished; the shared-commit warning only compared against the previous subtask, so out-of-order completion and the first subtask both escaped it; and --max had a floor but no ceiling, giving a task loop with no release.
- Generated content committed on a branch was scanned for markers and house style while the identical file untracked was skipped, so a TODO inside a lock file produced a gate block nobody could fix in their own code. Diff-derived paths are filtered like untracked ones.
- State writes used a fixed temp filename, so two Claude Code windows on one clone could truncate each other's half-written file before it was published. Every writer now uses a per-process temp name, and the debt register writes atomically like the rest.

## [3.0.0] - 2026-07-28

### Added
- Workspace modes. praxis resolves whether a repository is yours (owner) or one you only contribute to (contributor), offline from git alone: a remote, real history, and no commit from your git address means you cloned someone else's project. Resolution is PRAXIS_MODE, then .claude/.praxis/workspace, then .praxis.toml [workspace] mode, then detection, and the session audit prints the verdict with its reason every session. Set it with /praxis:config mode owner|contributor|auto.
- In contributor mode every artifact praxis writes stays on the machine: the brief is CLAUDE.local.md, settings are .claude/settings.local.json, praxis config is .claude/.praxis/praxis.toml, and /docs, CHANGELOG.md, docs/adr/ and docs/design/ are joined only if the project already has them, on its terms, otherwise kept under .claude/.praxis/knowledge/. The project's own CLAUDE.md is read and respected, never edited or reconciled, and .gitignore is never touched.
- Three layers keep those artifacts out of a project's history: a marked block in $GIT_DIR/info/exclude (the file gitignore(5) reserves for per-clone patterns that are never shared) makes them invisible to git status and unreachable by git add -A; the PreToolUse guard refuses any command that stages CLAUDE.local.md, .claude/.praxis/ or .claude/settings.local.json, -f included, and refuses to write a praxis path into a .gitignore that is not ours; and a stage-everything command is verified rather than trusted, repairing a missing exclusion and blocking only if the repair fails.
- A second config layer at .claude/.praxis/praxis.toml is read after .praxis.toml and overrides it. It is git-excluded, so a contributor can hold local preferences without editing a config file the upstream project owns, and a malformed shared file no longer discards the local layer.
- New settings: workspace.mode (auto|owner|contributor) and bootstrap.auto, with PRAXIS_MODE and PRAXIS_BOOTSTRAP as session overrides and .claude/.praxis/no-bootstrap as the per-repo opt-out. /praxis:config gained mode and bootstrap, and its status output names the brief, settings and knowledge paths in force.
- assets/workspace.svg: the owner and contributor artifact maps side by side, with the three containment layers.
- The workspace verdict is pinned once detection reaches contributor. Without it the ordinary contribution workflow undid the mode: clone (contributor), set up, fix the bug, commit, and on the next session your own address is in git log, detection says owner, and praxis would start writing a CLAUDE.md and a /docs tree into someone else's repository with nothing excluding them.
- A commit, push or stash is refused while a praxis local artifact is in the index, asked of git rather than inferred from the command string. Pattern matching can always be walked around (git -C .claude add -f settings.local.json, a glob the shell expands after the hook has read the command, git update-index --add); this is the layer that actually holds.
- guard_paths.py refuses a forced stage-everything outright (git add -f ., git add -A -f), because --force exists precisely to override the exclusion that normally hides these files, and it now covers git add ./, quoted pathspecs, --pathspec-from-file, update-index, stash and apply.
- The .gitignore rule is enforced on the shell route too (echo/printf/tee redirects and sed -i), not only through Edit and Write, and it no longer fires on an edit to a .gitignore that already lists the paths, so removing a praxis path stays possible.

### Changed
- BREAKING: /praxis:frontend is removed. The front-end pipeline is unchanged; what went is the fourth way to start it, and the only one that could be used wrongly (typed after the design decisions were made, or not typed at all for the 'fix the checkout bug' that was front-end work all along). The prompt router, the task-orchestrator and the Stop gate all decide it from the surface a change touches. See ADR-0020.
- praxis now bootstraps a repo it does not manage before working in it, in the same turn, instead of printing a recommendation that was routinely stepped past. The instruction is issued at SessionStart and repeated by the prompt router on every actionable prompt; conversational prompts stay silent. Bootstrap writes what is absent without asking and stops only to reconcile a brief praxis did not author, which still goes through @praxis:claudemd-verifier. Opt out with bootstrap.auto = false. See ADR-0018.
- repo_state() and the repo classifier moved from session_audit.py into common.py, so the session audit, the prompt router and the doctor share one definition. It is mode-aware: a bootstrapped contributor clone reads as managed from its CLAUDE.local.md, and the project's own CLAUDE.md is never counted.
- /praxis:doctor checks each artifact where the workspace mode actually keeps it, and asks git whether praxis's state is ignored (via git check-ignore) instead of reading .gitignore, so a working per-clone exclusion is no longer reported as missing.
- changelog.py and adr.py resolve their target through the workspace mode and print the path they wrote, so a session reports where the knowledge landed rather than assuming it went into the project.
- drift.py also reads CLAUDE.local.md, so a local brief that contradicts the live configuration is caught like any other instruction document.
- capability-discovery and bootstrap Step 7 follow the workspace mode: in contributor mode a scaffolded capability goes to .claude/.praxis/capabilities/ and MCP wiring to .claude/settings.local.json, never a committed .mcp.json.

### Fixed
- The per-clone exclusion was written to $GIT_DIR/info/exclude, which in a linked worktree is the worktree's private directory that git never reads. It now uses $GIT_COMMON_DIR/info/exclude, so contributor mode works in a worktree instead of reporting a successful exclusion that did nothing.
- _GIT_PUSH and the new staging patterns shared a self-ambiguous option prefix that backtracked exponentially: 40 dash-separated tokens took 27 seconds to reject against a 15 second hook budget, and a PreToolUse hook that times out does not deny the tool, so a padded command could switch the guard off from inside itself. The prefix is now unambiguous and the same input rejects in 0.03 ms.
- ensure_local_exclusions truncated the rest of the user's exclude file when a praxis block had lost its END marker, and removed only the first of several blocks. It now leaves an unterminated block untouched, strips every complete one, and writes atomically (temp file plus os.replace) like the rest of praxis's state.
- A git call that failed or timed out during detection was read as 'no commits by you' and resolved to contributor, moving a user's own project into contributor mode. Timeouts are now their own state and resolve to owner, said as a default rather than reported as a finding. The unbounded git rev-list --count is bounded, and the author scan has a timeout that fits inside the hook budget.
- A committed .praxis.toml can no longer declare that a repository is ours. It may set workspace.mode = contributor, which only ever withholds writes; owner is reported and then ignored in favour of detection, because a repository you cloned should not get to grant praxis write access to itself.
- _is_praxis_state covers every local artifact, not just the state directory, so a failed exclusion can no longer make the Stop gate see a permanently dirty tree and the scanners audit praxis's own brief.
- The four hand-rolled copies of the switch ladder are one table in common.py. They had already diverged: PRAXIS_GATE=on with a skip-gate file present was reported ON by /praxis:config and treated as OFF by the gate that enforces it, and PRAXIS_AUTOPILOT=yes was ON to one and OFF to the other.
- The gate.enabled drift rule had its two patterns the wrong way round, so it flagged a document for correctly saying the gate is on and could never catch the drift it exists for.
- changelog.py and adr.py exited 0 on every failure, reporting knowledge as recorded that was never written. Both now fail loudly, --type without a value is rejected, and a message word equal to the type is no longer swallowed.
- /praxis:doctor checks every local artifact rather than only the state directory, and distinguishes an already-tracked artifact (git rm --cached) from a missing exclusion, instead of blaming a working exclude file.
- Accessibility and craft on the README assets: the workspace diagram's alt text described a containment layer the image does not show and omitted two rows; the on-dark accent in layers.svg measured 3.4:1 and is now 7.9:1; every asset uses aria-describedby for its long description instead of folding it into the accessible name; and the inventory no longer labels all twelve subagents as vertical auditors when nine of them are.

## [2.0.1] - 2026-07-28

### Added
- selfcheck.py --require-repo asserts the full repo scope instead of detecting it, so CI cannot silently fall back to the smaller scope and report OK for a tree whose marketplace is missing, unreadable, or no longer lists the plugin. make check and the release workflow both use it.
- selfcheck.py rejects an unrecognised argument with a usage line and exit code 2 instead of ignoring it.
- The repo-scope house-style check now covers docs/adr/ as well as docs/*.md, so no directory of authored prose sits outside the check that gates CI.

### Fixed
- selfcheck.py demanded a marketplace manifest that only exists in the source checkout, so /praxis:doctor reported 'plugin integrity: PROBLEM' for every installed plugin, and had since the check was introduced. The checks are now scoped: an installed plugin is verified on everything that ships with it, and the marketplace and repo prose are verified in the source tree. Both selfcheck and doctor name the scope they covered, and a failing integrity line now cites the first problem and how to see the rest instead of printing a bare PROBLEM.
- Scope detection no longer raises on a marketplace manifest that parses but is not a marketplace (a bare list, a string, a non-list plugins key). Such a manifest does not publish the plugin, so it selects installed-plugin scope rather than a traceback.
- The integrity check writes nothing into the directory it checks. It uses the builtin compile instead of py_compile, and /praxis:doctor runs it with bytecode writing disabled, so diagnosing an installed plugin no longer leaves __pycache__ in the plugin cache.

## [2.0.0] - 2026-07-28

### Added
- PRIVACY.md: a plain data-flow statement: Praxis has no backend, makes no network calls and sends nothing to its author; it documents what is read locally, what is written to .claude/.praxis/, and the one place information leaves the machine (Claude Code's own conversation channel to Anthropic)
- New /praxis:config command and config.py: every switch, its value, and where it came from (environment, repo toggle, .praxis.toml, or the default). Asking for a state a higher-precedence source overrides warns and exits non-zero instead of reporting success.
- House-style enforcement. scan_style.py refuses em dashes and spaced en dashes in authored text and AI co-author or generated-by credits, over the whole change; the Stop gate blocks on its findings. Disable per repo with style.ban_em_dash and style.ban_ai_attribution.
- The PreToolUse guard blocks any git commit, git tag, gh pr create, gh release create or gh issue command carrying an AI co-author trailer or a generated-by credit, so the credit never reaches the history.
- drift.py detects documentation that contradicts the repo's live configuration and references (commands, slash commands, links) that no longer resolve. Surfaced at SessionStart, in /praxis:doctor, and at both ends of /praxis:docs.
- The SessionStart audit states the repo's live configuration every session: gate, test-evidence and UI-vertical requirements, auto-pilot, auto-merge with the PR base branch, house style, and the detected test command.
- UI changes are resolved from the changed file list, not from how the request was phrased. A change touching markup, styles, components, design tokens or docs/design/ cannot produce a green report without accessibility=pass and design-consistency=pass. Disable with gate.require_ui_verticals.
- Two README assets: assets/workflows.svg maps four example requests to the skills they run and what the gate then requires, and assets/inventory.svg lists all twelve skills and twelve auditors with the trigger for each.
- selfcheck.py now fails when plugin content references a /praxis: command or a script that does not exist, and when praxis's own text breaks the house style it enforces elsewhere.
- make check and CI now run the drift check, so documentation that contradicts the live configuration or references something that no longer exists fails the build.

### Changed
- BREAKING: consolidated thirteen commands into nine. /praxis:spec is now /praxis:task spec:, /praxis:scan is /praxis:audit repo, /praxis:sync is folded into /praxis:docs, /praxis:release is /praxis:ship release, and /praxis:autopilot is /praxis:config autopilot. No workflow was removed; the same skills run behind fewer entry points.
- BREAKING: autopilot.py and git_delivery.py are replaced by config.py, which toggles auto-pilot, auto-merge and the Stop gate, and reports the source that decided each resolved value.
- Removed every em dash from the plugin's own content, docs, and README, and rewrote the affected sentences with a colon, a comma, parentheses, or two sentences.
- /praxis:docs now covers the CLAUDE.md hierarchy alongside /docs, CHANGELOG.md and ADRs, and starts by running the drift check.

### Fixed
- The praxis:ack annotation is line-based, so a line that documents the annotation exempted itself: one em dash survived in docs/AUDIT.md behind an accidental self-exemption. Removed, and every tracked file is now verified dash-free independently of the ack mechanism.
- The placeholder scan missed brand-new files entirely: it read only git diff, which cannot see an untracked file, and fell back to the staged diff instead of scanning both. It now covers the unstaged diff, the staged diff, and every untracked file.
- Widened the deferral vocabulary the completeness scan matches, including out of scope for this, future work will, not production-ready, and both the contracted and spelled-out forms of we will fix this later.
- The prompt router missed UI work phrased without design vocabulary. It now matches a much wider interface vocabulary and any UI file extension in the prompt, and its delivery directive states the live merge policy rather than a default.
- Corrected stale claims in docs/FLOWS.md: the gate had not prompted once per signature since the escalating refusals landed, and intent has been classified from the prompt since the router landed.

## [1.6.0] - 2026-07-22

### Added
- Marketplace entry now carries the discovery metadata Claude Code and the official plugin directory read (displayName, category, author, homepage, license and keywords) so Praxis presents properly in the /plugin UI and is submission-ready. Validated with 'claude plugin validate'

### Changed
- CI: actions/checkout and actions/setup-python bumped to v7, which run natively on Node 24 and clear the Node 20 deprecation warning
- CI: the release job survives a protected main, it accepts a RELEASE_TOKEN secret and verifies it can write to the branch before stamping anything, instead of failing mid-release with a half-applied version bump
- README rebuilt around its own craft rules: a visual identity (banner, pipeline and layer diagrams as accessible SVGs), a lead that states what praxis is for, and hierarchy in place of a flat 22-row capability table, plus badges, a contents nav, and repo topics/description for discoverability

## [1.5.1] - 2026-07-21

### Fixed
- Marketplace renamed praxis → ohswedd-praxis: an unrelated project (xD4O/praxis) publishes a marketplace with the identical name AND an identical plugin name, and Claude Code keeps only one marketplace per name, silently replacing the first with the second, so praxis@praxis could resolve to the wrong plugin. Install is now praxis@ohswedd-praxis; the plugin name and all /praxis:* commands are unchanged. Existing installs need a one-time 'plugin marketplace remove praxis' then re-add (Claude Code auto-migrates plugin renames, but not marketplace renames)

## [1.5.0] - 2026-07-21

### Added
- Per-prompt skill router (UserPromptSubmit): a bare prompt like "fix the checkout page" now engages the same pipeline as /praxis:task, the router classifies the request and names the exact skills it needs
- Deferral detection in scan_placeholders.py: comments that admit unfinished work without a literal marker ("for now", "in a real implementation", "you can extend this", "omitted for brevity") are findings; a praxis:ack annotation exempts a line
- frontend-pipeline reference/craft.md: the visual judgement the checklists could not encode: the tells of generated UI and what to do instead, hierarchy, typography, space, colour, depth, motion, content-shaped states, and a pre-ship craft checklist

### Changed
- The Stop gate now escalates instead of giving up: it refused once per change state and then allowed any stop, so the audit was effectively optional. Refusals now sharpen over 3 attempts (workflow, then the missing evidence, then the consequence) before releasing, bounded per change state and per session
- report.py executes the project's test command itself and records the real exit code. A caller-supplied --tests-exit is accepted for compatibility but ignored, and reports without a verified run no longer satisfy the gate
- design-consistency-auditor gains a craft vertical: generic defaults, stock decoration, placeholder or invented content, and undesigned states are FAILs, so a uniformly generic page can no longer pass on consistency alone

### Fixed
- Unfinished markers in a change's own diff are now blocking and cited with file:line, instead of being printed as advisory text the model could step past
- Stop gate could block a session indefinitely when its counter state could not be written, and two Claude windows on one repo wiped each other's counters, both are release-cap failures that would have trapped a session
- Stop gate no longer fires on a working tree that was already dirty when the session started: it demanded an audit of pre-existing work and misattributed its unfinished markers to the current change
- report.py: a substituted test command (--tests true) no longer satisfies the gate, an empty vertical set is no longer vacuously green, a sensitive path in --tests is refused, timeouts kill the whole test tree, and secrets in the persisted output tail are redacted

## [1.4.0] - 2026-07-20

### Added
- /praxis:frontend, front-end pipeline (frontend-pipeline skill + reference playbook, accessibility-auditor + design-consistency-auditor agents): business research (client call → goals → audience → competitors → positioning → messaging) → story-first wireframes → design system → development → optimization → ship, for any UI niche, proportional to task size (full/feature/patch routing); design artifacts (docs/design/) kept as living knowledge; quality-rubric, best-practices catalog (new Front-end & UX family), perf auditor (Core Web Vitals), output style, and session directives extended for UI work

## [1.3.0] - 2026-07-20

### Added
- /praxis:scan, repo-wide scanner (repo-audit skill + repo_scan.py shard ledger + finding-verifier agent): audits an entire existing codebase across all seven vertical dimensions, adversarially reverse-audits every finding, fixes confirmed findings in audited change-sets, and reports with deterministic coverage accounting; resumable on large repos

### Fixed
- State writes under .claude/.praxis/ are now atomic (temp file + os.replace): a crash mid-write can no longer corrupt task/report/scan state, which read_state would silently reset to empty

## [1.2.1] - 2026-07-18

### Fixed
- Docs referenced the removed `/output-style` command (gone since Claude Code v2.1.91). The `praxis-quality` output style now auto-enables via `force-for-plugin` and sets `keep-coding-instructions`, so its doctrine layers on top of Claude Code's built-in engineering instructions instead of replacing them.

## [1.2.0] - 2026-07-18

### Added
- Git/GitHub delivery: new `/praxis:ship` command and `git-delivery` skill: write a Conventional Commit, branch, push, and open a PR. Human-in-the-loop merge by default; opt-in `git.auto_merge` (config, `PRAXIS_AUTO_MERGE`, or `git_delivery.py on`) reviews and merges autonomously, never without a green audit or by force-pushing the base branch. Adds `git.auto_merge`/`git.default_branch` config keys and git-delivery status in `/praxis:doctor`.

### Changed
- Compacted and unified every command body; sharpened the `code-craft` comment standard to forbid step-narration and doc-pointer scaffolding.
- Delivery no longer adds AI authorship attribution to commits or PR bodies; the git-delivery skill and CONTRIBUTING.md codify the rule.
- Strengthened simplicity/reuse enforcement: code-craft gains a build-only-what-is-needed section, the duplication auditor now also flags over-engineering (YAGNI), and the orchestrator reinforces it.
- Refreshed the README (delivery, configuration, updated capability/safety sections) and cleaned the architecture diagram's skills list (deduplicated, added git-delivery); plugin/marketplace descriptions mention delivery.

### Fixed
- `changelog.py add` now inserts a new `[Unreleased]` section below the document title and keeps subsections in Keep-a-Changelog order. Removed a dead no-op (`emit_context("")`) in `post_edit.py` and step-narration comments in `changelog.py`.

### Security
- Hardened the PreToolUse guard against branch-history rewrites: it now blocks `gh pr merge --admin` (a branch-protection bypass) and every force-push form (flag, bundled `-f`, or `+refspec`, in any argument order, and behind interposed git global options) so autonomous auto-merge can never override branch protection or rewrite a branch. praxis never force-pushes; a human runs it.

## [1.1.2] - 2026-07-18
### Fixed
- Three component manifests had an unquoted `: ` (colon-space) inside their YAML
  `description:`, which made the loader drop the **entire** frontmatter, so
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
  (`find_files_multi`) instead of four: faster SessionStart on large repos.
  No behaviour change. Test suite: 32 cases; selfcheck: 61 checks.

## [1.1.0] - 2026-07-16
### Added
- **Per-repo config** `.praxis.toml` (`gate.enabled`, `gate.require_tests`,
  `autopilot.default`, `audit.depth`): stdlib parser, wired into the gate,
  auto-pilot, and doctor; template + bootstrap proposal; ADR-0004.
- Dev DX / OSS hygiene: `Makefile`, `CODEOWNERS`, PR and issue templates,
  `.editorconfig`.
- selfcheck now validates `@praxis:` agent references and marketplace source paths.

### Changed
- **Performance:** replaced whole-tree `rglob` with a pruning `os.walk`
  (`common.find_files`) that skips `node_modules`/`.git`/build dirs: fast
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
  (when the repo has a test command) before accepting a green report, no longer
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
- **`selfcheck.py`**: plugin self-integrity validation (manifests, version
  agreement, hook→script references, frontmatter, compilation); in CI and doctor.
- **`SECURITY.md`** (threat model & posture) and **`CONTRIBUTING.md`**.
- **`/praxis:release`** command, SemVer from Conventional Commits + changelog
  finalize.
- **`docs/AUDIT.md`** (self-audit) and **ADR-0002** (self-testing decision);
  Requirements & compatibility section in the README.

### Fixed
- PostToolUse now formats a file only with a formatter the project actually adopts
  (config/adoption signal), instead of any formatter on `PATH`: prevents fighting
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
  change-based: deterministic regardless of phrasing.
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
