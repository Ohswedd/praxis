# Self-Audit (v0.7.0, v1.5, v2.0)

Praxis applied its own audit rubric to itself. This records the findings and the
fixes: the kind of living-knowledge artifact Praxis produces for any project.

## Scope
The plugin's scripts, hooks, skills, manifests, docs, and its fitness as an
enterprise-grade Claude Code tool. Lenses: completeness, adversarial/security,
edge-cases, correctness, and professional/OSS hygiene.

## Findings & resolutions

| # | Finding | Severity | Resolution |
| - | ------- | -------- | ---------- |
| 1 | No test suite: Praxis preached "no regression" but couldn't prove its own | High | Added `tests/` (16 stdlib unittest cases) covering guard, scanner, gate/task-loop, changelog, ADR, verifier, common; wired into CI |
| 2 | No plugin self-validation | High | Added `selfcheck.py` (manifests, version agreement, hook→script refs, frontmatter, compile); wired into CI and `/praxis:doctor` |
| 3 | PostToolUse formatted with *any* formatter on `PATH`, even one the project doesn't use: could fight project conventions | High (correctness) | `post_edit.py` now formats only with a formatter the project actually adopts (config/adoption signal); canonical formatters (gofmt/rustfmt) still always run |
| 4 | Destructive-command guard missed exfiltration/persistence vectors | Medium (security) | Added patterns: env/secret piped to network, writes to `authorized_keys` and `/etc`, plaintext credential-helper |
| 5 | Placeholder scanner could flag prose comments as "commented-out code" | Medium (noise) | Tightened the pattern to real statement shapes; fewer false FAILs |
| 6 | No security posture / contributor docs | Medium (hygiene) | Added `SECURITY.md` (threat model, known limits) and `CONTRIBUTING.md` |
| 7 | No release management for target repos | Medium | Added release support (SemVer from Conventional Commits + changelog finalize), reachable in 2.0 as `/praxis:ship release` |
| 8 | Requirements/compatibility under-specified | Low | Added a Requirements & compatibility section (Claude Code version, Python, OS, CI guarantees) |

## Deliberately not changed (documented trade-offs)
- **Green report remains trust-based** (ADR-0001): the deterministic scans are the
  backstops; a full cryptographic proof of audit would add complexity without
  proportional value.
  *(Superseded in v1.5: see [ADR 0010](adr/0010-the-quality-report-runs-the-tests-itself.md):
  the report's test evidence is now measured by `report.py`, not reported by its
  caller. The vertical verdicts are still trust-based.)*
- **Plan-mode stays guided, not a hard pre-edit block**: a deterministic
  "non-trivial" test would over-fire.
- **Monorepo per-package test detection**: session_audit detects one primary test
  command; per-package detection is a candidate for a future release.

## Result
Self-check: OK. Test suite: 16/16 green. The tool now proves its own integrity in
CI and no longer trusts unverified assumptions about the host environment.

---

## v1.0: remaining trade-offs resolved

- **Green report is now evidence-backed** (was trust-based). `report.py` records
  the test command + exit code and per-vertical verdicts; the Stop gate refuses a
  "green" report that lacks a passing test run when the repo has a test command.
  (ADR-0003.)
- **Monorepo awareness added.** `common.detect_workspaces` + `workspaces.py`
  surface packages; session_audit reports them and the orchestrator/regression run
  the changed package's tests, not just the root.
- **Robustness fix (found by the new tests):** the change signature now excludes
  Praxis's own `.claude/.praxis/` state, so recording a report can't perturb the
  signature in repos that haven't git-ignored it yet.
- **Plan-mode remains guided by design** (a deterministic "non-trivial" pre-edit
  block would over-fire): documented, not a defect. See ROADMAP for optional
  native-hook gating.

Praxis is v1.0: stable public surface (`docs/STABILITY.md`), CI-verified integrity
and tests, and no known correctness or completeness gaps in the core.

---

## v1.1: second audit pass

