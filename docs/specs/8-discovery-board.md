# Spec: Gig Discovery Board and Application Flow

**Issue**: #8
**Status**: Approved
**Author**: team
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Freelancers can browse funded, open gigs on a discovery board, filter by skills and currency, and
submit proposals. The client reviews proposals and selects one freelancer to begin work.

---

## Background and Motivation

Without a discovery board, freelancers have no way to find work and clients have no way to attract
talent. This is the core marketplace mechanic that connects supply (freelancers) with demand
(clients). After escrow funding (Issue #4), gigs enter `OPEN` status and must become visible
to freelancers.

---

## Scope

### In Scope

- Discovery board: list all `OPEN` (funded) gigs with filters (skills, currency, budget range)
- Freelancer submits a proposal (cover letter + estimated days)
- Client views all proposals for their gig
- Client accepts one proposal → gig moves to `IN_PROGRESS`, others rejected
- Freelancer withdraws their own proposal before a decision
- In-app notifications: proposal received (→ client), proposal accepted/rejected (→ freelancer)

### Out of Scope

- Email notifications (Issue #12)
- Full notification inbox UI (Issue #12)
- Dispute resolution (Issue #9)
- AI code review (Issue #7)

---

## Acceptance Criteria

- [ ] `GET /v1/gigs` returns only `OPEN` gigs by default, with filters: `skill`, `currency`,
      `min_amount`, `max_amount`
- [ ] `POST /v1/proposals` creates a proposal for an OPEN gig; freelancer role required; one
      proposal per freelancer per gig enforced; client notified via in-app notification
- [ ] `GET /v1/gigs/{gig_id}/proposals` returns all proposals for a gig; client-only
- [ ] `POST /v1/proposals/{proposal_id}/accept` accepts a proposal; client-only; gig → IN_PROGRESS;
      freelancer assigned; all other proposals → REJECTED; accepted freelancer notified; others notified
- [ ] `POST /v1/proposals/{proposal_id}/withdraw` withdraws a proposal; freelancer-only; only
      PENDING proposals may be withdrawn

---

## Technical Design

### Architecture Overview

All logic lives in `services/api`. Two new resource modules are added:

- `src/domain/proposal.py` — business logic
- `src/api/proposal.py` — FastAPI router

The discovery board enhancements live in the existing `gig` modules.

```
POST /v1/proposals            → domain/proposal.py::create_proposal
GET  /v1/gigs/{id}/proposals  → domain/proposal.py::list_proposals
POST /v1/proposals/{id}/accept    → domain/proposal.py::accept_proposal
POST /v1/proposals/{id}/withdraw  → domain/proposal.py::withdraw_proposal
GET  /v1/gigs (enhanced)      → domain/gig.py::list_gigs (+ filters)
```

### API Changes

#### New Endpoints

```
POST /v1/proposals
  Body: { gig_id: str, cover_letter: str, estimated_days: int }
  Response: Proposal
  Auth: FREELANCER role

GET /v1/gigs/{gig_id}/proposals
  Query: page, page_size
  Response: { proposals: Proposal[], total, page, page_size }
  Auth: required (client must own the gig)

POST /v1/proposals/{proposal_id}/accept
  Response: Proposal
  Auth: CLIENT role (must own the gig)

POST /v1/proposals/{proposal_id}/withdraw
  Response: Proposal
  Auth: FREELANCER role (must own the proposal)
```

#### Modified Endpoints

```
GET /v1/gigs
  Added query params: skill (str), currency (str), min_amount (str), max_amount (str)
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gig_id UUID NOT NULL REFERENCES gigs(id) ON DELETE CASCADE,
  freelancer_id UUID NOT NULL REFERENCES users(id),
  cover_letter TEXT NOT NULL,
  estimated_days INTEGER NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (gig_id, freelancer_id)
);

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  type VARCHAR(64) NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Notification Events

| Trigger                        | Type                                  | Recipient         |
| ------------------------------ | ------------------------------------- | ----------------- |
| Proposal submitted             | `NOTIFICATION_TYPE_PROPOSAL_RECEIVED` | gig client        |
| Proposal accepted              | `NOTIFICATION_TYPE_PROPOSAL_ACCEPTED` | freelancer        |
| Proposal rejected (via accept) | `NOTIFICATION_TYPE_PROPOSAL_REJECTED` | other freelancers |

---

## Security Considerations

- `POST /v1/proposals`: freelancer cannot submit more than one proposal per gig
- `GET /v1/gigs/{gig_id}/proposals`: only the gig owner (client) may see proposals
- `POST /v1/proposals/{id}/accept`: only the gig client may accept; gig must be OPEN
- `POST /v1/proposals/{id}/withdraw`: only the proposal owner; proposal must be PENDING
- All endpoints protected by auth middleware

---

## Testing Plan

### Unit Tests

- `tests/unit/test_proposal_domain.py` — all domain functions: create, list, accept, withdraw

### Integration Tests

- `tests/e2e/test_proposal_api.py` — happy path for each endpoint + error cases

### Manual Testing Steps

1. Register a client, create a gig, set status to OPEN (or fund via escrow)
2. Register a freelancer, submit a proposal
3. As client, view proposals for the gig
4. As client, accept one proposal; verify gig status = IN_PROGRESS
5. Verify other proposals are REJECTED

---

## Migration / Rollout Plan

- **Database migrations**: Yes — migration `0003_create_proposals_and_notifications.py`
- **Breaking changes**: No
- **Feature flag**: No
- **Rollback plan**: Run `alembic downgrade 0002`; drop `proposals` and `notifications` tables

---

## References

- Related ADR: [0002-tech-stack.md](../adr/0002-tech-stack.md)
- Related issues: #4 (escrow funding moves gig to OPEN), #12 (full notifications)
