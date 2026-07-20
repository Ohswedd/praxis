# Best-Practices Catalog

Reference for the `best-practices` skill. Apply the **minimal relevant set** for
the change — matched to existing repo conventions. Do not apply everything; KISS,
YAGNI and "avoid speculative generality" govern this catalog too.

Each entry: the concept, and *when to reach for it*.

---

## 1. Design principles
- **SOLID** — SRP, OCP, LSP, ISP, DIP. Reach for when structuring classes/modules;
  the backbone of maintainable OOP.
- **DRY** — remove duplicated knowledge (not just duplicated text). When you see
  the same decision expressed twice.
- **KISS** — the simplest thing that works. Always; it caps the others.
- **YAGNI** — don't build for imagined future needs. When tempted to generalise.
- **POLA / Principle of Least Astonishment** — behaviour should not surprise.
  Naming, API shape, defaults.
- **Principle of Least Privilege** — grant the minimum access. Security-sensitive
  code, tokens, DB users.
- **Separation of Concerns**, **High Cohesion / Low Coupling**, **Information
  Hiding** — module boundaries and dependencies.
- **Law of Demeter** — talk to immediate collaborators only. Reduces coupling.
- **Composition over Inheritance** — prefer has-a to is-a when reuse is the goal.
- **Convention over Configuration** — sensible defaults over ceremony.
- **Fail Fast**, **Defensive Programming**, **Design by Contract** — validate
  inputs/invariants early at trust boundaries.
- **CQS / CQRS** — separate reads from writes; CQRS only when the complexity is
  justified (not by default).
- **Don't Make Me Think** — obvious interfaces and code.

## 2. Software architecture
- **Layered / Clean / Hexagonal (Ports & Adapters) / Onion** — isolate domain
  from I/O. Reach for when the app has real business logic worth protecting.
- **Modular Monolith** — default for most systems; get boundaries right before
  considering microservices.
- **Microservices** — only when org/scale/deploy independence justifies the
  distributed-systems cost.
- **Event-Driven Architecture, SOA, Serverless, Client-Server, P2P** — pick per
  coupling/scaling needs.
- **MVC / MVP / MVVM, Flux/Redux** — UI structure.
- **BFF, API Gateway** — when multiple clients need tailored aggregation.

## 3. OOP & GoF patterns
- Core: Encapsulation, Abstraction, Inheritance, Polymorphism, Composition,
  Delegation, DI, IoC, Immutability, Value Objects, Entities, Aggregates.
- **Creational:** Factory, Builder, Singleton (sparingly), Prototype.
- **Structural:** Adapter, Facade, Decorator, Proxy, Bridge, Composite, Flyweight.
- **Behavioural:** Strategy, Observer, Command, State, Chain of Responsibility,
  Mediator, Template Method, Visitor, Iterator, Memento, Interpreter.
- Reach for a pattern to *name a solution the problem already has* — never to
  decorate simple code.

## 4. Domain-Driven Design
Ubiquitous Language, Bounded Context, Aggregate + Aggregate Root, Entity, Value
Object, Domain Event, Domain Service, Repository, Factory, Anti-Corruption Layer,
Context Mapping, Shared Kernel. Reach for when the domain is complex enough that
the model is the hard part; overkill for CRUD utilities.

## 5. Database
- **Normal Forms (1NF→BCNF, 4NF/5NF)** — normalise to remove anomalies; denormalise
  deliberately for read performance.
- **CAP / PACELC** — state the trade-off explicitly for distributed data.
- **Consistency options:** eventual consistency, read replica, sharding,
  partitioning, replication.
- **Indexing:** covering/composite/clustered/non-clustered; match to query shape.
- **Materialized View, Stored Procedure, Trigger** — use judiciously.
- **Concurrency:** optimistic vs pessimistic locking, MVCC, WAL. Choose per
  contention profile.

## 6. REST & API
- **REST constraints:** client-server, stateless, cacheable, uniform interface,
  layered, code-on-demand.
- **Richardson Maturity Model, HATEOAS** — level of RESTfulness.
- **HTTP verbs** GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD; **safe** vs **idempotent**
  semantics; correct status codes. Idempotency keys for unsafe retried operations.
- **Contracts:** OpenAPI/Swagger; GraphQL / gRPC / WebSocket / SSE / RPC per need.
- **Auth:** OAuth2, OpenID Connect, JWT.
- **Resilience/limits:** API versioning, rate limiting, circuit breaker, retry with
  backoff.

## 7. Cloud & distributed systems
Twelve-Factor App; horizontal vs vertical scaling; load balancer, reverse proxy,
CDN; service discovery; distributed tracing & observability; chaos engineering;
deploys (blue-green, canary, rolling); feature flags; patterns (sidecar, saga,
outbox, bulkhead, strangler fig). Reach for distributed patterns only when
actually distributed.

## 8. DevOps
CI, CD (delivery vs deployment), GitOps, IaC, immutable infrastructure; Docker,
Kubernetes, Helm, Terraform, Ansible; CI runners (GitHub Actions, GitLab CI,
Jenkins). Automate the path to production; keep it reproducible.

## 9. Git
Commit/branch/merge/rebase/cherry-pick/squash; fast-forward, detached HEAD, stash,
tag. **Semantic Versioning** (MAJOR.MINOR.PATCH), **Conventional Commits**.
Workflow: Git Flow vs GitHub Flow vs Trunk-Based (default to trunk-based for CD).

