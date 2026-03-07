# Spec: Gig Creation with Milestones and Acceptance Criteria

**Issue**: #3
**Status**: Approved
**Author**: team
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Clients can create a gig with a title, description, required skills, and one or more milestones. Each milestone has a budget and acceptance criteria used by the AI reviewer. Gigs support both ETH and USDC as payment currency.

---

## Background and Motivation

The gig is the central entity in SkillBridge. Without gig creation, clients cannot post work and freelancers have nothing to discover or apply to. This is the first step in the core product loop: Create Gig → Fund Escrow → Freelancer Applies → Work Submitted → AI Review → Approval → Payment.

---

## Scope

### In Scope

- Gig CRUD endpoints (create, read, update, delete) in `services/api`
- Milestone creation nested within gig creation
- Server-side validation that milestone amounts sum to total gig budget
- Status management: DRAFT on creation, OPEN after escrow funded (funded transition handled by issue #4)
- Gig discovery list (public, filtered by OPEN status)
- Auth enforcement: only CLIENT-role users can create gigs

### Out of Scope

- Escrow funding and the DRAFT → OPEN transition (issue #4)
- Freelancer application/proposal flow (issue #8)
- Work submission on milestones (issue #5)
- Milestone approval and fund release (issue #6)

---

## Acceptance Criteria

- [ ] Given an authenticated CLIENT user, when POST /v1/gigs is called with valid payload, then a gig is created in DRAFT status and returned
- [ ] Given a gig creation request, when milestone amounts do not sum to total_amount, then server returns 400 with code MILESTONE_AMOUNT_MISMATCH
- [ ] Given a gig creation request, when currency is ETH, then token_address must be empty or absent
- [ ] Given a gig creation request, when currency is USDC, then token_address must be a valid 0x... address
- [ ] Given an authenticated CLIENT user, when GET /v1/gigs/{gig_id} is called, then the gig and all its milestones are returned
- [ ] Given no auth, when GET /v1/gigs is called, then open gigs are listed (discovery board)
- [ ] Given an authenticated CLIENT owner, when PUT /v1/gigs/{gig_id} is called and gig is in DRAFT, then gig is updated
- [ ] Given an authenticated CLIENT owner, when PUT /v1/gigs/{gig_id} is called and gig is OPEN, then 409 is returned
- [ ] Given an authenticated CLIENT owner, when DELETE /v1/gigs/{gig_id} is called and gig is in DRAFT, then gig is deleted
- [ ] Given a gig with 0 or more than 10 milestones in the request, server returns 400
- [ ] Given a non-CLIENT user or unauthenticated user, when POST /v1/gigs is called, then 403 is returned

---

## Technical Design

### Architecture Overview

The gig creation flow lives entirely in `services/api`. A single POST /v1/gigs endpoint accepts gig fields plus a milestones array. The domain layer validates milestone amounts, creates both records in a single DB transaction, and returns the composed response.

```
Client → POST /v1/gigs (with milestones[])
           ↓
       AuthMiddleware (JWT required, CLIENT role)
           ↓
       api/gig.py router
           ↓
       domain/gig.py: validate → create GigModel + MilestoneModels
           ↓
       PostgreSQL (gigs + milestones tables)
```

### API Changes

#### New Endpoints

```
POST /v1/gigs
  Auth: Bearer JWT (CLIENT role required)
  Request: { title, description, total_amount, currency, token_address?, tags?, required_skills[], deadline?, milestones: [{title, description, acceptance_criteria, amount, order, due_date?}] }
  Response 201: { id, client_id, title, description, total_amount, currency, token_address, status, tags, required_skills, deadline, milestones: [...], created_at, updated_at }

GET /v1/gigs
  Auth: none required
  Query: status?, page?, page_size?
  Response 200: { gigs: [...], total, page, page_size }

GET /v1/gigs/{gig_id}
  Auth: none required
  Response 200: { id, ..., milestones: [...] }

PUT /v1/gigs/{gig_id}
  Auth: Bearer JWT (must be gig client_id owner)
  Request: same shape as POST (all fields optional)
  Response 200: updated gig with milestones

DELETE /v1/gigs/{gig_id}
  Auth: Bearer JWT (must be gig client_id owner)
  Response 204: no content
```

### Data Model Changes

#### New Tables

```sql
CREATE TYPE gig_status AS ENUM ('DRAFT','OPEN','IN_PROGRESS','COMPLETED','CANCELLED','DISPUTED');
CREATE TYPE currency AS ENUM ('ETH','USDC');

CREATE TABLE gigs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES users(id),
  freelancer_id UUID REFERENCES users(id),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  total_amount TEXT NOT NULL,
  currency gig_status NOT NULL,
  token_address TEXT,
  contract_address TEXT,
  status gig_status NOT NULL DEFAULT 'DRAFT',
  tags TEXT[] NOT NULL DEFAULT '{}',
  required_skills TEXT[] NOT NULL DEFAULT '{}',
  deadline TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE milestone_status AS ENUM ('PENDING','IN_PROGRESS','SUBMITTED','APPROVED','DISPUTED','RESOLVED');

CREATE TABLE milestones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gig_id UUID NOT NULL REFERENCES gigs(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL,
  amount TEXT NOT NULL,
  "order" INTEGER NOT NULL,
  due_date TIMESTAMPTZ,
  status milestone_status NOT NULL DEFAULT 'PENDING',
  revision_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Queue / Event Changes

None in this issue. GigCreatedEvent will be published in a follow-up.

### Dependencies

No new packages. Existing FastAPI, SQLAlchemy, Pydantic stack is sufficient.

---

## Security Considerations

- Only CLIENT-role users may create gigs (role check in domain layer)
- Gig owner check on PUT/DELETE prevents other users from mutating gigs
- Status guard prevents editing OPEN/IN_PROGRESS/COMPLETED gigs
- total_amount and milestone amounts are stored as strings (wei) to avoid floating point errors
- token_address for ETH must be empty; for USDC must match ERC-20 address format

---

## Observability

- **Logs**: INFO on gig created (gig_id, client_id, currency); WARN on validation failures
- **Metrics**: none new in v1 (standard FastAPI metrics via /metrics)
- **Alerts**: none new in v1

---

## Testing Plan

### Unit Tests

- `test_gig_domain.py`: create_gig with valid data, milestone sum mismatch, too many milestones, update DRAFT, update OPEN (forbidden), delete DRAFT, delete OPEN (forbidden)

### Integration Tests

- `test_gig_api.py`: POST /v1/gigs happy path, milestone mismatch 400, GET /v1/gigs (public), GET /v1/gigs/{id} with milestones, PUT (update), DELETE, auth enforcement

### Manual Testing Steps

1. POST /v1/auth/email/register with role=USER_ROLE_CLIENT
2. POST /v1/gigs with 2 milestones, amounts summing to total_amount
3. GET /v1/gigs — verify gig appears in list (it will only appear when OPEN; DRAFT is not on discovery board)
4. GET /v1/gigs/{id} — verify milestones attached
5. PUT /v1/gigs/{id} — update title, verify change persisted
6. DELETE /v1/gigs/{id} — verify 204

---

## Migration / Rollout Plan

- **Database migrations**: yes — new migration `0002_create_gigs_and_milestones.py`
- **Breaking changes**: no — all new tables
- **Feature flag**: no
- **Rollback plan**: `alembic downgrade 0001` drops the two new tables without affecting users/auth

---

## Open Questions

| Question                                                        | Owner | Status               |
| --------------------------------------------------------------- | ----- | -------------------- |
| Should clients be allowed to add milestones after gig creation? | team  | Deferred to issue #5 |

---

## References

- Related ADR: docs/adr/0002-tech-stack.md
- Related issues: #4 (escrow funding, DRAFT→OPEN), #5 (submissions), #8 (proposals)
