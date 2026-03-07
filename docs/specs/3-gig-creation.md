# Spec: Gig Creation with Milestones and Acceptance Criteria

**Issue**: #3
**Status**: Approved
**Author**: agent
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Clients can create a gig with a title, description, required skills, and one or more milestones. Each milestone has a budget and acceptance criteria in markdown used by the AI reviewer. Gigs support both ETH and USDC as payment currency. Milestone amounts must sum to the total gig budget. Gigs start in `DRAFT` status and move to `OPEN` after escrow is funded (Issue #4).

---

## Background and Motivation

The gig creation flow is the primary client-facing feature of SkillBridge. Without it, clients cannot post work, freelancers cannot discover opportunities, and the escrow/review pipeline cannot start. This is a prerequisite for Issue #4 (escrow funding), Issue #5 (submissions), Issue #7 (AI review), and Issue #8 (discovery board).

---

## Scope

### In Scope

- `POST /v1/gigs` — create a gig with nested milestones
- `GET /v1/gigs` — list OPEN gigs (discovery board, paginated)
- `GET /v1/gigs/{gig_id}` — get a single gig with milestones
- `PUT /v1/gigs/{gig_id}` — edit a gig (only while in DRAFT)
- `DELETE /v1/gigs/{gig_id}` — delete a DRAFT gig
- SQLAlchemy models: `GigModel`, `MilestoneModel`
- Alembic migration: `0002_create_gigs_and_milestones`
- Server-side validation: milestone amounts sum = total_amount
- Auth ownership check: only the gig creator (client) can mutate their gig
- Unit tests for domain logic
- E2E tests for all endpoints

### Out of Scope

- Escrow funding (Issue #4)
- Work submissions (Issue #5)
- AI review (Issue #7)
- Proposal/application flow (Issue #8)
- `GET /v1/gigs/{gig_id}/milestones` (milestones returned nested in gig response)

---

## Acceptance Criteria

- [ ] Given an authenticated client, when POST /v1/gigs is called with valid body and 1–10 milestones, then a gig is created with status DRAFT and milestones are persisted.
- [ ] Given milestone amounts that do not sum to total_amount, when POST /v1/gigs is called, then 422 is returned with a clear validation error.
- [ ] Given a DRAFT gig owned by the authenticated client, when PUT /v1/gigs/{id} is called with valid data, then the gig and milestones are updated.
- [ ] Given a gig with status OPEN or later, when PUT /v1/gigs/{id} is called, then 409 is returned.
- [ ] Given a gig owned by a different user, when PUT or DELETE is called, then 403 is returned.
- [ ] Given GET /v1/gigs (no filter), then only OPEN gigs are returned.
- [ ] Given GET /v1/gigs/{id}, then the gig and its milestones are returned regardless of status (to the owner or after OPEN).
- [ ] Given a DRAFT gig owned by the client, when DELETE /v1/gigs/{id} is called, then 204 is returned and the gig is deleted.
- [ ] For ETH gigs: token_address is optional/empty.
- [ ] For USDC gigs: token_address is required and validated as non-empty.

---

## Technical Design

### Architecture Overview

All business logic lives in `src/domain/gig.py`. The FastAPI router at `src/api/gig.py` delegates to domain functions. SQLAlchemy models are in `src/infra/models.py`. Types come from proto (already defined in `packages/schema/proto/api/v1/gig.proto` and `milestone.proto`); Pydantic request/response shapes are thin wrappers in the router file.

```
POST /v1/gigs
  → auth middleware (JWT/API key)
  → GigRouter.create_gig
    → domain.gig.create_gig_with_milestones(db, client_id, body)
      → validate milestone sum == total_amount
      → insert GigModel + MilestoneModels
      → return GigResponse with nested milestones
```

### API Changes

#### New Endpoints

```
POST /v1/gigs
  Auth: Bearer JWT (client role)
  Request: CreateGigRequest + nested milestones[]
  Response: GigResponse (201)

GET /v1/gigs
  Auth: Bearer JWT or API Key
  Query: page, page_size, skill, currency
  Response: GigsListResponse (200) — only OPEN gigs

GET /v1/gigs/{gig_id}
  Auth: Bearer JWT or API Key
  Response: GigResponse with milestones (200)

PUT /v1/gigs/{gig_id}
  Auth: Bearer JWT (must be owner)
  Request: UpdateGigRequest + optional milestones[]
  Response: GigResponse (200)
  Error: 409 if not DRAFT, 403 if not owner

DELETE /v1/gigs/{gig_id}
  Auth: Bearer JWT (must be owner)
  Response: 204 No Content
  Error: 409 if not DRAFT, 403 if not owner
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE gigs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   UUID NOT NULL REFERENCES users(id),
  freelancer_id UUID REFERENCES users(id),
  title       TEXT NOT NULL,
  description TEXT NOT NULL,
  total_amount TEXT NOT NULL,
  currency    VARCHAR(32) NOT NULL DEFAULT 'CURRENCY_ETH',
  token_address TEXT NOT NULL DEFAULT '',
  contract_address TEXT NOT NULL DEFAULT '',
  status      VARCHAR(32) NOT NULL DEFAULT 'GIG_STATUS_DRAFT',
  tags        TEXT[] NOT NULL DEFAULT '{}',
  required_skills TEXT[] NOT NULL DEFAULT '{}',
  deadline    TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE milestones (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gig_id              UUID NOT NULL REFERENCES gigs(id) ON DELETE CASCADE,
  title               TEXT NOT NULL,
  description         TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL,
  amount              TEXT NOT NULL,
  "order"             INTEGER NOT NULL,
  status              VARCHAR(32) NOT NULL DEFAULT 'MILESTONE_STATUS_PENDING',
  contract_index      INTEGER NOT NULL DEFAULT -1,
  revision_count      INTEGER NOT NULL DEFAULT 0,
  due_date            TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Queue / Event Changes

None for this issue. GigCreatedEvent will be published in a future issue when the notification service is implemented.

### Dependencies

No new packages. Uses existing: SQLAlchemy, FastAPI, Pydantic, Alembic.

---

## Security Considerations

- Auth middleware already applied globally; all gig routes are protected.
- Ownership check: `gig.client_id == request.state.user_id` before any mutation.
- Status guard: mutations blocked once gig leaves DRAFT.
- Input: milestone amounts validated as valid integer strings (wei/smallest unit).
- Max milestone count: 10 (enforced in domain validation).
- USDC: token_address required and non-empty when currency = USDC.

---

## Observability

- **Logs**: Log `gig_id`, `client_id`, `status` on create, update, delete at INFO level.
- **Metrics**: No new metrics in v1 (covered by existing /metrics stub).
- **Alerts**: None for v1.

---

## Testing Plan

### Unit Tests (`tests/unit/test_gig.py`)

- `validate_milestone_sum` — happy path, sum mismatch, empty list, >10 milestones
- `validate_usdc_token_address` — empty token for USDC returns error
- `validate_milestone_count` — 0 milestones, 11 milestones rejected

### E2E Tests (`tests/e2e/test_gig.py`)

- POST /v1/gigs — happy path, sum mismatch, unauthenticated, wrong role
- GET /v1/gigs — returns only OPEN gigs
- GET /v1/gigs/{id} — owner can read DRAFT, 404 for non-existent
- PUT /v1/gigs/{id} — happy path, non-owner rejected, OPEN gig rejected
- DELETE /v1/gigs/{id} — happy path, non-DRAFT rejected

### Manual Testing Steps

1. Start the API with `docker compose up api`
2. Register as CLIENT role
3. POST /v1/gigs with 2 milestones whose amounts sum to total_amount — expect 201
4. GET /v1/gigs — expect 0 results (gig is DRAFT)
5. GET /v1/gigs/{id} — expect gig with milestones
6. PUT /v1/gigs/{id} with updated title — expect 200
7. DELETE /v1/gigs/{id} — expect 204

---

## Migration / Rollout Plan

- **Database migrations**: Yes — `0002_create_gigs_and_milestones.py`
- **Breaking changes**: No
- **Feature flag**: No
- **Rollback plan**: Run `alembic downgrade 0001` to drop `gigs` and `milestones` tables. No data loss risk on DRAFT gigs.

---

## Open Questions

| Question                                            | Owner | Status                                                                   |
| --------------------------------------------------- | ----- | ------------------------------------------------------------------------ |
| Should GET /v1/gigs return DRAFT gigs to the owner? | agent | Resolved: no, only OPEN on discovery board; owner uses GET /v1/gigs/{id} |

---

## References

- Related ADR: [ADR 0002](../adr/0002-tech-stack.md)
- Related issues: #4 (escrow funding), #7 (AI review), #8 (discovery board)
- Proto: `packages/schema/proto/api/v1/gig.proto`, `milestone.proto`
