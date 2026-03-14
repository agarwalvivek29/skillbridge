# Core Repository Rules

> **This document is law.** It applies equally to every contributor — human or AI agent.
> No exception is valid unless it is itself captured in an ADR.

---

## 1. Spec-First Development

**No feature code may be written without a corresponding spec file.**

- Every feature, enhancement, or significant refactor requires a spec at `docs/specs/[ISSUE-NUMBER]-[feature-name].md`
- Use `docs/specs/TEMPLATE.md` as the starting point
- The spec must exist and be linked in the GitHub Issue **before** any implementation begins
- Agents must verify the spec exists before starting any non-trivial coding task

Exceptions: bug fixes, typo corrections, dependency updates, and documentation-only changes.

---

## 2. Architecture Decision Records (ADRs)

**Any decision affecting more than one service, the data layer, or infrastructure requires an ADR.**

- ADRs live in `docs/adr/[NNNN]-[short-title].md`
- Use `docs/adr/README.md` to find the next sequential number
- ADRs are append-only — once accepted, they are never deleted, only superseded
- If you are reversing a previous decision, create a new ADR that references and supersedes the old one
- ADRs must be referenced in both the spec and the PR

Triggers for an ADR:

- Choosing a new database, queue, or caching layer
- Changing API protocol (REST → gRPC, etc.)
- Adding a new shared package or cross-service dependency
- Significant infra change (new AWS service, new docker-compose service)
- Changing authentication/authorization strategy
- Any decision that future contributors will ask "why did we do it this way?"

---

## 3. Plan-Before-Code

**Non-trivial work requires an approved plan before implementation.**

- **Agents**: Use `EnterPlanMode` for any task touching more than 2 files or introducing new architecture. Exit only when the plan is documented and approved.
- **Humans**: Write a brief implementation plan as a comment on the GitHub Issue. Get a LGTM from at least one other team member.
- A "plan" must include: what files change, why, and what the rollback strategy is.
- Agents must **not** write production code during the planning phase.

---

## 4. Conventional Commits

**All commits must follow the Conventional Commits specification. No AI authorship attribution.**

Format: `<type>(<scope>): <description>`

Allowed types:

- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `refactor` — code change that neither fixes a bug nor adds a feature
- `test` — adding or correcting tests
- `chore` — build process, dependency updates, tooling
- `perf` — performance improvement
- `ci` — CI/CD changes

Scope is the service or package name (e.g., `feat(auth-service): add JWT refresh endpoint`).

This is enforced by the `commit-msg` git hook. Hooks must **never** be skipped (`--no-verify` is forbidden unless explicitly approved in an ADR).

**No AI attribution in commits or PRs:**

- Never add `Co-Authored-By: Claude` or any AI model as a co-author in commit messages
- Never mention Claude, Anthropic, or any AI tool in PR titles, PR bodies, or commit messages
- Commits and PRs represent the team's work — AI tooling is an implementation detail, not a contributor

---

## 5. No Direct Commits to Main

**Main is a protected branch. All changes arrive via Pull Request.**

- PRs require at least one approval
- All CI checks must pass before merge
- Squash merges are preferred to keep history clean
- Branch naming: `feat/[ISSUE-NUMBER]-[short-description]`, `fix/[ISSUE-NUMBER]-[short-description]`

---

## 6. Service Isolation

**Each microservice is a self-contained unit.**

- Every service has its own `Dockerfile`, `.env.example`, and `AGENTS.md`
- Services communicate only via well-defined interfaces (HTTP, gRPC, events, queues) — never via shared in-process state
- Shared code lives in `packages/` — it is never copy-pasted between services
- A new service must be created via `scripts/new-service.sh`, not manually

---

## 7. Docker-First Local Development

**All services and infrastructure run via `docker-compose`. "Works on my machine" is not acceptable.**

- Every service must have a working `Dockerfile` with multi-stage build (dev + prod targets)
- Local dev uses hot-reload where possible
- `infra/docker-compose.yml` is the single source of truth for local infra
- Environment variables are managed via `.env` files (gitignored); `.env.example` is always committed
- No service should require manual steps beyond `docker compose up`

---

## 8. Test Coverage

**PRs must not reduce test coverage below the established baseline.**

- Unit tests live alongside the code they test
- Integration tests live in a `tests/` directory at the service root
- CI enforces the coverage gate — PRs failing coverage checks are not merged
- Test files follow the same conventional commit and review standards as production code

---

## 9. Secret Hygiene

**Secrets and credentials are never committed to the repository.**

