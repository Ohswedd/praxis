# Modes, Effort & Autonomy

The contract is simple:

> **You write the prompt and choose the effort level. praxis handles the goals,
> workflows, and subagents automatically.**

No magic keywords, no deciding when to run `/goal`, no manual orchestration.

---

## What you control vs what praxis controls

| You | praxis (automatic) |
| --- | --- |
| Write the prompt in chat | Restructure it into a spec, plan, implement |
| Pick the effort (`high`, `ultracode`, …) | Set the repo up before working in it |
| Answer at genuine decision points | Work out whether the repo is yours, and write accordingly |
| | Dispatch the right skills & subagents |
| | Run QA / audit / regression / completeness |
| | Keep working until the task is done (the loop) |
| | Enforce no secrets, no destructive ops, no placeholders |

---

## Workspace mode: whose repository is this?

praxis writes real files into a project: an operating brief, settings, a `/docs`
tree, a changelog, ADRs. In your own repository that is the point. In a
repository you only contribute to, every one of them is a file the project never
asked for, sitting one `git add -A` away from a pull request that should have
contained a bug fix.

So praxis resolves the question first, and everything else follows from it.

| | `owner` | `contributor` |
| --- | --- | --- |
| Operating brief | `CLAUDE.md` (+ nested files) | `CLAUDE.local.md`, root only |
| Settings | `.claude/settings.json` | `.claude/settings.local.json` |
| praxis config | `.praxis.toml` (committed) | `.claude/.praxis/praxis.toml` (local) |
| `/docs`, `CHANGELOG.md`, `docs/adr/`, `docs/design/` | created and maintained | joined **only if the project already has them**, on its terms; otherwise kept under `.claude/.praxis/knowledge/` |
| Ignore rules | praxis's paths added to `.gitignore` | `.gitignore` untouched; praxis maintains `$GIT_COMMON_DIR/info/exclude` |
| Delivery | commit, PR, and merge per the auto-merge policy | commit and PR in the project's own style, then stop |

`CLAUDE.local.md` and `.claude/settings.local.json` are the locations Claude Code
documents for local, uncommitted configuration, so praxis reuses that contract
rather than inventing one.

### How the mode is decided

Most specific source wins, and the session audit always prints which one:

```
PRAXIS_MODE  →  .claude/.praxis/workspace  →  .praxis.toml [workspace] mode  →  detection
```

Detection is offline and asks one question: has the person configured to commit
here ever actually committed here? A repo with a remote, real history, and no
commit from your git address is somebody else's project that you cloned.
Everything uncertain (no remote, no `user.email`, barely any history, not a git
repo at all) resolves to `owner`, which is how praxis has always behaved. A git
call that fails or times out is *not* treated as uncertainty in your favour: it
is its own state, because reading a timeout as "no commits by you" would move
your own project into contributor mode.

**The verdict is pinned once detection reaches `contributor`**, in
`.claude/.praxis/workspace`. Without that, the ordinary contribution workflow
would undo the mode: you clone (contributor), praxis sets up locally, you fix the
bug and commit it, and on the next session your own address is in `git log`,
detection says `owner`, and praxis starts writing a `CLAUDE.md` and a `/docs`
tree into a repository that is not yours.

One asymmetry is a trust boundary rather than a preference: a **committed**
`.praxis.toml` belongs to the repository, and a repository does not get to tell
praxis that it is yours. It may declare `contributor`, which only ever withholds
writes; its `owner` is reported and then ignored in favour of detection. Local
sources (the environment variable, the toggle, the git-excluded config) are yours
and may say either.

```bash
/praxis:config mode contributor   # or owner, or auto
```

Switching also adds or removes praxis's block in `$GIT_COMMON_DIR/info/exclude`,
so the files match the verdict immediately.

### Three layers keep it out of their history

1. **Excluded.** The marked block in `$GIT_COMMON_DIR/info/exclude` (the file
   gitignore(5) reserves for per-clone patterns that are never shared) makes
   praxis's artifacts invisible to `git status`, unreachable by `git add -A`, and
   absent from praxis's own change detection. It is the *common* dir, not the
   per-worktree one, because that is the only one git reads.
2. **Refused.** The PreToolUse guard blocks any command that stages
   `CLAUDE.local.md`, `.claude/.praxis/` or `.claude/settings.local.json` **by
   name**, `-f` included, and refuses a forced stage-everything outright, since
   `--force` exists precisely to override the exclusion. It also refuses to write
   a praxis path into the project's `.gitignore` (through the file tools or a
   shell redirect), and on an unforced stage-everything it verifies the exclusion
   rather than assuming it, repairing it first and blocking only if the repair
   fails.
