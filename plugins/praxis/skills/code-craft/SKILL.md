---
name: code-craft
description: Professional code craftsmanship standards, especially how to write comments the right way. Use whenever writing or editing code, when adding comments or docstrings, during code review, or when the user asks for clean, production-quality, well-documented code. Covers comment discipline (explain why not what), docstrings/API docs, self-documenting naming, TODO hygiene, and removing debug/dead code. Apply these standards to every code change.
---

# Code Craft

Production code is read far more than it is written. These are the standards
praxis applies to every change so the result is clean, professional, and
maintainable — not just working.

## Comments — the core discipline

**Explain *why*, not *what*.** The code already says what it does; a good comment
says why it does it that way, what it protects against, or what non-obvious
constraint it satisfies.

- Bad: `// increment i by 1`
- Bad: `// loop over users`
- Good: `// Retry once: the upstream returns 503 during its rolling deploy.`
- Good: `// Must run before auth middleware — it populates the request context.`

**Rules:**
1. Do not comment the obvious. If the comment restates the code, delete it and
   improve the name instead.
2. Comment intent, invariants, edge-case reasoning, non-obvious performance or
   security decisions, and links to the spec/issue/doc that justifies a choice.
3. Keep comments next to the code they describe and update them in the same edit
   — a stale comment is worse than none.
4. Use the language's documentation convention for public APIs (docstrings,
   JSDoc/TSDoc, Javadoc, rustdoc, GoDoc): describe purpose, parameters, return,
   errors/exceptions, and side effects — not the line-by-line implementation.
5. Prefer self-documenting code over comments: a well-named function or variable
   removes the need for the comment entirely.
6. Write comments in the language and style already used in the file/project.

## TODO hygiene
- Do not leave bare `TODO`/`FIXME` in delivered code. If a follow-up is genuinely
  out of scope, surface it in the task report's "Out of scope / follow-ups"
  section so the user knows about it — do not bury it in a comment.
- Never ship `NotImplemented`, stub returns, `...`, `pass # implement`, or
  `throw "not implemented"` as a substitute for finishing in-scope work.

## Naming and structure
- Names reveal intent: a reader should infer purpose without reading the body.
- One responsibility per function; keep them short enough to hold in your head.
- Match the file's existing conventions (casing, ordering, error handling) before
  introducing a new style.
- No dead code, no commented-out blocks "just in case" — version control is the
  history. Remove them.

## Cleanliness before "done"
- Remove debug output (`console.log`, `println!`, `print`, `debugger`).
- Keep formatting consistent with the project's formatter (praxis auto-formats
  on save; still write it clean).
- Ensure error messages are accurate, actionable, and free of internal jargon
  that leaks implementation detail to end users.

## Tests as documentation
Well-named tests document intended behaviour. When you change behaviour, update
the tests to match the new intent so they remain a truthful spec.