| # | Finding | Severity | Resolution |
| - | ------- | -------- | ---------- |
| 1 | `rglob` hot paths walked `node_modules`/`.git`/build dirs → slow SessionStart on large/enterprise repos | High (perf) | Added `common.find_files` (os.walk with in-place dir pruning + caps); refactored workspace detection, nested-CLAUDE.md scan, and the non-git secret scan to use it |
| 2 | Secret-read guard only covered `cat`/`less`/…: `grep`/`awk`/`sed`/`source`/`.` bypassed it; the sensitive path could be a non-first arg | High (security) | Token-based scan of reader command segments; blocks the sensitive path in any argument; added `source`/`.` sourcing |
| 3 | Destructive-command guard missed long-form `rm --recursive --force /` (a `\b` regex bug) | Medium (security) | Fixed the pattern; verified |
| 4 | No per-repo configuration | Medium (enterprise) | Added committed `.praxis.toml` (`gate.enabled`, `gate.require_tests`, `autopilot.default`, `audit.depth`), stdlib parser, wired into gate/autopilot/doctor |
| 5 | selfcheck didn't catch dangling `@praxis:agent` refs or bad marketplace source paths | Medium | selfcheck now validates both (61 checks) |
| 6 | No dev DX / OSS hygiene (Makefile, CODEOWNERS, PR/issue templates) | Low | Added |

Two of these (1–2) were genuine bugs found by writing the checks; the guard fixes
were caught by new tests. Suite grew 20 → 31 cases.

---

## v1.5: behavioural audit (why praxis under-delivered in practice)

This pass audited praxis against its own *observed* behaviour rather than its
code: it left regressions, skipped skills on command-less prompts, delivered
MVP-shaped work, and produced generic UI. Each symptom traced to a mechanism,
not to wording.

| # | Finding | Severity | Resolution |
| - | ------- | -------- | ---------- |
| 1 | The pipeline was announced once at `SessionStart`; skill selection then relied on the model matching a skill description. A bare prompt late in a session skipped the orchestrator, the front-end pipeline, and the audit | High (correctness) | Added `prompt_router.py` on `UserPromptSubmit`: classifies each request and names the exact skills it needs ([ADR 0008](adr/0008-per-prompt-skill-routing-via-userpromptsubmit.md)) |
| 2 | The per-change gate blocked the *first* stop attempt per change signature and allowed every one after it: the audit was effectively optional | High (correctness) | Refusals now escalate over 3 attempts, each naming something more concrete, then release with an instruction to tell the user the change is unaudited ([ADR 0009](adr/0009-escalating-stop-gate-refusals-over-a-single-reminder.md)) |
| 3 | `report.py` accepted a caller-supplied `--tests-exit`, so an unverified "green" report could close the gate on a change whose tests never ran | High (correctness) | `report.py` executes the test command itself; reports without a verified run are rejected ([ADR 0010](adr/0010-the-quality-report-runs-the-tests-itself.md)) |
| 4 | Unfinished markers in the diff were printed as advisory text the model could step past | High (completeness) | They now lead the block message, cited file:line, and must be implemented or removed and reported as out of scope |
| 5 | Only literal markers (`TODO`, `NotImplementedError`) were detected. Deferred work usually arrives as an apologetic comment instead: "for now", "in a real implementation", "you can extend this", "omitted for brevity" | High (completeness) | Added a deferral-prose marker class, matched in comments only, exempt in prose files and on `praxis:ack` lines |
| 6 | The front-end pipeline was entirely process and contained no craft: it made an interface correct, then assumed good would follow. A uniformly generic page passed consistency auditing perfectly | High (quality) | Added `frontend-pipeline/reference/craft.md` and a craft vertical in the design-consistency-auditor ([ADR 0011](adr/0011-design-craft-as-an-explicit-reference-not-implied-by-the-des.md)) |
| 7 | `report.py` failed open: a crash exited 0, implying a report that was never written | Medium (correctness) | It now exits 1 with the reason; the hooks keep their fail-open behaviour, which is correct for them |
| 8 | A test run that never started (timeout, missing binary) discarded its reason from the report | Low (diagnosability) | The output tail is kept for every non-passing run, including one that never started |

Findings 2, 3, 4 and 7 were latent defects in praxis's own enforcement: the
gate and the report were softer than their documentation claimed.

### Reverse audit of the fixes

The change above was then audited adversarially in its own right, against its own
claims ("the gate can never trap a session", "a claim is not evidence"). It broke
both. Every finding below is a defect introduced or amplified by the v1.5 fixes,
not by the code they replaced:

