---
name: audit-evidence
description: "What an auditor is allowed to assert, and what it must cite. Preloaded into every praxis review auditor through the `skills` frontmatter field, so the rule exists once. Use whenever you are reviewing, auditing, or verifying a change and about to state a verdict: it defines the difference between a finding and a guess, requires every claim to name the file and line it came from, and requires an honest account of what could not be checked."
---

# Audit evidence

An auditor's output is believed. That is its entire value, and its entire
hazard: a verdict is acted on without being re-derived, so a claim that turns
out on a second look to be wrong costs more than the review saved. A review
that reports what it assumed is worse than no review at all.

## The rule

**Assert only what you read.** Every finding, and every PASS, comes from a
specific place in the code you actually opened.

- **Cite `file:line` for each finding**, and for the code that decided a PASS on
  a concern that mattered. "Handled upstream" is a claim; `src/api.py:88` is a
  citation.
- **Quote what the code says**, not what the name suggests it says. A function
  called `validate_input` is evidence of nothing.
- **Read the callers before judging a contract.** A signature change is safe or
  unsafe depending on who calls it, and that is a question with an answer, not
  an impression.
- **Never infer a file's contents from its path, its neighbours, or the diff.**
  If you have not opened it, you do not know what is in it.

Downstream, `report.py vertical` records each verdict with its citations and
**refuses any that does not resolve**: a file that does not exist, a line past
the end of one. An auditor that read the code can name it for free. So this is
not extra work, it is the work.

## Say what you could not check

An auditor's honest limits are part of its verdict, not a weakness in it:

- The scope you were given, and anything in it you did not reach (a file too
  large, a generated bundle, a path with no source in this repo).
- Questions that need a runtime, a credential, or a service you do not have. Say
  what would answer them, so someone with access can.
- A base commit you could not resolve. Report the gap; do not review the working
  tree alone and return PASS, which is how an audit of a committed branch comes
  back clean having read nothing.

`PASS` means "I examined this concern and found nothing". If you did not examine
it, the answer is not `PASS`, whatever the pressure to produce a clean row.

## Severity is a claim too

State impact in terms of what actually happens: the input, the state, and the
observable consequence. "Could be a security issue" is not a finding. "An empty
`X-Forwarded-For` makes `parse_ip()` at `net.py:40` raise, and the handler at
`net.py:71` converts that to a 500" is. If the realistic impact is smaller than
the worst case, say the realistic one.
