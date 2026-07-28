# 13. House rules enforced by hooks, not by doctrine

- Status: accepted
- Date: 2026-07-28

## Context
Two rules had been stated in the output style, the session directives, and the git-delivery skill for several versions, and were still broken regularly: no em dash in authored text, and no AI co-author or generated-by credit in the project's record. A prose instruction is easy to agree with and easy to forget at the moment it applies, and the two failures are asymmetric in cost. An em dash can be edited out later; a co-author trailer that reaches a commit is in the history for good and can only be removed by rewriting it.

## Decision
Enforce both mechanically. scan_style.py checks the whole change (unstaged diff, staged diff, untracked files) for em dashes, spaced en dashes, and AI attribution, and the Stop gate blocks on its findings alongside the placeholder scan. guard_paths.py refuses any git commit, git tag, gh pr create, gh release create or gh issue command carrying an attribution, so the credit is stopped at the command rather than after the fact. praxis:ack exempts a line, style.ban_em_dash and style.ban_ai_attribution disable each per repo, and selfcheck.py holds praxis's own content to both rules so the plugin cannot ship what it refuses elsewhere.

## Consequences
The rules now hold without depending on the model remembering them, and the failure is named with a file and a line instead of being noticed later by a reader. Cost: the plugin's own text had to be rewritten (roughly 700 em dashes across 82 files) and every new sentence has to reach for a colon, a comma, parentheses, or a full stop. The dash ban deliberately excludes the ASCII double hyphen, which in a repository is far more often a command-line separator than punctuation, and the unspaced en dash, which is correct in a numeric range.

## Alternatives considered
Leaving both to the doctrine, which is the status quo that produced the complaint. Blocking the em dash at PostToolUse, which cannot undo the write and would fire on every intermediate edit. Rewriting an attribution trailer out of the commit automatically, which silently edits the user's message and would surprise anyone who genuinely wanted it.
