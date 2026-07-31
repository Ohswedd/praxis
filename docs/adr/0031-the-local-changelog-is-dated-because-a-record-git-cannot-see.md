# 31. The local changelog is dated, because a record git cannot see needs its own evidence

- Status: accepted
- Date: 2026-07-31

## Context
In contributor mode with no project CHANGELOG.md, praxis keeps the record under .claude/.praxis/knowledge/, which is git-excluded and appears in no diff. knowledge_check could therefore only ask whether an [Unreleased] entry existed, which an entry written three sessions ago satisfies, so a contributor could pass the living-knowledge gate without recording today's work. The repo-changelog path has no such gap: git answers it exactly. Shipped as debt entry 2 in v3.2.0 with its interest and principal written down.

## Decision
changelog.py records every entry it writes into .claude/.praxis/changelog_log.json with the path, type, message, timestamp, branch and head, bounded to the last 100 writes. knowledge_check's local-knowledge branch requires a recorded write at or after common.change_started_at, which is the base commit's committer time on a branch and HEAD's off one. The two failure modes report differently, because nothing-written and belongs-to-earlier-work need different fixes. A state-write failure is surfaced by changelog.py as a warning rather than swallowed: the entry is on disk either way, and a user who is not told the record was lost cannot act on the refusal that follows.

## Consequences
A new state file, listed in docs/STABILITY.md. A contributor whose local record predates this branch is asked to write the entry again, which is correct rather than merely stricter. A write is also matched on the commit it was made at, so a sibling branch cut from the same base does not inherit another branch's entry unless that entry predates the branch's first commit, which is recorded as debt entry 3 along with the change-signature half of the principal that went unimplemented. Three bounded residues, all documented: a commit date has one-second resolution while a write is stamped to the microsecond, so an entry written moments before its commit counts as part of it, which is the right direction to be wrong in; a rebase moves the base forward and can age out an earlier entry, where writing it again is what the branch's history now says happened; and a base commit dated after this machine's clock dates nothing, because the base of a repository we do not own is stamped on somebody else's machine and any positive skew would otherwise refuse every entry the session writes. Owner mode and contributor repos that have their own changelog are untouched, since git already answers those exactly.
