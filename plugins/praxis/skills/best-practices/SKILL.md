---
name: best-practices
description: Select and apply the software-engineering best-practices and guidelines relevant to the task at hand — and, in auto-pilot, resolve design decisions autonomously by picking the best-practice that fits. Use during planning, implementation, review, or any time an approach/design decision is being made: choosing an architecture, designing an API or schema, handling auth, structuring code, writing tests, addressing performance or security. Pulls from a curated catalog (SOLID, DDD, REST, ACID/CAP, OWASP, testing, clean code, performance, concurrency, functional) and applies only what the situation needs — never cargo-culting.
---

# Best Practices

praxis applies established engineering best-practices **based on the need** —
the minimal relevant set for the change at hand, matched to the repo's existing
conventions. It never applies everything blindly; KISS and YAGNI are themselves
part of the catalog.

## How to use it

1. **Identify the change's domains** from the spec/plan. A change usually touches
   two or three of: API design, data/persistence, domain modelling, security,
   concurrency, performance, architecture/structure, testing.
2. **Select the applicable families** using the table below. Reach for the full
   catalog only when you need the detail:
   read `${CLAUDE_PLUGIN_ROOT}/skills/best-practices/reference/catalog.md`.
3. **Apply the minimal relevant set**, consistent with existing repo patterns.
   Prefer the simplest solution that satisfies the principle (KISS/YAGNI). Do not
   introduce a pattern the problem doesn't warrant.
4. **Check against them in the audit** — the vertical auditors already map to
   families (adversarial→OWASP, perf→complexity/N+1, regression→contracts). Note
   which best-practices you applied in the report.

## Selection table (task signal → families to apply)

| The change… | Apply |
| --- | --- |
| adds/changes an HTTP endpoint | REST constraints, correct HTTP verbs, idempotency, safe methods, status codes, API versioning, rate limiting; OWASP (authz, input validation) |
| touches the database/schema | Normalisation (to the point that fits), transactions/ACID, indexing, N+1 avoidance, optimistic/pessimistic locking, migration safety |
| models a domain | DDD (bounded context, aggregate, value object, domain event), SoC, high cohesion/low coupling |
| structures code/classes | SOLID, composition over inheritance, DRY, Law of Demeter, appropriate GoF pattern, guard clauses/early return |
| handles auth / user input / secrets | OWASP Top 10 (injection, XSS, CSRF, SSRF), authN vs authZ, RBAC/ABAC, least privilege, password hashing+salting, TLS, input validation, CORS/CSP |
| is on a hot path / large data | Big-O awareness, caching/memoization, pagination, batching, lazy vs eager, connection pooling, avoid accidental quadratic |
| is concurrent/async | immutability, locks/mutex/semaphore correctness, avoid deadlock/race, idempotency, actor/producer-consumer where fitting |
| chooses an architecture | layered/hexagonal/clean/onion, modular monolith vs microservices (default to the simpler that fits), EDA/saga/outbox only when justified |
| distributed data consistency | CAP/PACELC trade-off stated explicitly, ACID vs BASE, eventual consistency, saga/outbox for cross-service writes |
| any code | Clean Code (meaningful names, small functions, no magic numbers, pure functions where possible, self-documenting), no code smells, Boy Scout Rule |
| any behaviour change | Testing: right level per the test pyramid (unit/integration/contract/E2E), TDD/BDD where it fits |

## Deciding autonomously (auto-pilot)

When resolving a design decision without asking the user, choose the option that
best satisfies, in order:
1. **Correctness & safety** — the option that is correct and fails safe.
2. **Applicable best-practice** — the family from the table above that governs
   this decision (e.g. "make the POST idempotent", "validate at the boundary").
3. **Repo consistency** — match how the codebase already does it.
4. **Simplicity** — the simplest option that satisfies 1–3 (KISS/YAGNI); avoid
   speculative generality.
5. **Reversibility** — prefer the choice that is cheapest to change later.

Record every non-trivial decision and its rationale so it appears in the report's
"Decisions taken autonomously" section. Deciding autonomously never means hiding
the decision.
