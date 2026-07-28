<!-- praxis:managed -->
# Project: <NAME>

<One-to-three sentence description of what this project is and does.>

## Commands
- Build:  <exact build command>
- Test:   <exact test command>
- Run:    <exact run/dev command>
- Lint:   <exact lint command>
- Format: <exact format command>

## Architecture
<3–6 lines: the main components and how they relate. Link nested CLAUDE.md files
for subsystems instead of duplicating their detail here.>

## Conventions
- <language/version, strict settings>
- <naming / module layout rules>
- <error-handling approach>
- Commit format: <e.g. Conventional Commits: type(scope): summary>

## Do
- Follow the authoritative docs and existing repo patterns before writing new code.
- Reuse existing utilities; do not reinvent or duplicate.
- Run the praxis quality rubric (/praxis:audit) after non-trivial changes.

## Don't
- <project-specific footguns: generated files, non-obvious invariants, etc.>
- Commit secrets or edit .env / credential files.

## Integration points
- <datastores / external services / APIs, configured via which env vars, no secrets here>

<!--
Writing note for whoever maintains this file, praxis included.

State behaviour that a setting controls *as* conditional, and name the setting:
"with auto-merge off, which is the default, praxis stops at the PR" survives the
toggle being flipped, while "praxis never merges" becomes a confident lie the
moment someone turns it on, and every later session repeats it.

`/praxis:doctor` prints the settings actually in force and reports any line here
that contradicts them. Prefer pointing at that command over restating a value.
-->