| # | Finding | Severity | Resolution |
| - | ------- | -------- | ---------- |
| 9 | Both release caps depended on a state write that `write_state` swallows on failure. An unwritable `.claude/` (read-only mount, full disk, or a user who ran `touch .claude/.praxis` after misreading the escape hatch) meant the counters never advanced, **every turn blocked, forever** | Critical | The gate uses `write_state_strict` and fails open when the record cannot be persisted |
| 10 | One shared session record: two Claude windows on the same repo wiped each other's counters every turn, so neither ever reached a cap, both blocked indefinitely | High | Each session owns its own entry, pruned oldest-first |
| 11 | Escalation was keyed on the change signature, which changes whenever Claude edits between two Stops. The refusal restarted at attempt 1 every turn, so it never sharpened and the final disclosure never fired: the gate then released **silently** | High | Escalation keyed on the session refusal total; the cap turn always carries the disclosure, and only the turn after releases |
| 12 | `--tests true` or `pytest \|\| true` exits 0 without running the suite, and the gate accepted it. A bare `report.py record` with no verticals was also vacuously green | High | Substituted commands are recorded and rejected by the gate; an empty vertical set is 'fail' |
| 13 | The gate fired on trees dirtied *before* the session: demanding a seven-vertical audit of someone else's work, and reporting their unfinished markers as "this change leaves N unfinished marker(s) in its own diff". The escalation multiplied the cost from 1 wasted turn to 12 | High | A tree byte-for-byte as the session found it is not gated |
| 14 | `--tests` was a clean path around `guard_paths`: `report.py record --tests "cat .env"` executed it via `shell=True`, with the output landing in `quality_report.json` | Medium (security) | Sensitive paths in `--tests` are refused; the persisted output tail is secret-redacted |
| 15 | `subprocess.run(shell=True, timeout=…)` kills only the shell: the real test process survives holding the output pipe, so the wait never returns. `capture_output` also buffered an entire verbose suite in memory for up to 900s | Medium | Own process group, killed as a tree; output streamed to a temp file, only the tail read |
| 16 | The routing directive told Claude to record the report *before* updating docs/CHANGELOG, and the report is keyed to the change signature, so the doc write invalidated the audit it had just passed | Medium | The directive and the rubric both record the report last |
| 17 | A `cap_reached` task left the per-change gate dead for 12h; `task_state.py open x --max 0` was an undocumented permanent gate-off switch | Medium | `cap_reached` falls through to the quality gate; `--max` is clamped to ≥ 1 |
| 18 | `"evidence": null` in a hand-edited report raised `AttributeError` in the gate, which fails open, a one-line bypass | Low | Normalised with `or {}` |
| 19 | The router's question guard was anchored at `^`, so "Please explain how X works: don't change anything" hit `change` and was routed as an implementation request, which could open a 25-turn task loop on a read-only question | Low | Politeness prefixes allowed before the interrogative; an explicit "don't change / read-only" instruction outranks every verb; `support`/`handle` dropped from the verb list |

Three of these (9, 10, 11) would have made the release worse than the bug it
fixed: a gate that blocks forever, or one that quietly stops blocking at the
moment it matters. They were found only because the fixes were audited as
adversarially as any other change, which is the point of the rubric.

Suite grew 82 → 98 cases.

---

## Pass 3 (v2.0): the rules that only existed in prose

This pass started from seven reported symptoms rather than from a code read. Each
one traced to the same shape of defect: a rule praxis stated clearly, repeatedly,
and in the right places, with nothing but the model's memory enforcing it.

