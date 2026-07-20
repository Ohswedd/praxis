# 6. Repo-wide scan as a deterministic shard ledger reusing the vertical auditors

- Status: accepted
- Date: 2026-07-20

## Context
Praxis audited changes (diffs) but had no way to audit an entire already-developed repository. An LLM-driven whole-repo audit fails by silent sampling on large codebases, by over-reporting without a counterweight, and by losing progress across sessions.

## Decision
Add /praxis:scan backed by a stdlib ledger CLI (repo_scan.py): deterministic inventory with counted exclusions, subsystem-grouped shards capped by files/lines, per-shard-per-dimension audit marks, and an explicit finding lifecycle (open -> confirmed/refuted/downgraded -> fixed/deferred). Reuse the seven existing vertical auditors with scope-generalised prompts instead of adding parallel repo-scoped agents; add one new agent (finding-verifier) for the adversarial reverse audit. The final report is computed from ledger state and prints INCOMPLETE for any coverage gap. Unlike the fail-open hook scripts, repo_scan.py propagates errors: a silently-lost ledger write would forge coverage claims. Architectural/breaking/irreversible findings are deferred with a remediation plan, never auto-fixed, even in auto-pilot.

## Consequences
Coverage claims are mechanically honest and scans resume across sessions. One more stable CLI/state file to maintain (repo_scan.py, repo_scan.json). Auditor wording is now scope-agnostic (change set or assigned files), which the change-audit path shares.
