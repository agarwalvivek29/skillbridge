# Spec: Dispute Resolution with AI Evidence and Community Arbitration

**Issue**: #9
**Status**: Approved
**Author**: agent
**Date**: 2026-03-09
**Services Affected**: api

---

## Summary

Implement dispute resolution for milestones on SkillBridge. Either party (client or freelancer) can raise a dispute on a submitted milestone. The system generates an AI evidence summary, opens a 3-day discussion window, and escalates to arbitration if unresolved. An admin resolves disputes on-chain.

---

## Background and Motivation

Disputes are inevitable in a freelance marketplace. Current competitors charge $337+ for dispute resolution and take weeks. SkillBridge automates evidence gathering via AI and provides structured resolution with on-chain finality. Without this, there is no recourse when parties disagree on deliverable quality.

---

## Scope

### In Scope

- Raise dispute on a milestone (client or freelancer)
- AI evidence summary generation (from existing ReviewReport or Claude API call)
- Discussion window with threaded messages
- Admin resolution endpoint that calls resolveDispute on-chain
- Background escalation from OPEN -> ARBITRATION after discussion deadline
- Notifications for DISPUTE_RAISED and DISPUTE_RESOLVED

### Out of Scope

- Community voting UI (future — admin resolves for v1)
- Automatic AI-based resolution (human admin decides)
- Frontend UI (separate issue)

---

## Acceptance Criteria

- [ ] Client or freelancer can raise a dispute on a milestone in SUBMITTED or UNDER_REVIEW status
- [ ] Only one active dispute per milestone
- [ ] AI evidence summary is generated asynchronously within 60s of dispute creation
- [ ] Discussion messages can be posted by client or freelancer while dispute is OPEN and before deadline
- [ ] Disputes escalate to ARBITRATION status after discussion_deadline passes
- [ ] Admin can resolve a dispute, recording resolution and tx_hash
- [ ] Milestone status transitions to DISPUTED when dispute is raised
- [ ] Notifications created for DISPUTE_RAISED and DISPUTE_RESOLVED events

---

## Technical Design

### Architecture Overview

```
[Client/Freelancer] -> POST /v1/milestones/{id}/dispute -> creates Dispute (OPEN)
                                                         -> sets milestone status = DISPUTED
                                                         -> triggers AI evidence generation (background)
                                                         -> creates DISPUTE_RAISED notification

[Client/Freelancer] -> POST /v1/disputes/{id}/messages -> adds DisputeMessage
                                                        -> only while OPEN and before deadline

[Background job]    -> every 15 min checks OPEN disputes past deadline -> sets ARBITRATION

[Admin]             -> POST /v1/disputes/{id}/resolve -> sets RESOLVED
                                                      -> records resolution + tx_hash
                                                      -> creates DISPUTE_RESOLVED notification
```

### API Changes

#### New Endpoints

```
POST /v1/milestones/{milestone_id}/dispute
  Auth: CLIENT or FREELANCER (must be gig party)
  Body: { reason: string }
  Response: Dispute object

GET /v1/disputes/{dispute_id}
  Auth: any authenticated user (gig party or admin)
  Response: Dispute object with messages

GET /v1/milestones/{milestone_id}/dispute
  Auth: any authenticated user (gig party)
  Response: Dispute object

POST /v1/disputes/{dispute_id}/messages
  Auth: CLIENT or FREELANCER (must be gig party)
  Body: { content: string }
  Response: DisputeMessage object

POST /v1/disputes/{dispute_id}/resolve
  Auth: ADMIN role
  Body: { resolution: string, freelancer_split_amount?: string, tx_hash: string }
  Response: Dispute object
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE disputes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  gig_id UUID NOT NULL REFERENCES gigs(id) ON DELETE CASCADE,
  raised_by_user_id UUID NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
  ai_evidence_summary TEXT,
  resolution VARCHAR(32),
  freelancer_split_amount TEXT,
  resolution_tx_hash TEXT,
  discussion_deadline TIMESTAMPTZ NOT NULL,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(milestone_id)
);

CREATE TABLE dispute_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dispute_id UUID NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Dependencies

- `anthropic` Python SDK (for AI evidence generation on file-only submissions)

---

## Security Considerations

- Only gig parties (client + assigned freelancer) can raise disputes or post messages
- Only ADMIN role can resolve disputes
- AI evidence generation uses ANTHROPIC_API_KEY from env (never exposed)
- Discussion messages are limited to parties involved in the dispute

---

## Testing Plan

### Unit Tests

- raise_dispute: validates milestone status, party access, duplicate prevention
- post_dispute_message: validates OPEN status, deadline, party access
- resolve_dispute: validates ADMIN role, status transition, resolution recording
- generate_ai_evidence: tests both repo_url and file-only paths
- escalate_disputes: tests deadline-based escalation

### Integration Tests

- Full dispute lifecycle via API endpoints
- Auth enforcement on all endpoints

---

## Migration / Rollout Plan

- **Database migrations**: Yes — migration 0008 creates disputes and dispute_messages tables
- **Breaking changes**: No
- **Rollback plan**: Drop tables via reverse migration

---

## References

- Related issues: #9, #12 (notifications dependency)
- Proto: `packages/schema/proto/api/v1/dispute.proto`