3. **Checked at the index.** A command string can always be written another way:
   `git -C .claude add -f settings.local.json`, a glob the shell expands after the
   hook has read the command, `git update-index --add`. So the last layer stops
   pattern-matching and asks git. A `commit`, `push` or `stash` is refused while a
   praxis artifact is in the index, however it got there. This is the layer that
   actually holds; the two above it are what make the failure legible early.

The session audit, the prompt router and every skill also state the mode and the
artifact map, so the correct path is normally used first rather than caught last.

### Caveats worth knowing

- **Worktrees.** `CLAUDE.local.md` is per-worktree, so each `git worktree` gets
  its own brief. The exclusion is shared (it lives in the common dir), so all of
  them are covered.
- **`--setting-sources`.** Running `claude --setting-sources user,project` skips
  `CLAUDE.local.md` and `.claude/settings.local.json` entirely. praxis still
  resolves the mode from disk and still protects the artifacts; they simply are
  not loaded into that session.
- **`/init`.** Claude Code's own `/init`, in its personal mode, writes
  `CLAUDE.local.md` into the project's `.gitignore`. That is the one unrequested
  `.gitignore` diff praxis cannot intercept, since it is not a tool call. Prefer
  `/praxis:bootstrap` in a repo that is not yours.

---

## Auto-bootstrap: set up first, then work

Any session that does real work in a repo praxis does not manage runs the
`bootstrap` skill first, in the same turn, and then carries straight on to the
request. It maps the repo read-only, writes what is absent, and reports it in a
line or two.

It asks about exactly one thing: reconciling a `CLAUDE.md` that praxis did not
author, which is the only lossy step and which goes through
`@praxis:claudemd-verifier`. In `contributor` mode even that cannot arise, since
the brief praxis owns is a separate, additive file.

Turn it off per repo with `/praxis:config bootstrap off`, `bootstrap.auto =
false`, or `PRAXIS_BOOTSTRAP=off`. Conversational prompts never trigger it:
answering a question does not require writing a brief first.

---

## Effort: the one knob you set

praxis is **effort-agnostic**: it behaves identically at any level. Effort only
changes how deeply Claude *executes* the same workflow: it never changes whether
the workflow, subagents, or gates run.

- `/effort high`: great everyday baseline.
- `/effort ultracode`: xhigh every turn **plus** Claude's own automatic parallel
  sub-agent orchestration. This composes with praxis: you get ultracode's
  parallelism *and* praxis's named vertical auditors. Nothing conflicts.
- `ultrathink` (a word in one prompt): max thinking for that single turn only,
  then it reverts. Use it for one unusually hard step.

Whatever you pick, praxis's auditors stay pinned to Opus / high effort in their
own frontmatter, so audits are always deep, even if your session is lower.

**So: set `high` or `ultracode` as your habit and forget about it.** Everything
else still works.

---

## Autonomy: praxis runs the loop, you don't run `/goal`

Continuation is handled deterministically inside praxis, driven by a task-state
file (`.claude/.praxis/task.json`), not by a prompt keyword and not by you
typing `/goal`.

How it works for a multi-step request:

1. At spec time Claude opens a task with acceptance criteria and a turn cap
   (`task_state.py open …`).
2. praxis's **Stop gate** keeps the session working turn after turn while the
   task is open: self-driving to the finish.
3. When Claude hits a **genuine decision point**, it marks the task `waiting` and
   stops to ask you. You answer; it resumes. (So you're never trapped, and you're
   never left out of real decisions.)
4. When **every criterion is met and the audit is green**, Claude marks it `done`
   and the loop releases.
5. A hard turn cap and the escapes (`skip-gate`, `PRAXIS_GATE=off`) mean the loop
   can never run away.

For a single small change there's no task loop: the per-change quality gate simply
refuses to let the turn end while the change is unreviewed. Either way you don't
manage it.

### Is `/goal` ever needed? No: it's optional.

The native `/goal` command still exists and is a fine power-tool for handing off a
very long, **unattended, cross-session** run (pair it with auto mode). But for
normal work you never need it: praxis's task loop already provides the
continuation. If you *do* use `/goal`, it coexists with praxis, both keep the
session going, and praxis feeds its audit results into the transcript the `/goal`
evaluator reads.

---

## auto mode (optional, for unattended runs)

If you want a truly hands-off run, enable **auto mode** (approves tool calls
without prompting). It's safe under praxis because the guards are deterministic
and independent of permission mode:

- secret-file access and destructive commands are still **denied** (PreToolUse);
- the quality/task gate still runs every turn;
- the placeholder scan still catches unfinished work.

Still include a turn cap in the task and be ready to `Ctrl+C`.

---

## Delivery: human-in-the-loop by default

