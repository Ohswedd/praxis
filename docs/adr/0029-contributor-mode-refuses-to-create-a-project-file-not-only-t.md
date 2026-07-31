# 29. Contributor mode refuses to create a project file, not only to commit its own

- Status: accepted
- Date: 2026-07-31

## Context
ADR-0019 contained everything praxis authors: the exclude block, the staging guard, the index check. All three protect praxis's own artifacts (CLAUDE.local.md, .claude/.praxis/, settings.local.json). A CHANGELOG.md written into a project that never had one is not one of those. It is the project's own file: visible to git status, correctly staged by git add -A, and outside every layer. knowledge_path had always routed the helpers correctly, and nothing routed a direct write, so an unasked-for changelog was created and committed inside pull requests whose subject was a bug fix.

## Decision
The guard refuses to create, in contributor mode, a file praxis scaffolds for a repository it owns: CHANGELOG.md, CLAUDE.md, .praxis.toml, .mcp.json, .claude/settings.json, the /docs skeleton, and the contents of docs/adr/, docs/design/ and .claude/{commands,skills,agents}/. Only creation, and only where the project does not already have it. Refused at the file tool, at the shell, and at the index, since a rule that holds for Write and not for a shell redirect is not a rule, and since whatever wrote the file it becomes the project's only by being committed.

## Consequences
'Add a changelog to this project' is a legitimate request, so it gets an explicit switch (workspace.allow_project_artifacts, /praxis:config project-artifacts on, PRAXIS_PROJECT_ARTIFACTS=on) rather than a workaround. The list is a fixed set of names, so a project convention praxis does not know about is not protected by it; that is the correct scope, because the rule is about what praxis introduces, not about what a contributor may write. Editing a file the project already has is untouched, which is the behaviour a good pull request needs.
