# 17. Self-check is scoped to what is actually present

- Status: accepted
- Date: 2026-07-28

## Context
selfcheck.py computed the repo root as two levels above the plugin directory and unconditionally demanded a marketplace manifest there. That holds in the source checkout and never holds for an installed plugin, whose cache contains the plugin directory alone. /praxis:doctor runs selfcheck from the install path, so every healthy installation had been reporting 'plugin integrity: PROBLEM' since the check was introduced. The same conflation silently skipped the repo prose checks, and the summary line still reported a check count as though the coverage were complete. A permanent false alarm is worse than no check: it teaches the reader to ignore the one line that matters when something really is broken, and an unqualified OK claims coverage that was never attempted.

## Decision
Split the checks into two scopes. Plugin scope covers everything that travels inside the installed plugin: manifest, hooks, frontmatter, compilation, internal command and script references, and the house style of the shipped text and templates. Repo scope adds the enclosing marketplace, its version agreement and source paths, and the repo prose. Scope is detected from whether a marketplace manifest that actually publishes this plugin sits above it, matched by resolving each entry's source against the plugin directory, so a plugin unpacked inside an unrelated repository is never cross-checked against that repository's marketplace. A manifest that exists but does not parse selects repo scope and fails, rather than falling back to the smaller scope and hiding the error. Both selfcheck and doctor state the scope they covered. --require-repo turns detection into an assertion and is what make check, CI and CONTRIBUTING use.

## Consequences
An installed plugin now passes its own integrity check, and /praxis:doctor answers the question a user actually has. CI cannot silently weaken: a checkout whose marketplace is missing, unreadable, or no longer lists the plugin fails on the assertion instead of quietly reporting OK for a smaller scope. Coverage is stated rather than implied, which is the same rule the repo scanner already follows. Cost: one more flag on a stable CLI, and two code paths to keep in step, covered by tests that exercise both scopes plus the unrelated-marketplace, corrupt-manifest and version-mismatch cases.

## Alternatives considered
Skipping the marketplace check whenever the file is absent, which was the small fix. It removes the false alarm but leaves CI able to pass on a tree that lost its marketplace, and leaves the repo prose silently unchecked with no signal. Making doctor ignore selfcheck's exit code, which hides real integrity failures too. Shipping the marketplace manifest inside the plugin so the check always applies, which duplicates a file the plugin does not own and would go stale.
