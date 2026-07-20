---
description: "Audit, reverse-audit, and fix the entire repository — every shard, every dimension, coverage-honest."
argument-hint: "[path scope] [--report-only]"
---

Use the `repo-audit` skill on ${ARGUMENTS:-the whole repository}.

Run the full pipeline: inventory + shard ledger (`repo_scan.py init`), starting
report, forward audit (every shard × every vertical dimension — adversarial,
edge-case, regression, duplication, performance, doc-reference, completeness),
reverse audit of every finding via `@praxis:finding-verifier`, fix confirmed
findings in audited change-sets (defer architectural/breaking items with a
remediation plan; skip fixing entirely in --report-only mode), and finish with
the coverage-honest final report plus the living-knowledge updates.

Coverage comes from the ledger, not from memory: no shard skipped, no dimension
sampled, no finding acted on unverified, and any gap stated explicitly.
