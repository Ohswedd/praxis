# Security Policy

## Threat model & posture

Praxis is a Claude Code plugin: installing it means its hooks and scripts run on
your machine during sessions. It is designed to be safe by construction.

- **Read-only auditors.** The twelve vertical/analysis subagents are restricted to
  `Read, Grep, Glob` (the doc-reference-finder additionally to web search). An
  audit can never modify code.
- **Fail-open hooks.** Every hook script catches its own exceptions and exits 0 on
  error, so a bug in Praxis can never break or hijack your session.
- **No secrets shipped, no live services.** Praxis ships no credentials and no
  active `.mcp.json`; MCP wiring is a template that references environment
  variables only.
- **Defensive guards (deterministic).** The PreToolUse guard denies access to
  sensitive files (`.env`, private keys, credentials) and destructive/exfiltration
  commands (`rm -rf` on broad paths, force-push to protected branches,
  `curl | sh`, piping env/secrets to the network, writing to `authorized_keys` or
  `/etc`). These denials hold even under `--dangerously-skip-permissions` and in
  auto mode, because a PreToolUse deny precedes the permission check.
- **Stdlib only.** Scripts use the Python standard library — no third-party
  packages are installed or imported, reducing supply-chain surface.
- **Local state only.** Praxis writes to `.claude/.praxis/` in your repo (git-
  ignored) and never phones home.

## Known limitations (by design)

- The Stop-gate green report is **trust-based**: it verifies the report exists and
  matches the change signature, not that the audit reasoning was genuine. The
  deterministic scans (placeholders, secrets, destructive commands) are the hard
  backstops. See `docs/adr/0001-*`.
- The destructive-command guard is heuristic; it targets high-signal patterns and
  will not catch every conceivable dangerous command. Keep normal review habits.

## Reporting a vulnerability

Open a private security advisory on the repository, or email the maintainers.
Please do not file public issues for security reports.

## Privacy

Praxis collects and transmits nothing; all processing is local. See
[`PRIVACY.md`](PRIVACY.md) for the full data-flow statement, including the
one place information leaves your machine — Claude Code's own conversation
channel to Anthropic.
