# Spec: Freelancer Portfolio with Verified Delivery Badges

**Issue**: #2
**Status**: Approved
**Author**: agent
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Freelancers can add portfolio items (title, description, files, external URL, tags) to their profile. Items linked to a completed on-chain gig automatically display a "Verified Delivery" badge. This is a core differentiator: verified on-chain completion history that cannot be faked.

---

## Background and Motivation

Freelancers cannot get hired without showcasing their work. The "Verified Delivery" badge is SkillBridge's key differentiator from every other portfolio system — it proves that the deliverable was accepted by a real client and paid through a trustless smart contract escrow. Without this feature, the platform has no trust advantage over a LinkedIn profile.

---

## Scope

### In Scope

- CRUD endpoints for portfolio items: `POST /v1/portfolio`, `GET /v1/portfolio/{item_id}`, `PUT /v1/portfolio/{item_id}`, `DELETE /v1/portfolio/{item_id}`
- Public listing endpoint: `GET /v1/users/{user_id}/portfolio` (returns all items for a user, ordered by `created_at DESC`)
- S3 presigned URL endpoint: `POST /v1/portfolio/upload-url` (direct browser upload; API never receives file bytes)
- Badge logic: `is_verified` field on each response item — `true` when `verified_gig_id` is set AND the linked gig has status `GIG_STATUS_COMPLETED` in the DB
- Only the owner can create, update, or delete their own portfolio items
- Unit tests for all domain functions
- E2E tests for all new API endpoints

### Out of Scope

