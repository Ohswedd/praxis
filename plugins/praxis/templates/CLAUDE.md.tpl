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
- <datastores / external services / APIs, configured via which env vars — no secrets here>
