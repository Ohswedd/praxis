# 9. Escalating Stop-gate refusals over a single reminder

- Status: accepted
- Date: 2026-07-21

## Context
The per-change gate blocked the first stop attempt for a given change signature and allowed every subsequent one. In practice the audit was therefore optional: acknowledge the reminder, stop again, done. This was the mechanism behind the reported laziness — work handed back unaudited, with TODOs and 'for now' comments left in the diff as advisory text the model could step past.

## Decision
Refusals now escalate: attempt 1 names the workflow and why any existing report was rejected, attempt 2 names the concrete steps, attempt 3 tells Claude to execute rather than restate the plan. Escalation is keyed on the session's refusal **total**, not on the change signature — Claude normally edits between two Stops, which re-keys the signature, so a per-change counter would restart at 1 every turn and the refusal would never sharpen. Unfinished markers in the change's own diff — literal markers and deferral prose alike — lead the message at every attempt, cited with file:line.

When a cap is reached the gate spends one final turn on a disclosure — finish the audit, or tell the user plainly that the change is going out unaudited, which verticals are unverified, and what to check — and only releases the turn after. Releasing silently would skip the message that matters most. Two caps bound it: 3 refusals per change signature and 12 per session.

## Consequences
Finishing unaudited work now requires either completing the audit or explicitly telling the user it was skipped. Four layers guarantee the session can always finish: the two caps; per-session counter entries (a shared record would let two windows on one repo wipe each other's counters, so the caps would never be reached); failing open when the counter cannot be persisted (the caps depend on that write, so blocking while unable to record the block would trap the session forever); and the existing skip-gate / PRAXIS_GATE=off escapes. A tree that is byte-for-byte as the session found it is also never gated — a repo can be dirty from work that predates the session, and demanding an audit of someone else's diff, while attributing their unfinished markers to "this change", is worse than not gating. Cost: up to three extra turns on a change that resists auditing, and the escalation wording is declared internal so it can be tuned.