- Frontend portfolio page (tracked in web service, future issue)
- On-chain badge minting / NFT (future phase)
- Public portfolio discovery / search across all freelancers (future issue)
- Gig CRUD endpoints (Issue #3)

---

## Acceptance Criteria

- [ ] Given an authenticated freelancer, when POST /v1/portfolio is called with valid data, then a portfolio item is created and returned with `is_verified: false`
- [ ] Given an authenticated user, when GET /v1/portfolio/{item_id} is called, then the item is returned with correct `is_verified` flag
- [ ] Given an authenticated owner, when PUT /v1/portfolio/{item_id} is called with updated data, then the item is updated
- [ ] Given an authenticated non-owner, when PUT or DELETE /v1/portfolio/{item_id} is called, then 403 is returned
- [ ] Given an authenticated owner, when DELETE /v1/portfolio/{item_id} is called, then the item is deleted
- [ ] Given any authenticated user, when GET /v1/users/{user_id}/portfolio is called, then all items for that user are returned ordered by `created_at DESC`
- [ ] Given a portfolio item with `verified_gig_id` pointing to a gig with status `GIG_STATUS_COMPLETED`, when the item is fetched, then `is_verified: true`
- [ ] Given a portfolio item with `verified_gig_id` pointing to a non-completed gig, when the item is fetched, then `is_verified: false`
- [ ] Given a portfolio item with no `verified_gig_id`, when the item is fetched, then `is_verified: false`
- [ ] Given an authenticated user, when POST /v1/portfolio/upload-url is called with a valid filename, then a presigned S3 PUT URL is returned
- [ ] All mutating endpoints require JWT or API key authentication

---

## Technical Design

### Architecture Overview

```
Browser
  │  POST /v1/portfolio/upload-url → get presigned S3 PUT URL
  │  PUT directly to S3 (presigned URL, file never touches API)
  │  POST /v1/portfolio (with file_keys from S3)
  │  GET /v1/users/{user_id}/portfolio
  ▼
FastAPI (api service)
  │  portfolio router → domain/portfolio.py → infra/models.py
  │  badge logic: join portfolio item with gig status in DB
  ▼
PostgreSQL
  - portfolio_items table
  - gigs table (future, referenced by verified_gig_id)
```

### API Changes

#### New Endpoints

```
POST /v1/portfolio
Authorization: Bearer <jwt>
Request: {
  title: str (required),
  description: str (optional),
  file_keys: list[str] (optional, S3 keys),
  external_url: str (optional),
  tags: list[str] (optional),
  verified_gig_id: str (optional)
}
Response 201: {
  id: str,
  user_id: str,
  title: str,
  description: str,
  file_keys: list[str],
  external_url: str,
  tags: list[str],
  verified_gig_id: str | null,
  is_verified: bool,
  created_at: str (ISO-8601),
  updated_at: str (ISO-8601)
}

GET /v1/portfolio/{item_id}
Authorization: Bearer <jwt>
Response 200: PortfolioItemResponse

PUT /v1/portfolio/{item_id}
Authorization: Bearer <jwt> (owner only)
Request: {
  title: str (optional),
  description: str (optional),
  file_keys: list[str] (optional),
  external_url: str (optional),
  tags: list[str] (optional)
}
Response 200: PortfolioItemResponse

DELETE /v1/portfolio/{item_id}
Authorization: Bearer <jwt> (owner only)
Response 204: no content

GET /v1/users/{user_id}/portfolio
Authorization: Bearer <jwt>
Response 200: { items: list[PortfolioItemResponse] }

POST /v1/portfolio/upload-url
Authorization: Bearer <jwt>
Request: { filename: str, content_type: str }
Response 200: { upload_url: str, s3_key: str }
```

### Data Model Changes

#### New Table: portfolio_items

```sql
CREATE TABLE portfolio_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  file_keys TEXT[] NOT NULL DEFAULT '{}',
  external_url TEXT,
  tags TEXT[] NOT NULL DEFAULT '{}',
  verified_gig_id TEXT,  -- references gigs.id, nullable, no FK enforced in v1 (gigs table doesn't exist yet)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_portfolio_items_user_id ON portfolio_items(user_id);
```

### Badge Logic

`is_verified` is computed at query time:

1. If `verified_gig_id` is null or empty → `is_verified = False`
2. If `verified_gig_id` is set, query `gigs` table for `status == 'GIG_STATUS_COMPLETED'`
3. Since the `gigs` table does not exist in v1, the badge check returns `False` if the gig is not found — safe default
4. `is_verified` is never stored in the DB; it is always computed on read

### S3 Presigned URL

- `POST /v1/portfolio/upload-url` generates a presigned PUT URL using boto3
- Key format: `portfolio/{user_id}/{uuid4}-{sanitized_filename}`
- URL expires in 300 seconds
- If `AWS_ACCESS_KEY_ID` is empty (local dev), return a mock URL with a warning

### Queue / Event Changes

None for v1. Portfolio creation is synchronous.

### Dependencies

No new packages. boto3, SQLAlchemy, FastAPI are already in the dependency list.

---

## Security Considerations

- All endpoints require authentication (JWT or API key)
- Owner check: on PUT/DELETE, compare `request.state.user_id` with `item.user_id`; return 403 if mismatch
- `verified_gig_id` is accepted from the client but the badge is computed server-side — client cannot self-issue badges
- S3 keys are validated to prevent path traversal (no `..` allowed)
- Presigned URL filename is sanitized before use as S3 key

---

## Observability

- **Logs**: INFO on item create/update/delete (log item_id, user_id, operation); INFO on presigned URL generation (log user_id, s3_key)
- **Metrics**: None additional for MVP
- **Alerts**: None for MVP

---

## Testing Plan

### Unit Tests (`tests/unit/test_portfolio.py`)

- `test_compute_is_verified_no_gig_id` — returns False when verified_gig_id is None
- `test_compute_is_verified_gig_not_found` — returns False when gig_id set but gig not in DB
- `test_compute_is_verified_gig_completed` — returns True when gig status is COMPLETED
- `test_compute_is_verified_gig_not_completed` — returns False when gig status is IN_PROGRESS
- `test_sanitize_s3_key` — verifies key generation for presigned URL

### E2E Tests (`tests/e2e/test_portfolio.py`)

- `TestCreatePortfolioItem` — happy path create, auth required, title required
- `TestGetPortfolioItem` — happy path get, not found returns 404
- `TestUpdatePortfolioItem` — owner can update, non-owner gets 403
- `TestDeletePortfolioItem` — owner can delete, non-owner gets 403, not found returns 404
- `TestGetUserPortfolio` — returns items ordered by created_at DESC
- `TestGetPresignedUrl` — returns upload_url and s3_key

### Manual Testing Steps

1. Register as a freelancer, obtain JWT
2. POST /v1/portfolio with title + description → verify 201 and `is_verified: false`
3. POST /v1/portfolio/upload-url → verify presigned URL structure
4. GET /v1/users/{user_id}/portfolio → verify item appears
5. PUT /v1/portfolio/{item_id} → verify update
6. Register as a second user → attempt PUT /v1/portfolio/{item_id} → verify 403
7. DELETE /v1/portfolio/{item_id} as owner → verify 204

---

## Migration / Rollout Plan

- **Database migrations**: Yes — new `portfolio_items` table. Migration file: `0002_create_portfolio_items.py`
- **Breaking changes**: No
- **Feature flag**: No
- **Rollback plan**: `alembic downgrade 0001` drops `portfolio_items` table. No data loss to existing users.

---

## Open Questions

| Question                                         | Owner | Status                                                                           |
| ------------------------------------------------ | ----- | -------------------------------------------------------------------------------- |
| Should `verified_gig_id` be enforced by a DB FK? | agent | Resolved: No FK in v1 since `gigs` table doesn't exist yet. Soft reference only. |

---

## References

- Related ADR: [ADR 0002](../adr/0002-tech-stack.md)
- Related issues: #1 (auth, completed), #3 (gig creation, future)
- Proto: `packages/schema/proto/api/v1/portfolio.proto`
