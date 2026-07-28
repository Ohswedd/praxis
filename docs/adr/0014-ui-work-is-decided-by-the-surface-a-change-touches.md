# 14. UI work is decided by the surface a change touches

- Status: accepted
- Date: 2026-07-28

## Context
The front-end pipeline and the two UI auditors ran when the request sounded like design work. Real requests do not announce themselves: 'fix the checkout bug', 'the empty state looks wrong', and 'update Header.tsx' are all interface work phrased as anything but. The result was UI shipped without a brief, a story, or a design system, and audited on the seven code verticals only, which is precisely the generic output the craft reference exists to prevent.

## Decision
Resolve the question from the changed file list rather than from the prompt. common.is_ui_path classifies markup, style, component, token and theme files plus docs/design/, common.ui_files_in_change applies it to the whole change, and both report.py and quality_gate.py refuse a green report for such a change without accessibility=pass and design-consistency=pass. The prompt router keeps its role as the early signal and gains a file-extension match and a much wider interface vocabulary, but enforcement no longer depends on it.

## Consequences
A UI change cannot be audited as if it were server code, whatever it was called, and the gate names the file that made the requirement apply so it never reads as arbitrary. Cost: a change that touches a stylesheet for a non-visual reason still owes two auditor runs, which gate.require_ui_verticals disables per repo. Deciding late is expensive because the report is keyed to the change signature, so the skills now say so explicitly.

## Alternatives considered
Classifying intent from the prompt alone, which is what failed. Asking the user whether a change counts as UI work, which pushes a judgement call back onto them every time. Running the two auditors on every change, which wastes them on pure backend work and trains the reader to ignore their verdicts.
