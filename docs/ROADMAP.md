# Roadmap

Praxis v1.0 is feature-complete for its core mission. Post-1.0 candidates,
roughly in priority order:

- **Per-workspace gating.** Today the Stop gate keys on the whole-repo change
  signature; a future version can scope the quality report per changed package in
  a monorepo, allowing independent green states.
- **Native `prompt`/`agent` Stop hooks** as an optional stronger gate where the
  Claude Code version supports them (see ADR-0001), keeping the deterministic
  `command` gate as the default.
- **Coverage-aware regression.** Integrate test-coverage deltas so the
  regression-sentinel can flag untested changed lines precisely.
- **Config file** (`.praxis.toml`) for per-repo tuning of gate strictness,
  auto-pilot default, and audit depth, versioned in the repo.
- **Team profiles.** Shareable best-practice profiles (e.g. an org's security or
  API conventions) layered onto the catalog.
- **Metrics/telemetry (local, opt-in).** A per-repo log of audits and decisions
  for retrospective review — never phoning home.

Have a need? Record it as an issue; significant accepted directions become ADRs.