- `.env` files are always gitignored
- `.env.example` is committed with placeholder (non-functional) values
- Never hardcode API keys, passwords, or tokens in source code
- CI secrets are managed through the platform secret store (GitHub Actions secrets, AWS Secrets Manager)
- If a secret is accidentally committed: revoke it immediately, rotate it, then remove it from git history

---

## 11. Agent Operating Discipline

**Agents must follow additional rules beyond those for humans.**

- Read `AGENTS.md` in every service being modified before writing any code
- Consult `docs/specs/` and `docs/adr/` before proposing solutions
- Never modify infrastructure (docker-compose, AWS configs) without explicit human approval
- Always prefer editing existing files over creating new ones
- Maintain memory files (`.claude/memory/`) to preserve context across sessions
- If a task is unclear, stop and ask — do not make assumptions that affect architecture
- Agents may download and use MCP servers, skills, and tools as needed, but must document any new tool dependency in the service's `AGENTS.md`

---

---

## 10. Mandatory Auth Middleware

**Every backend service endpoint must be protected by authentication middleware.**

All inbound requests — whether from the frontend (FE→BE) or from another service (BE↔BE) — must carry a valid credential. The middleware accepts either:

- **JWT** (`Authorization: Bearer <token>`) — for user sessions and service-issued JWTs
- **API Key** (`X-API-Key: <key>`) — for direct service-to-service calls without user context

Both the JWT secret and API key are shared across all services via environment variables (`JWT_SECRET`, `API_KEY`). This is an acceptable simplification; rotate both via a coordinated config update when needed.

**Exempt paths** (must be explicitly allowlisted in the middleware, not unprotected by default):

- `GET /health` — liveness/readiness probe
- `GET /metrics` — Prometheus scrape endpoint

**Rules:**

- Every new service starts with the auth middleware applied globally to all routes
- Middleware must be the **first** middleware in the chain (before logging, before rate limiting)
- On auth failure → `401 Unauthorized` with `ErrorResponse` body (from `common.v1.ErrorResponse`)
- Do not log tokens or API keys — log only the auth method and subject on success
- Services must never forward raw tokens in response bodies
- `JWT_SECRET` and `API_KEY` must be set via `.env` — never hardcoded

See `docs/CONVENTIONS.md → Authentication & Middleware` for per-language implementation patterns.

---

## 12. Schema-First Type Definitions

**All data types are defined in `packages/schema/proto/` before any service code is written.**

This applies without exception to:

- Database entities (User, Order, Payment…)
- View models / API response shapes (UserPublic, OrderSummary…)
- API request bodies (CreateUserRequest, UpdateOrderRequest…)
- Enums and status types (UserStatus, OrderState…)
- Event/queue payloads (UserCreatedEvent, PaymentCompletedEvent…)
- Internal domain objects used across functions

**Process:**

1. Add or modify the `.proto` file in `packages/schema/proto/[service-name]/v1/`
2. Run `cd packages/schema && ./scripts/generate.sh`
3. Commit the updated proto AND generated files together
4. Import the generated type in your service — never redefine it

Agents must NEVER define a `type`, `interface`, `struct`, `class`, `dataclass`, `enum`, or equivalent in service code for a business domain concept. If the type doesn't exist in `packages/schema/proto/`, create it there first.

See `packages/schema/README.md` for the full guide.

---

## 13. Mandatory Tests for Backend Services

**All backend services must have both unit and end-to-end tests.**

- `tests/unit/` — unit tests covering every public function in `domain/`
- `tests/e2e/` — integration tests covering the happy path of every API endpoint or queue consumer
- Frontend apps (`apps/`) are exempt from this rule

Test frameworks by language:

- TypeScript: **vitest** (unit) + **supertest** (e2e)
- Python: **pytest** (unit) + **httpx** (e2e)
- Go: **testing** + **testify** (unit), **testcontainers-go** (e2e)
- Rust: **cargo test** (unit), **testcontainers-rs** (e2e)

CI runs tests and enforces that coverage does not decrease. PRs that add features without tests will not be merged.

---

## 14. No Example or Placeholder Data in Production Code

**Scaffolded example content must be removed before any code ships.**

When a new service, module, route, or model is created (via `scripts/new-service.sh`, a framework generator, or manually), it often contains boilerplate: sample model instances, `hello world` endpoints, demo seed records, or TODO stubs left by the generator. All of this must be deleted before the first commit that contains real feature code.

**Must be removed:**

