---
description: Cut a release for this project — determine the SemVer bump, finalize the changelog, and prepare the tag.
argument-hint: "[explicit version, optional]"
---

Prepare a release for the current project:

1. Review the pending changes:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/changelog.py" show
   ```
2. Determine the next version (unless the user gave one in ${ARGUMENTS}):
   inspect commits since the last tag and the `[Unreleased]` entries, then apply
   SemVer per Conventional Commits — breaking change → MAJOR, `feat` → MINOR,
   `fix`/`perf` → PATCH. State your reasoning.
3. Finalize the changelog into a dated version section:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/changelog.py" release <version>
   ```
4. Bump any version files the project uses (package.json, pyproject.toml, etc.) to
   match, following the repo's existing convention.
5. Prepare (do not push without confirmation) the commit and tag:
   `chore(release): v<version>` and tag `v<version>`. Show the user the diff first.

Keep it consistent with the project's existing release process if one exists.