| # | Finding | Severity | Resolution |
| - | ------- | -------- | ---------- |
| 1 | `scan_placeholders.py` read `git diff`, which cannot see an untracked file, and fell back to the staged diff instead of scanning both. A change made entirely of new files was scanned as if it were empty, which is exactly where unfinished work lands | High (completeness) | `common.added_line_pairs` unions the unstaged diff, the staged diff, and the full content of every untracked file; both scanners and the gate use it |
| 2 | The UI verticals ran when the request sounded like design work. "Fix the checkout bug" and "update `Header.tsx`" are UI work that never says so, and shipped audited on the seven code verticals only | High (quality) | `common.is_ui_path` resolves it from the changed file list; `report.py` and the gate both refuse a green report without both UI verdicts ([ADR 0014](adr/0014-ui-work-is-decided-by-the-surface-a-change-touches.md)) |
| 3 | The no-AI-attribution rule lived in the git-delivery skill's prose. It has to hold on every commit forever, and a single lapse is permanent: the trailer is then in the history | High (correctness) | The PreToolUse guard denies any `git commit`, `git tag`, `gh pr create`, `gh release create` or `gh issue` command carrying one ([ADR 0013](adr/0013-house-rules-enforced-by-hooks-not-by-doctrine.md)) |
| 4 | The em-dash ban had the same shape and the same outcome, in the plugin's own text most of all: roughly 700 of them across 82 files | Medium (quality) | `scan_style.py` over the whole change, blocked by the gate; `selfcheck.py` holds praxis's own content to it so CI fails rather than shipping the contradiction |
| 5 | Documentation asserted configurable behaviour as constant. `docs/FLOWS.md` still claimed the gate "prompts once per signature per session" (untrue since the escalating refusals) and that "intent is not classified from the prompt" (untrue since the router). The reported case was delivery policy: docs saying a human merges every PR, in a repo with `auto_merge` on | High (correctness) | `drift.py` compares assertions against the live configuration and checks every documented reference resolves; the SessionStart audit prints the resolved values so no turn has to trust prose ([ADR 0015](adr/0015-documentation-drift-detected-against-the-live-configuration.md)) |
| 6 | Thirteen commands, five of which were a phase, a scope, a sibling concern, or a toggle of another. A large palette hides the right entry point and multiplies what can drift | Medium (usability) | Nine commands with modes as arguments; `selfcheck.py` now fails on a dangling `/praxis:` or script reference so a rename cannot leave instructions pointing at nothing ([ADR 0016](adr/0016-nine-commands-with-modes-as-arguments.md)) |
| 7 | The deferral vocabulary missed the phrasings that carry the most weight: "out of scope for this", "future work will", "not production-ready", "we will fix this later" | Medium (completeness) | Vocabulary widened; the orchestrator and the session directives now say explicitly that "Out of scope" is for what the user excluded, not for work that was started and abandoned |

The common lesson is finding 5 in general form: **a rule that is only written down
is a rule that holds until the moment it matters.** Every fix in this pass moved
one from the doctrine layer into the hook layer, or made the truth resolvable at
read time instead of quotable from memory.

### Caught by the pre-release verification

The release itself was fanned out to six independent read-only checks before the
irreversible steps. Twenty-eight of thirty-six raw findings were refuted; four
were real defects introduced by this very change, and are fixed above:

| # | Finding | How it was found |
| - | ------- | ---------------- |
| 8 | `docs/STABILITY.md` inserted the "Removed in 2.0" heading into the middle of the "Stable" list, so three stable-surface guarantees (install identifier, managed marker, docs contract) rendered as *removed* in the normative statement of what this MAJOR bump breaks | reading the rendered structure, not the diff |
| 9 | One em dash survived the repo-wide purge. `praxis:ack` is line-based, so the row of the Pass 2 table that *documents* the annotation exempted itself, and the scanner reported clean | scanning every tracked file for U+2014 directly, bypassing the ack |
| 10 | The changelog advertised `we will fix this later` as a matched deferral phrase, but the shipped pattern was `(we\|i)'?ll`, which matches only the contraction | importing the shipped module and running its compiled patterns against the cited strings |
| 11 | The git index was stale: the finalized `## [2.0.0]` heading and the Makefile's drift target existed only in the working tree. Committing the index would have published a MAJOR release whose GitHub page fell back to "see CHANGELOG.md" with no notes | running the release workflow's own notes regex against `git show :CHANGELOG.md` |

Finding 9 is the instructive one. A line-scoped opt-out cannot distinguish a line
that *uses* the escape hatch from a line that *describes* it, so any documentation
of `praxis:ack` silently exempts itself. The rule that catches this is the same one
the release is built on: verify the property directly, never through the mechanism
that is supposed to enforce it.

### What was deliberately left guided

