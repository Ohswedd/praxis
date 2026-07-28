---
name: prompt-architect
description: Restructure a vague or terse request into an explicit, actionable engineering spec before any work begins. Use at the start of any implementation task, whenever a prompt is ambiguous, underspecified, or high-level (e.g. "fix this", "make it better", "integrate X"), or when the user asks you to turn an idea into a proper task. Produces goal, scope, non-goals, acceptance criteria, assumptions, and open questions so nothing is misunderstood or silently narrowed.
---

# Prompt Architect

Most defects start as misunderstood requests. This skill converts a loose prompt
into a spec precise enough to execute against and to verify against, without
inventing scope the user did not ask for.

## Method

1. **Extract the true intent.** State, in one or two sentences, the outcome the
   user actually wants, not a literal restatement of their words. If their
   phrasing and their apparent goal diverge, note both.

2. **Draw the scope boundary.**
   - *In scope*: the concrete deliverables that satisfy the intent.
   - *Out of scope / non-goals*: adjacent things you will NOT do. This is the most
     important part: it prevents both over-reach and silent under-delivery. If
     you must exclude something the user might expect, say so explicitly.

3. **Write acceptance criteria.** Testable, observable conditions for "done"
   (e.g. "endpoint returns 400 on missing field", "existing X tests still pass").
   These become the audit checklist later.

4. **Separate facts from assumptions.** List every assumption you are making to
   fill a gap the user left. Assumptions are allowed; hiding them is not.

5. **Surface open questions.** Only genuine blockers or true ambiguities. For each:
   - if it blocks correct work → ask it now, concisely;
   - if not → state the assumption you'll proceed under and continue.
   Prefer proceeding under a stated assumption over stalling on trivia.

6. **Right-size the output.** For a big or ambiguous task, present the full spec
   and confirm before proceeding. For a small, unambiguous task, compress it to a
   sentence or two and move on: do not bureaucratise trivial work.

7. **Split a large request into an ordered plan.** One prompt is very often
   several tasks. "Handle these four improvements and ship it" is not one unit of
   work, and treating it as one produces a single opaque commit, a pull request
   nobody can review, and a report that cannot say which part is finished.

   Decompose whenever the request has more than one deliverable, touches more
   than one subsystem, or would take more than a handful of steps. Each subtask
   must be:
   - **independently completable**, and ideally independently correct: something
     you could stop after and still have left the repo in a working state;
   - **one commit's worth of work**, because that is exactly what it becomes;
   - **ordered by dependency**, so nothing is started before what it rests on.

   Where the parts genuinely depend on each other, say so in the plan rather than
   pretending they are parallel. And where one improvement *forces* another (a
   change that would break something unless a second change lands with it), that
   is not two subtasks, it is one: splitting it produces a commit that does not
   work on its own.

   Record the plan so the loop and the gate can drive it:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" open "<macro title>" \
     --criteria "..." --subtasks "first" "second" "third" --max <N>
   ```
   The subtasks are the plan; the criteria remain the definition of done for the
   whole task. A task cannot close while a subtask is unfinished, so the plan is
   a commitment rather than a note.

## Auto-pilot: decide, don't ask
When auto-pilot is on (`config.py status` / env `PRAXIS_AUTOPILOT`), do **not**
emit questions to the user. Convert every open question into an **autonomous
decision**: resolve it with the `best-practices` decision procedure
(correctness/safety → applicable best-practice → repo consistency → simplicity →
reversibility), then record it under "Decisions taken autonomously" with a
one-line rationale. Proceed without pausing. The only permitted stop is an
external blocker you genuinely cannot resolve yourself (e.g. a credential the user
must provide), and even then, state the assumption you'd use if told to continue.

## Output shape

```
**Goal:** ...
**In scope:** ...
**Out of scope:** ...
**Acceptance criteria:**
- ...
**Assumptions:** ...
**Open questions:** ... (or "none: proceeding")
**Plan:** (when the request is more than one deliverable)
1. ... 2. ... 3. ...   one commit each, in dependency order
```

## Anti-patterns to avoid
- Silently shrinking scope to make the task easier.
- Inflating scope with work the user didn't ask for.
- Turning a five-second request into a questionnaire.
- Accepting a large request as one undifferentiated task. If you cannot name the
  steps, you do not yet understand the request well enough to start it.
- Splitting for the sake of it. Subtasks that cannot stand alone produce commits
  that do not build, which is worse than one honest commit.
- Proceeding on a hidden assumption instead of stating it.
