# 4. Per-repo configuration via .praxis.toml

- Status: accepted
- Date: 2026-07-16

## Context
Teams need to tune Praxis per repository (gate strictness, default auto-pilot)
and have that setting versioned with the code, not hidden in a shell env var.
tomllib is only in Python 3.11+, but Praxis targets 3.8+ and stays stdlib-only.

## Decision
Support an optional committed `.praxis.toml` parsed by a small, flat, stdlib
parser (a `[section]` + `key = value` subset covering the few keys we need).
Recognised keys: `gate.enabled`, `gate.require_tests`, `autopilot.default`,
`audit.depth`. Env vars and the toggle file still win for ad-hoc overrides;
malformed files fall back to defaults rather than raising.

## Consequences
- Positive: versioned, reviewable per-repo policy; no new dependency; works on 3.8.
- Negative: the parser supports only the documented subset (not full TOML); adding
  richer config later may warrant a real TOML lib once 3.11 is the floor.

## Alternatives considered
`.praxis.json` (rejected — TOML is the ecosystem norm for tool config) and
requiring tomllib/3.11 (rejected — breaks the 3.8 floor and stdlib-only rule).
