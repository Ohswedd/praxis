---
name: runtime-verification
description: "Prove a change works by running the product, not only its tests. Use whenever a change touches a user-facing surface (a page, a screen, a route, a CLI command, a job) and whenever the unit suite passing would not actually tell you the thing works: after implementing a feature, before recording the quality report, when the user asks you to check, try, or confirm something works, or when the Stop gate reports a missing runtime check. Covers choosing the right harness for the project (Playwright, Cypress, Puppeteer, an HTTP probe, the CLI itself), driving a real browser through the Chrome tools when one is available, adding a harness to a project that has none, and recording the result as evidence rather than as a claim."
---

# Runtime Verification

A green unit suite proves that a function returns what its test expects. It does
not prove that the page renders, the route answers, the button submits, the
migration applies, or the command exits zero. That gap is where a change passes
every check and is still broken for the person who has to use it, and it is why
"the tests pass" is the single most common true-but-useless sentence in a
handover.

**The rule: if a change alters something a person or another system interacts
with, run that thing and observe the result before you call the work done.**

## Step 1: Decide what "running it" means here

Derive it from the project, never from habit. The question is always the same:
what is the smallest real execution that would fail if this change were wrong?

| The change touches | Run |
| --- | --- |
| A page, component, or style | The app in a browser, on the route that renders it |
| An HTTP route or API | A request against a locally running server (`curl`, `httpie`, the project's client) |
| A CLI command or flag | The command itself, including its failure path and its `--help` |
| A background job, queue, or cron | The job, against a real (local) queue or a fake with the same contract |
| A migration or schema change | The migration forward, then backward, against a scratch database |
| A build, bundler, or CI change | The build, and check the artifact it produced |
| A library with no runnable surface | The test suite is the runtime check; say so rather than inventing one |

## Step 2: Use the harness the project already has

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status` reports the
end-to-end harness praxis detected, and `report.py` runs it for you:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" record \
  --runtime "npm run e2e" --runtime-timeout 900 --verticals "..."
```

`report.py` executes the command and records the real exit code, exactly as it
does for the test suite. When the change touches user-facing files and the
project has a harness, the run is required and the report is not green without
it (`gate.require_runtime`).

Prefer the project's own harness over anything you would introduce. It already
encodes how this app starts, what it needs, and what "working" means for it.
Reinventing that in an ad-hoc script is the wheel this pipeline exists to
refuse.

## Step 3: Drive a browser when the surface is visual

Two routes, in order of preference.

**The Chrome tools, when they are available in this session** (`claude-in-chrome`
tooling: `tabs_context_mcp`, `navigate`, `computer`, `read_page`,
`read_console_messages`). They drive the user's real browser, need no dependency
added to the project, and let you *look* at the result:

1. Start the app the way the project documents it (`npm run dev`, `make serve`).
   Run it in the background and wait for the port to answer; do not assume it
   started.
2. Open the route the change affects in a new tab.
3. Read the page, take the screenshot, and check the console for errors the
   change introduced. A page that renders while throwing is not working.
4. Exercise the actual interaction: submit the form, follow the flow, resize to
   a narrow viewport. Static rendering is a third of what you changed.
5. Check the states you built: loading, empty, error. If you cannot reach one
   from the UI, drive it directly (a fixture, a forced error, a throttled
   network) rather than declaring it fine.

**Playwright, when the session has no browser tooling or the check must be
repeatable.** Playwright is the default choice for a project adding its first
browser harness: it ships its own browsers, runs headless without configuration,
and covers Chromium, Firefox and WebKit from one API. Cypress is the right
answer when the project already uses it. Puppeteer is Chromium-only and is
appropriate when the task genuinely is Chrome automation (scraping, PDF
generation) rather than testing.

## Step 4: Adding a harness to a project that has none

A test dependency is still a dependency, and it is the project's to accept.

- **In a repository you own**: propose it, install it, and commit a real test
  rather than a scaffold. `npm init playwright@latest` writes a config, a
  workflow and an example; keep the config, delete the example, and write the
  test that covers the flow this change touched. Add the script to
  `package.json` under a name praxis detects (`test:e2e` or `e2e`) so every
  later change is verified without anyone remembering to.
- **In a repository you only contribute to**: do not add it. Verify by hand
  through the Chrome tools or a local run, state in the pull request exactly what
  you exercised and how, and, if the project would benefit from a harness, say
  so as a suggestion rather than as a commit.
- **Either way, ask before adding a dependency the project did not have**, in
  auto-pilot as well: a new dev dependency changes what every contributor
  installs and what CI runs, which is the user's call, not a detail.

## Step 5: Record what you ran, exactly

This is where runtime verification is usually lost. The run happened, the result
was fine, and the report says "verified manually", which is indistinguishable
from nothing.

- If a command ran, let `report.py` run it so its exit code is measured rather
  than reported.
- If you drove the browser yourself, write down in the report: the URL, the
  interactions, what you observed, and what you could *not* reach. Cite it as
  evidence on the vertical it supports:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" vertical edge-case \
    --verdict pass \
    --summary "Drove /checkout in Chrome: empty cart, one item, declined card. Error state renders and keeps the form state." \
    --evidence "src/routes/checkout.tsx:44,src/components/CartEmpty.tsx"
  ```

- If you could not run it at all (no environment, a missing credential, a
  service you cannot reach), say that plainly in the report under what was not
  verified. An honest gap is a finding the user can act on. A vague claim is a
  defect they will meet later, and praxis treats a stated "verified" that was
  not verified as the most serious kind of failure in this pipeline.

## What this is not

Not a replacement for tests. A runtime check is a single observation at one
moment; the test suite is what keeps the behaviour true tomorrow. A change that
was verified by hand and has no test covering it is incomplete: write the test,
then run the thing.