## 10. Testing
- **Levels:** unit, integration, contract, E2E, smoke, regression.
- **Shape:** Test Pyramid (default) or Test Diamond; more fast tests, fewer slow.
- **Approaches:** TDD, BDD, ATDD, mutation testing.
- **Doubles:** mock, stub, spy, fake, fixture; snapshot testing.
- Test the behaviour you change at the *cheapest level that gives confidence*.

## 11. Clean Code
Meaningful names, small functions, single responsibility, no magic numbers, avoid
side effects, pure functions, guard clauses, early return, self-documenting code,
refactoring, Boy Scout Rule (leave it cleaner). See also `code-craft` skill.

## 12. Refactoring moves
Extract Method/Class, Inline Method, Rename, Replace Temp with Query, Introduce
Parameter Object, Encapsulate Field, Move Method, Replace Conditional with
Polymorphism. Refactor in small, behaviour-preserving steps with tests green.

## 13. Code smells (flag & fix)
God Object, Long Method, Large Class, Primitive Obsession, Feature Envy, Shotgun
Surgery, Data Clumps, Duplicate Code, Dead Code, Spaghetti/Lava Flow, Magic
Numbers, Long Parameter List.

## 14. Performance
Big O (time/space), caching, memoization, lazy vs eager loading, **N+1 query
problem**, pagination, connection pooling, batching, debouncing, throttling,
prefetching. Measure before optimising; don't add complexity the workload doesn't
justify.

## 15. Security (OWASP-first)
OWASP Top 10; SQL Injection, XSS, CSRF, SSRF, RCE. AuthN vs AuthZ; RBAC/ABAC; MFA;
password hashing + salting; encryption, TLS/HTTPS; CSP, CORS. Validate at
boundaries; least privilege; never log secrets; fail closed.

## 16. Agile
Agile Manifesto; Scrum/Kanban/XP/Lean; sprint, backlogs, user stories, story
points, planning poker, burndown, **Definition of Done / Ready**, retrospective.

## 17. Logging & monitoring
Structured logging; metrics; tracing; observability; health/readiness/liveness
probes; SLA/SLO/SLI. Make failures diagnosable; don't log sensitive data.

## 18. Concurrency
Thread/process/coroutine; async/await; mutex, semaphore, lock; deadlock, livelock,
starvation, race condition; producer-consumer, actor model. Prefer immutability
and message-passing; make shared-state access explicit and minimal.

## 19. Data structures & algorithms
Array, linked list, stack, queue, deque, heap, hash table, tree, trie, graph,
bloom filter, B-tree, red-black tree. Algorithms: binary search, BFS, DFS,
Dijkstra, A*, merge/quick/heap sort, dynamic programming, greedy, divide &
conquer, backtracking. Pick the structure whose operations match the access
pattern.

## 20. Functional principles
Pure functions, referential transparency, immutability, higher-order & first-class
functions, currying, partial application, function composition, monads/functors,
lazy evaluation. Reach for to reduce side effects and improve testability.

## 21. Front-end & UX
- **Semantic HTML** — native elements before ARIA; landmarks, heading order,
  buttons vs links. The foundation of accessibility and SEO; always on UI work.
- **Accessibility (WCAG 2.2 AA)** — keyboard operability, visible focus,
  contrast (4.5:1 text / 3:1 UI), labels, announced dynamic content,
  reduced-motion. Correctness, not polish; any user-facing surface.
- **Design tokens & design system** — colors/type/spacing/radii as a single
  source of truth; components with variants *and states*; extend the system,
  never fork it. Reach for whenever styling anything.
- **Typography & spacing scales** — a modular type scale and one spacing scale;
  off-scale values are drift.
- **Responsive & mobile-first** — content-driven breakpoints, fluid layout,
  reflow without horizontal scroll; test what you claim.
- **State completeness** — loading, empty, error, disabled, focus, hover ship
  with the component, not as follow-ups.
- **Core Web Vitals & performance budget** — LCP/CLS/INP targets, asset weight,
  image/font strategy, minimal shipped JS. Any page users wait for.
- **Forms & validation UX** — visible labels, inline errors that help recovery,
  no placeholder-as-label, sensible defaults.
- **Story-first structure** — every page has one goal; sections carry
  message/feel/evidence/action; hierarchy scannable from headings alone.
  Reach for on marketing/landing/storefront pages especially.
- **SEO fundamentals** — unique titles/descriptions, canonical, Open Graph,
  structured data where genuine. Public pages only.
- **UI architecture** — MVC/MVVM/Flux per the stack's idiom (§2); component
  composition over inheritance; container/presentational separation only when
  it earns its keep.

---

## The "must-know" core (weight these highest)
SOLID · DRY · KISS · YAGNI · Separation of Concerns · High Cohesion/Low Coupling ·
Clean Architecture · GoF patterns · DDD basics · ACID/BASE/CAP · REST & API design
· Git & branching strategy · CI/CD · Testing (TDD, unit/integration/E2E) · Clean
Code & Refactoring · Big O & data structures · Concurrency & async · Security
(OWASP Top 10) · Docker/Kubernetes concepts · Observability · Front-end & UX
(semantic HTML, WCAG, design tokens, Core Web Vitals) on any user-facing work.