Finishing the code and delivering it are separate steps. Praxis never pushes on
every edit; when a change is complete and audited, `/praxis:ship` turns it into a
Conventional Commit and a pull request, and stops there for you to review and
merge. Merging is the one irreversible step praxis leaves to you.

Opt into autonomy with `git.auto_merge` (`.praxis.toml`), `PRAXIS_AUTO_MERGE=on`,
or `/praxis:config auto-merge on`: praxis then reviews and merges its own PR, but
only on a green audit and passing checks, and never by force-pushing the base
branch.

Whichever way you set it, praxis resolves the policy at the moment it delivers
rather than repeating what a document says: the session audit and
`/praxis:config` both print the value in force and where it came from. See
[DELIVERY.md](DELIVERY.md).

In `contributor` mode auto-merge does not apply at all. Merging somebody else's
project is not a decision praxis gets to make, so it opens the pull request in
the project's own style and stops.

---

## Determinism summary

| Concern | Mechanism | Deterministic? |
| --- | --- | --- |
| Does the workflow engage? | always-on directive (SessionStart) + output style + per-prompt router (UserPromptSubmit); enforced by the change/task gate | Yes: the router names the skills each request needs, and the gate is keyed on real file changes |
| Is the repo set up before work starts? | `repo_state` at SessionStart and on every actionable prompt | Yes (the instruction); the setup itself is Claude running the skill |
| Does praxis leave a trace in a repo that is not yours? | `$GIT_COMMON_DIR/info/exclude`, the staging guard, and an index check before `commit`/`push`/`stash` | Yes: whatever staged it, the command that would publish it is refused |
| Keep working until done | Stop gate + `task.json` (turn cap, `waiting`, `done`) | Yes |
| No secrets / destructive ops | PreToolUse guard (holds even in auto mode) | Yes |
| No placeholders / stubs / deferral | `scan_placeholders.py` over the branch's commits, the working tree and every untracked file (literal markers + deferral prose in comments) | Yes |
| No em dash, no AI attribution | `scan_style.py` at the Stop gate; `guard_paths.py` at the commit/PR command | Yes |
| UI changes get the UI audits | resolved from the changed file list, not from the request's wording | Yes |
| Docs match the live configuration | `drift.py` at SessionStart, in the doctor, and in `/praxis:docs` | Yes (detection) |
| Actually run the audit | Stop gate escalates 3× with increasingly specific instructions before releasing | Yes |
| Tests really passed | `report.py` executes the test command itself; unverified evidence is rejected | Yes |
| Depth of reasoning | your `/effort` setting | You choose |

The prompt router reads your request to decide **which skills to name**, but it
can only ever add context: it never blocks, never rewrites your prompt, and is
not what makes the workflow apply. That guarantee still comes from the
always-injected directive and the change-based gates, which are keyed on real
file changes rather than on your wording. So a request the router misreads still
gets the full pipeline; the router only means you don't have to rely on phrasing
for the *right* skills to engage.

---

## Auto-pilot: zero questions

Turn it on and praxis asks you **nothing** about design or approach. It does its
own QA and resolves each decision by the best-practice that fits, then records
every non-trivial choice under **"Decisions taken autonomously"** in the report,
so nothing is hidden; you review after, not during.

```
/praxis:config autopilot on      # this repo
/praxis:config autopilot off
```

Or pin it globally by exporting `PRAXIS_AUTOPILOT=on` in your shell profile.

The decision procedure (from the `best-practices` skill), in priority order:
correctness & safety → the applicable best-practice → repo consistency →
simplicity (KISS/YAGNI) → reversibility.

Safety is unchanged in auto-pilot: the PreToolUse guard still blocks secrets and
destructive commands, and the quality/task gate still runs. The only thing praxis
will ever stop for is a **hard external blocker it cannot resolve itself** (e.g. a
credential you must provide), and even then it states the assumption it would use.

## Best-practices: applied by need

praxis follows established engineering best-practices, choosing the **minimal
relevant set** for the change's domains rather than applying everything. The
`best-practices` skill has a selection table (HTTP endpoint → REST/idempotency/
OWASP; DB change → transactions/indexing/N+1; domain model → DDD; hot path →
Big-O/caching; …) and a full catalog it consults on demand. It respects KISS and
YAGNI, so it won't over-engineer, and it notes which practices it applied in the
report.

## The whole workflow, from your side

1. Set your effort once (`/effort high` or `/effort ultracode`).
2. (Optional) `/praxis:config autopilot on`, or set `PRAXIS_AUTOPILOT=on` once.
3. Type the idea: *"migra l'intero layer di pagamento a Stripe."*
4. In auto-pilot: just read the final report (with the decisions it made). Without
   it: answer only genuine questions.

That's it.
