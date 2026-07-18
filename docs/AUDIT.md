# Self-Audit (v0.7.0)

Praxis applied its own audit rubric to itself. This records the findings and the
fixes — the kind of living-knowledge artifact Praxis produces for any project.

## Scope
The plugin's scripts, hooks, skills, manifests, docs, and its fitness as an
enterprise-grade Claude Code tool. Lenses: completeness, adversarial/security,
edge-cases, correctness, and professional/OSS hygiene.

## Findings & resolutions

| # | Finding | Severity | Resolution |
| - | ------- | -------- | ---------- |
| 1 | No test suite — Praxis preached "no regression" but couldn't prove its own | High | Added `tests/` (16 stdlib unittest cases) covering guard, scanner, gate/task-loop, changelog, ADR, verifier, common; wired into CI |
| 2 | No plugin self-validation | High | Added `selfcheck.py` (manifests, version agreement, hook→script refs, frontmatter, compile); wired into CI and `/praxis:doctor` |
| 3 | PostToolUse formatted with *any* formatter on `PATH`, even one the project doesn't use — could fight project conventions | High (correctness) | `post_edit.py` now formats only with a formatter the project actually adopts (config/adoption signal); canonical formatters (gofmt/rustfmt) still always run |
| 4 | Destructive-command guard missed exfiltration/persistence vectors | Medium (security) | Added patterns: env/secret piped to network, writes to `authorized_keys` and `/etc`, plaintext credential-helper |
| 5 | Placeholder scanner could flag prose comments as "commented-out code" | Medium (noise) | Tightened the pattern to real statement shapes; fewer false FAILs |
| 6 | No security posture / contributor docs | Medium (hygiene) | Added `SECURITY.md` (threat model, known limits) and `CONTRIBUTING.md` |
| 7 | No release management for target repos | Medium | Added `/praxis:release` (SemVer from Conventional Commits + changelog finalize) |
| 8 | Requirements/compatibility under-specified | Low | Added a Requirements & compatibility section (Claude Code version, Python, OS, CI guarantees) |

## Deliberately not changed (documented trade-offs)
- **Green report remains trust-based** (ADR-0001): the deterministic scans are the
  backstops; a full cryptographic proof of audit would add complexity without
  proportional value.
- **Plan-mode stays guided, not a hard pre-edit block**: a deterministic
  "non-trivial" test would over-fire.
- **Monorepo per-package test detection**: session_audit detects one primary test
  command; per-package detection is a candidate for a future release.

## Result
Self-check: OK. Test suite: 16/16 green. The tool now proves its own integrity in
CI and no longer trusts unverified assumptions about the host environment.

---

## v1.0 — remaining trade-offs resolved

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
  block would over-fire) — documented, not a defect. See ROADMAP for optional
  native-hook gating.

Praxis is v1.0: stable public surface (`docs/STABILITY.md`), CI-verified integrity
and tests, and no known correctness or completeness gaps in the core.

---

## v1.1 — second audit pass

| # | Finding | Severity | Resolution |
| - | ------- | -------- | ---------- |
| 1 | `rglob` hot paths walked `node_modules`/`.git`/build dirs → slow SessionStart on large/enterprise repos | High (perf) | Added `common.find_files` (os.walk with in-place dir pruning + caps); refactored workspace detection, nested-CLAUDE.md scan, and the non-git secret scan to use it |
| 2 | Secret-read guard only covered `cat`/`less`/… — `grep`/`awk`/`sed`/`source`/`.` bypassed it; the sensitive path could be a non-first arg | High (security) | Token-based scan of reader command segments; blocks the sensitive path in any argument; added `source`/`.` sourcing |
| 3 | Destructive-command guard missed long-form `rm --recursive --force /` (a `\b` regex bug) | Medium (security) | Fixed the pattern; verified |
| 4 | No per-repo configuration | Medium (enterprise) | Added committed `.praxis.toml` (`gate.enabled`, `gate.require_tests`, `autopilot.default`, `audit.depth`), stdlib parser, wired into gate/autopilot/doctor |
| 5 | selfcheck didn't catch dangling `@praxis:agent` refs or bad marketplace source paths | Medium | selfcheck now validates both (61 checks) |
| 6 | No dev DX / OSS hygiene (Makefile, CODEOWNERS, PR/issue templates) | Low | Added |

Two of these (1–2) were genuine bugs found by writing the checks; the guard fixes
were caught by new tests. Suite grew 20 → 31 cases.
