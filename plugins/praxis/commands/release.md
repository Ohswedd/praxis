---
description: Cut a release for this project — determine the SemVer bump, finalize the changelog, and prepare the tag.
argument-hint: "[explicit version, optional]"
---

Prepare a release for the current project:

1. Review pending changes: `changelog.py show`.
2. Determine the next version (unless given in ${ARGUMENTS}) from commits since the
   last tag and the `[Unreleased]` entries, applying SemVer per Conventional
   Commits — breaking → MAJOR, `feat` → MINOR, `fix`/`perf` → PATCH. State your reasoning.
3. Finalize the changelog into a dated section: `changelog.py release <version>`.
4. Bump any version files the project uses (package.json, pyproject.toml, …) to match.
5. Prepare — don't push without confirmation — the commit `chore(release): v<version>`
   and tag `v<version>`. Show the diff first.

(Scripts live under `${CLAUDE_PLUGIN_ROOT}/scripts/`.) Match the project's existing
release process if one exists.