- Sample model instances left by generators (e.g. `user = User(id=1, name="Alice")`)
- Demo or scaffold routes (e.g. `GET /example`, `GET /hello`, `POST /demo`)
- Scaffold comments: `# TODO: replace with your logic`, `// Example usage:`, `/* Remove before shipping */`
- Hardcoded test credentials or placeholder tokens in source files (outside `.env.example`)
- Seed scripts that insert fake records into the DB — unless they live in `tests/fixtures/` and are explicitly test-only
- Unused imports or variables introduced solely by the scaffold

**Allowed to stay:**

- `.env.example` placeholder values (required by Rule 9)
- `tests/fixtures/` files used exclusively by automated tests
- `docs/specs/TEMPLATE.md` and other template/doc files

**When this applies:**

- Creating a new service via `scripts/new-service.sh`
- Adding a route/module via a framework generator
- Copying an existing file as a starting point — strip all non-applicable example content first
- Writing scaffold code before real logic — cleanup must be in the same PR, never deferred

**Agents:** scan the full diff before pushing. If any file in the diff contains example, placeholder, or demo content not covered by real implementation, fix it in the same branch before opening the PR.

---

## 15. Proto Field Name Alignment Across Layers

**Proto defines canonical field names. Every layer must use them consistently.**

- API Pydantic models MUST use the same field names as the proto definitions. Never create alias fields (e.g., `project_url` for `external_url`, or `display_name` for `name`).
- Frontend TypeScript types MUST match the JSON field names returned by the API.
- If a frontend API client function needs to map between user-facing form names and API field names (e.g., `skills` → `required_skills`), this mapping must happen exclusively in the API client function (`lib/api/*.ts`), not in components or types.
- When in doubt, check `packages/schema/proto/` for the canonical name.

---

## 16. Enum Constants — No Raw String Literals

**Never use raw string literals for status, role, or currency values.**

- Backend: import from `services/api/src/domain/enums.py` (or the equivalent enum module for other services). See `services/api/src/domain/enums.py` for all enum definitions. Never write `"OPEN"`, `"CLIENT"`, or `"SOL"` as bare strings in business logic.
- Frontend: define typed string union types that match proto enum values (e.g., `type GigStatus = "DRAFT" | "OPEN" | "IN_PROGRESS" | ...`). Never use untyped strings for enum-like values.
- If a new enum value is needed, add it to the proto first, regenerate, then update `domain/enums.py` and frontend types.

---

## 17. Safe Array Access

**Always use null-safe defaults when accessing array fields from API responses.**

- Frontend: use `?? []` when accessing any array field from an API response (e.g., `gig.milestones ?? []`, `gig.skills ?? gig.required_skills ?? []`).
- Backend: use `or []` in Python when accessing optional list fields from database models or request payloads.
- This prevents runtime crashes when the API returns `null` or `undefined` for an optional array field.

---

## 18. Amount Formatting

**All monetary amounts are stored and transmitted in smallest unit. Display must use human-readable formatting.**

- Storage and API transport: amounts are always in the smallest unit of the currency (lamports for SOL at 10^9, smallest unit for USDC at 10^6).
- Frontend display: always use the shared formatting utility (`formatAmountWithCurrency()` from `lib/format.ts`) when rendering amounts to users. Never display raw on-chain amounts.
- Valid currencies are **SOL** and **USDC**. ETH is not a valid currency in this project (see ADR 0003 — Solana migration).

---

## Checklist: Before Opening a PR

- [ ] Spec file exists in `docs/specs/` and is linked in the issue
- [ ] ADR created if an architectural decision was made
- [ ] All commits follow Conventional Commits format
- [ ] `AGENTS.md` updated if service behavior or architecture changed
- [ ] New types defined in `packages/schema/proto/` (not in service code)
- [ ] `packages/schema/generated/` regenerated and committed
- [ ] Unit tests written for new domain logic
- [ ] E2E tests written for new API endpoints / queue handlers
- [ ] Coverage not reduced
- [ ] `.env.example` updated if new env vars were added
- [ ] No secrets committed
- [ ] No scaffold/example/placeholder code remaining in the diff (Rule 14)
- [ ] No AI attribution (`Co-Authored-By: Claude`) in any commit message or PR body (Rule 4)
- [ ] Pydantic/TS field names match proto definitions — no alias fields (Rule 15)
- [ ] No raw string literals for enum values — import from `domain/enums.py` or typed unions (Rule 16)
- [ ] Array fields accessed with `?? []` (frontend) or `or []` (backend) fallbacks (Rule 17)
- [ ] Amounts displayed via `formatAmountWithCurrency()`, not raw values (Rule 18)
- [ ] `docker compose up` still works
