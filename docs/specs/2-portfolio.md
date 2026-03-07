# Spec: Freelancer Portfolio with Verified Delivery Badges

**Issue**: #2
**Status**: Approved
**Author**: Claude (ao agent)
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Freelancers can create, manage, and display portfolio items showcasing their work. Items linked
to a completed on-chain gig automatically display a "Verified Delivery" badge — the core trust
differentiator that lets clients know the work was actually delivered and accepted on-chain.

---

## Background and Motivation

Trust is the hardest problem in freelance marketplaces. Anyone can claim they built X; very few
can prove it was accepted and paid. SkillBridge's "Verified Delivery" badge bridges that gap:
if a portfolio item is linked to a gig whose escrow was released, the badge is earned automatically
with no manual verification needed. Without this feature, the portfolio is indistinguishable from
any other freelance profile page.

---

## Scope

### In Scope

- CRUD endpoints for portfolio items (`POST`, `GET`, `PUT`, `DELETE /v1/portfolio`)
- Portfolio item fields: title, description, S3 file keys, external URL, tags, optional verified_gig_id
- S3 presigned URL generation for file uploads (files never pass through the API)
- Badge logic: `verified_gig_id` set AND linked gig status is `GIG_STATUS_COMPLETED`
- Profile page endpoint: list items for a given user ordered by creation date (newest first)
- Authorization: only the owner can create/edit/delete their own items

### Out of Scope

- Frontend rendering of the badge (web app concern)
- Gig creation/management (separate issue)
- File content validation or virus scanning
- Pagination of portfolio items (deferred to v2)

---

## Acceptance Criteria

- [ ] Given an authenticated user, when they POST `/v1/portfolio`, then a portfolio item is created and returned
- [ ] Given a portfolio item owner, when they PUT `/v1/portfolio/:id`, then the item is updated
- [ ] Given a portfolio item owner, when they DELETE `/v1/portfolio/:id`, then the item is deleted
- [ ] Given any user, when they GET `/v1/portfolio?user_id=:id`, then all items for that user are returned ordered by created_at desc
- [ ] Given a non-owner trying to PUT or DELETE, then a 403 Forbidden is returned
- [ ] Given a portfolio item with `verified_gig_id` pointing to a COMPLETED gig, then `is_verified=true` is returned
- [ ] Given a portfolio item with `verified_gig_id` pointing to a non-COMPLETED gig, then `is_verified=false` is returned
- [ ] Given a portfolio item with no `verified_gig_id`, then `is_verified=false` is returned
- [ ] S3 presigned upload URL is returned when requested via `POST /v1/portfolio/presign`
- [ ] All endpoints return 401 if no valid token is provided
- [ ] Unit tests cover all domain logic (create, update, delete ownership, badge computation)
- [ ] E2E tests cover happy path for all four CRUD endpoints

---

## Technical Design

### Architecture Overview

```
Client
  │
  ▼
POST /v1/portfolio/presign     → returns S3 presigned URL (client uploads directly to S3)
POST /v1/portfolio             → creates portfolio item (with file_keys already in S3)
GET  /v1/portfolio?user_id=X   → lists portfolio items for user X
PUT  /v1/portfolio/:id         → updates portfolio item (owner only)
DELETE /v1/portfolio/:id       → deletes portfolio item (owner only)
  │
  ▼
domain/portfolio.py            → business logic (ownership checks, badge computation)
  │
  ▼
infra/database.py              → SQLAlchemy async ORM (PortfolioItemModel, GigModel)
infra/s3.py                    → boto3 presigned URL generation
```

### API Changes

#### New Endpoints

```
POST /v1/portfolio/presign
Authorization: Bearer <jwt>
Request:  { "filename": "screenshot.png", "content_type": "image/png" }
Response: { "upload_url": "<presigned S3 URL>", "key": "<S3 key>" }

POST /v1/portfolio
Authorization: Bearer <jwt>
Request: {
  "title": "E-commerce Platform",
  "description": "Full-stack Next.js + Stripe",
  "file_keys": ["uploads/abc123/screenshot.png"],
  "external_url": "https://github.com/user/project",
  "tags": ["nextjs", "stripe"],
  "verified_gig_id": "<uuid>"   // optional
}
Response: PortfolioItemResponse (see schema below)

GET /v1/portfolio?user_id=<uuid>
Authorization: Bearer <jwt>
Response: { "items": [PortfolioItemResponse, ...] }

PUT /v1/portfolio/:id
Authorization: Bearer <jwt>
Request: { "title": "...", "description": "...", ... }
Response: PortfolioItemResponse

DELETE /v1/portfolio/:id
Authorization: Bearer <jwt>
Response: PortfolioItemResponse (the deleted item)
```