- **Vertical-auditor reasoning.** The gate can check that a verdict exists for
  every required vertical and that the test evidence is real. It cannot check that
  an auditor thought hard. That remains the honest gap, and the deterministic
  scans remain its backstop.
- **The ASCII double hyphen.** Banning ` -- ` would catch an em dash typed as
  ASCII, and would also catch `git ls-files -- path` and `npm test -- --watch`.
  In a repository the separator is far more common than the punctuation mark, so
  the rule stops at the Unicode dashes.
- **The unspaced en dash.** Correct typography in a numeric range (`320px-1440px`
  written properly), so it is left alone; only the spaced sentence dash is refused.
- **Drift detection is conservative by design.** It catches unqualified
  contradictions and broken references, not every possible inaccuracy. A report
  that fires on correct documentation is a report nobody reads, and that failure
  mode would reintroduce the problem it exists to solve.

Suite grew 98 to 131 cases.

---

## v3.2: the pipeline audited against its own reported failures

Six defects reported from real sessions, all of the same family: praxis stated a
rule, complied with it in the abstract, and had no way to tell when it had not
been followed. The fix in each case is the same move the project has made before,
applied to a claim it was still trusting.

| # | Reported failure | Root cause | Resolution |
| - | ---------------- | ---------- | ---------- |
| 1 | Docs and adjacent files regress or go unupdated on a "finished" task | "documentation is part of done" existed only in prose, and no scanner could see documentation a change *removed*, because every one of them reads added lines | `knowledge_check.py`: changelog moved, a document moved, nothing deleted; run by `report.py` and named in the gate's refusal |
| 2 | `.praxis.toml` sometimes absent after contributor-mode scaffolding: bug or normal? | normal, and unknowable: `doctor.py` hardcoded the owner-mode path, so a clone configured entirely through its git-excluded local layer reported "defaults" | both surfaces name the layers that exist, the layer praxis would write here, and that the file is optional; `resolve_switch` reports the layer that actually set a value |
| 3 | A `CHANGELOG.md` created and committed in a repo that never had one | the rule held for the helpers (`changelog.py` routes itself correctly) and nothing routed a direct write. The three containment layers all protect praxis's *own* files, and this file is the project's | the guard refuses to create or commit a project artifact the repo lacks, at the file tool, the shell and the index |
| 4 | Claims in tests and audits that a second look shows were never verified | the report measured the test run and trusted everything else: the scanners (which the gate skips once a report exists), and every vertical verdict | `report.py` runs all three scanners itself and records what they found; each verdict needs a summary and a citation that resolves; the gate re-derives the verdict from the evidence rather than reading `status` |
| 5 | No way to actually exercise what was built | praxis had no notion of running the product, only of running its tests | `detect_runtime_command` + `report.py --runtime` + the `runtime-verification` skill |
| 6 | Too much debt left behind; three or four rounds needed to clear it | a green report bypassed the placeholder and style scans entirely, so unfinished work shipped inside a change that reported itself clean | closed by #4: the scanners run at record time and a report cannot be green over an unresolved finding |

Findings 4 and 6 are the same defect seen from two ends, and it is the most
instructive one in this list. The gate's fast path was `has_green_report ->
allow`, so every deterministic scan it performed applied *only* while no report
existed. Recording a report was therefore not the consequence of passing the
scanners, it was the way around them. The lesson is the one from finding 9 above,
restated: verify the property directly, never through the mechanism that is
supposed to enforce it.

### What is still guided, stated honestly

- **The ledger proves substantiation, not execution.** A verdict now needs a
  summary and a citation that resolves against the repository, which refuses the
  invented `file:line`. It cannot prove a subagent ran, and praxis does not claim
  it does.
- **The living-knowledge check is a floor, not a judgement.** It asks whether the
  documentation moved, not whether what was written is any good. The
  doc-reference auditor and human review remain responsible for that.
- **The contributor changelog check is weaker off-repo.** When the record lives in
  git-excluded local knowledge, no diff can see it, so the check verifies that an
  `[Unreleased]` entry exists rather than that it describes today's work. Stated
  in the script rather than dressed up.
- **Runtime verification needs a harness.** In a project without one, praxis
  reports the gap and asks for a stated manual check, rather than inventing a
  command or adding a dependency the maintainers never agreed to.

Suite grew 264 to 310 cases.
