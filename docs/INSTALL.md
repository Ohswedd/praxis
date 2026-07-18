# Install

## Requirements
- Claude Code (a recent version; `claude --version`).
- Python 3.8+ available as `python3` on `PATH` (hooks are stdlib-only — no pip
  installs). On Windows, ensure `python3` resolves, or adjust the hook commands
  in `hooks/hooks.json` to `python`.

## Option A — from GitHub (recommended, supports auto-update)

1. Push this repository to GitHub (public, or private if your org allows).
2. Register the marketplace and install:

   ```
   /plugin marketplace add Ohswedd/praxis
   /plugin install praxis@praxis
   ```

3. Enable auto-update by adding the marketplace to your settings
   (`~/.claude/settings.json` or `.claude/settings.json`):

   ```json
   {
     "extraKnownMarketplaces": {
       "praxis": {
         "source": { "source": "github", "repo": "Ohswedd/praxis" },
         "autoUpdate": true
       }
     }
   }
   ```

## Option B — local (fastest iteration)

From the repo root:

```
/plugin marketplace add ./          # registers the marketplace in this folder
/plugin install praxis@praxis
```

Or load without installing, for a single session:

```
claude --plugin-dir ./plugins/praxis
```

After editing a skill's SKILL.md it applies immediately; after editing hooks,
agents, MCP, or output styles run `/reload-plugins` or restart the session.

## Turn on the mindset

```
/output-style praxis-quality
```

## Verify

```
/praxis:doctor
```

You should see the plugin version and a health report. Open a session in any
repo and the `SessionStart` audit will classify it and print standing directives.