#### PortfolioItemResponse schema

```json
{
  "id": "<uuid>",
  "user_id": "<uuid>",
  "title": "E-commerce Platform",
  "description": "...",
  "file_keys": ["..."],
  "external_url": "https://...",
  "tags": ["nextjs"],
  "verified_gig_id": "<uuid>|null",
  "is_verified": true,
  "created_at": "2026-03-07T00:00:00Z",
  "updated_at": "2026-03-07T00:00:00Z"
}
```

### Data Model Changes

#### New Tables

```sql
-- Minimal gigs table (extended by the gig feature issue)
CREATE TABLE gigs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status VARCHAR(50) NOT NULL DEFAULT 'GIG_STATUS_DRAFT',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE portfolio_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  file_keys JSONB NOT NULL DEFAULT '[]',
  external_url VARCHAR(2048) NOT NULL DEFAULT '',
  tags JSONB NOT NULL DEFAULT '[]',
  verified_gig_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_portfolio_items_user_id ON portfolio_items(user_id);
CREATE INDEX idx_portfolio_items_created_at ON portfolio_items(created_at DESC);
```

### Badge Logic

```python
# is_verified = True when:
#   1. verified_gig_id is set (not null)
#   2. The referenced gig exists AND gig.status == 'GIG_STATUS_COMPLETED'
def compute_is_verified(item: PortfolioItemModel, gig: GigModel | None) -> bool:
    if item.verified_gig_id is None:
        return False
    if gig is None:
        return False
    return gig.status == GigStatus.COMPLETED
```

---

## Security Considerations

- All endpoints require JWT or API key authentication (enforced by `require_auth` dependency)
- Ownership is verified server-side before any mutation: `item.user_id != auth["subject"]` → 403
- S3 keys in `file_keys` are not validated for existence (client is trusted to upload before submitting)
- `verified_gig_id` is accepted without validation at write time; badge is computed at read time
- Presigned URLs expire in 300 seconds; content-type is validated against allowed MIME types

---

## Observability

- **Logs**: INFO on item create/update/delete with item_id and user_id; no PII logged
- **Metrics**: Standard FastAPI request metrics via `/metrics` endpoint
- **Alerts**: None needed at this stage

---

## Testing Plan

### Unit Tests (`tests/unit/test_portfolio.py`)

- `test_create_portfolio_item_returns_item`
- `test_update_portfolio_item_checks_ownership`
- `test_delete_portfolio_item_checks_ownership`
- `test_compute_is_verified_with_completed_gig`
- `test_compute_is_verified_with_non_completed_gig`
- `test_compute_is_verified_with_no_gig_id`
- `test_compute_is_verified_with_missing_gig`

### E2E Tests (`tests/e2e/test_portfolio_api.py`)

- `test_create_portfolio_item_happy_path`
- `test_get_portfolio_items_for_user`
- `test_update_portfolio_item_by_owner`
- `test_delete_portfolio_item_by_owner`
- `test_update_portfolio_item_forbidden_for_non_owner`
- `test_portfolio_item_verified_badge`

---

## Migration / Rollout Plan

- **Database migrations**: Yes — creates `gigs` (minimal) and `portfolio_items` tables
- **Breaking changes**: No — new tables and endpoints only
- **Feature flag**: No
- **Rollback plan**: Run the down migration to drop both tables. No data loss risk at this stage.

---

## Open Questions

| Question                                           | Owner   | Status         |
| -------------------------------------------------- | ------- | -------------- |
| Should file_keys be validated against S3 on write? | Product | Deferred to v2 |

---

## References

- Related ADR: `docs/adr/0002-tech-stack.md`
- Proto: `packages/schema/proto/api/v1/portfolio.proto`
- Issue: #2
