# Contributing to Praxis

Thanks for improving Praxis. It holds itself to the standards it enforces.

## Ground rules
- **Everything stays stdlib-only** in `scripts/` (no third-party imports) so hooks
  run anywhere Python 3.8+ exists.
- **No regression.** Add/adjust tests for any behaviour you change; keep docs and
  the CHANGELOG current (Praxis dogfoods its own living-knowledge rules).
- **Determinism first.** Prefer deterministic enforcement (hooks, state files)
  over prompt-dependent behaviour.

## Before you open a PR
Run the same checks CI runs:

```bash
python plugins/praxis/scripts/selfcheck.py        # plugin integrity
python -m unittest discover -s tests -v           # test suite
python -m compileall plugins/praxis/scripts       # compiles
```

## Conventions
- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`…). The
  release workflow derives the next SemVer from these.
- Update `CHANGELOG.md` `[Unreleased]` for user-visible changes.
- Record significant design decisions as an ADR under `docs/adr/`.

## Project layout
See `docs/ARCHITECTURE.md` (design), `docs/FLOWS.md` (behaviour), and
`docs/KNOWLEDGE.md` (living-knowledge model).
