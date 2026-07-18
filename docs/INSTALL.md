# Install

## Requirements
- Claude Code **v2.1.139+** (`claude --version`); the auto-enabled output style
  relies on the current output-style mechanism (the old `/output-style` command
  was removed in v2.1.91).
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

## The quality mindset (automatic)

The `praxis-quality` output style activates automatically when the plugin is
enabled (via its `force-for-plugin` frontmatter), so the doctrine is on from the
first turn — no command to run. It sets `keep-coding-instructions`, so it layers
on top of Claude Code's built-in engineering instructions rather than replacing
them, and it overrides your `outputStyle` while Praxis is enabled — disable the
plugin to opt out.

> The standalone `/output-style` command was removed in Claude Code v2.1.91.
> Output styles are now managed through `/config` (Output style) or the
> `outputStyle` key in a settings file; `force-for-plugin` makes the manual step
> unnecessary here.

## Verify

```
/praxis:doctor
```

You should see the plugin version and a health report. Open a session in any
repo and the `SessionStart` audit will classify it and print standing directives.
