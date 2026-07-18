# Praxis per-repo configuration (optional). Commit this to version it with the repo.
# All keys are optional; shown values are the defaults.

[gate]
# Master switch for the Stop quality/task gate.
enabled = true
# Require passing test evidence in the green report when the repo has a test command.
require_tests = true

[autopilot]
# Start sessions in auto-pilot (no questions; decide by best-practice, log decisions).
default = false

[audit]
# Informational depth hint for the auditors: "high" | "max".
depth = "high"
