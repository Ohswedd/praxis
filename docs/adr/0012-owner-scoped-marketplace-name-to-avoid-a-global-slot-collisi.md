# 12. Owner-scoped marketplace name to avoid a global-slot collision

- Status: accepted
- Date: 2026-07-21

## Context
A Claude Code marketplace name is a single global slot per user: the docs state that adding a second marketplace with the same name replaces the first, silently. praxis published its marketplace as 'praxis' with a plugin also named 'praxis', making the install identifier 'praxis@praxis'. An unrelated project, xD4O/praxis, publishes a marketplace named 'praxis' containing a plugin named 'praxis' — a byte-identical identifier, pushed before praxis v1.4.0. Any user who added both would silently lose one, and 'praxis@praxis' would resolve to whichever was added last. 'praxis' is a crowded name in this ecosystem: at least six unrelated Claude Code projects use it.

## Decision
Rename the marketplace to 'ohswedd-praxis' and keep the plugin named 'praxis', so the identifier becomes 'praxis@ohswedd-praxis'. The marketplace name is the only globally-unique axis, so scoping it by owner is sufficient; a plugin name need only be unique within its marketplace, so the /praxis:* command prefix and the plugin identity are untouched. The install identifier is added to the stable public surface so it cannot drift again.

## Consequences
No user can silently replace this marketplace by installing an unrelated 'praxis'. Cost: a one-time manual migration — Claude Code auto-migrates plugin renames via the 'renames' field but has no equivalent for marketplace renames, so existing users must remove and re-add the marketplace. Done at the earliest possible moment (the day of first public release) when adoption is near zero. Rejected: renaming the plugin as well, which would break every /praxis:* command for no additional collision protection; and documenting the clash without fixing it, which leaves users' installs silently pointing at the wrong plugin.
