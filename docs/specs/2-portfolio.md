# Spec: Freelancer Portfolio with Verified Delivery Badges

**Issue**: #2
**Status**: Approved
**Author**: ao
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Freelancers can create and manage portfolio items showcasing their work. Items optionally link to
a completed on-chain gig and automatically display a "Verified Delivery" badge — the core trust
differentiator that separates SkillBridge from every other portfolio site.

---

## Background and Motivation

Trust is the hardest problem in freelancing. Portfolios today are self-reported and unverifiable.
SkillBridge solves this by anchoring portfolio items to completed, on-chain escrow gigs. If a
freelancer delivered work that was approved and funds released on-chain, the badge appears
automatically — no admin approval, no manual process.

Without this feature, the profile page is empty and the platform has no way to differentiate
freelancers beyond self-description.

---

## Scope

### In Scope

- CRUD operations on `PortfolioItem` (create, read, update, delete)
- Role-restricted creation (FREELANCER only)
- Owner-only edit/delete
- S3 presigned PUT URL generation for direct browser-to-S3 file uploads
- "Verified Delivery" badge logic: `verified_gig_id` is set AND linked gig status is `COMPLETED`
- Public GET endpoint (`GET /v1/portfolio/{user_id}`) returns items ordered by `created_at DESC`
  with `is_verified` flag computed per item
- `GET /v1/users/{user_id}` profile already returns `skills[]` and `hourly_rate_wei`

### Out of Scope

- Frontend rendering of badges (Issue: web/profile page — future)
- Pagination of portfolio items (users are unlikely to exceed 20 items at MVP scale)
- AI review of portfolio content
- Social sharing or public embed cards

---

## Acceptance Criteria

- [ ] Given an authenticated FREELANCER, when `POST /v1/portfolio` is called with valid data,
      then a portfolio item is created and returned with `is_verified: false`.
- [ ] Given an authenticated CLIENT, when `POST /v1/portfolio` is called, then `403 FORBIDDEN`
      is returned.
- [ ] Given an unauthenticated request, when `POST /v1/portfolio` is called, then `401` is returned.
- [ ] Given an authenticated FREELANCER owner, when `PUT /v1/portfolio/{item_id}` is called,
      then the item is updated and returned.
- [ ] Given a non-owner authenticated user, when `PUT /v1/portfolio/{item_id}` is called,
      then `403 FORBIDDEN` is returned.
- [ ] Given an authenticated owner, when `DELETE /v1/portfolio/{item_id}` is called,
      then the item is deleted and `204` is returned.
- [ ] Given any caller (unauthenticated or authenticated), when `GET /v1/portfolio/{user_id}`
      is called, then portfolio items for that user are returned ordered by `created_at DESC`.
- [ ] Given a portfolio item linked to a gig with status `COMPLETED`, when the item is returned,
      then `is_verified: true` is present in the response.
- [ ] Given a portfolio item linked to a gig with status != `COMPLETED` (e.g., `IN_PROGRESS`),
      when the item is returned, then `is_verified: false` is present.
- [ ] Given a portfolio item with no `verified_gig_id`, when the item is returned, then
      `is_verified: false` is present.
- [ ] Given an authenticated FREELANCER, when `POST /v1/portfolio/upload-url` is called with a
      valid `content_type`, then a presigned S3 PUT URL and `key` are returned.
- [ ] File keys included at create time are stored and returned in GET responses.

---

## Technical Design

### Architecture Overview

```
Browser
  │  1. POST /v1/portfolio/upload-url  → { url, key }
  │  2. PUT <presigned S3 url>  (direct to S3, bypasses API)
  │  3. POST /v1/portfolio  { ..., file_keys: [key] }
  ▼
[api — FastAPI]
  ├── GET  /v1/portfolio/{user_id}          (public)
  ├── POST /v1/portfolio                    (FREELANCER auth)
  ├── POST /v1/portfolio/upload-url         (FREELANCER auth)
  ├── PUT  /v1/portfolio/{item_id}          (auth + owner)
  └── DELETE /v1/portfolio/{item_id}        (auth + owner)
  │
  ├── PostgreSQL: portfolio_items table
  │     LEFT JOIN gigs ON verified_gig_id = gigs.id
  │     is_verified = (verified_gig_id IS NOT NULL AND gig.status = 'COMPLETED')
  └── S3: boto3 presigned PUT URL (ExpiresIn=300s)
```

### API Changes

#### New Endpoints

```
GET /v1/portfolio/{user_id}
  Auth: none (public)
  Response: { items: PortfolioItemOut[] }

POST /v1/portfolio
  Auth: Bearer JWT (FREELANCER role)
  Request: CreatePortfolioItemRequest
  Response: PortfolioItemOut  (201)

POST /v1/portfolio/upload-url
  Auth: Bearer JWT (FREELANCER role)
  Request: { content_type: string }
  Response: { url: string, key: string }  (200)

PUT /v1/portfolio/{item_id}
  Auth: Bearer JWT (owner only)
  Request: UpdatePortfolioItemRequest (title, description, file_keys, external_url, tags)
  Response: PortfolioItemOut  (200)

DELETE /v1/portfolio/{item_id}
  Auth: Bearer JWT (owner only)
  Response: 204 No Content
```

#### Modified Endpoints

None.

### Data Model Changes

#### New Tables

```sql
CREATE TABLE portfolio_items (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title           TEXT         NOT NULL,
  description     TEXT         NOT NULL,
  file_keys       TEXT[]       NOT NULL DEFAULT '{}',
  external_url    TEXT,
  tags            TEXT[]       NOT NULL DEFAULT '{}',
  verified_gig_id UUID         REFERENCES gigs(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_portfolio_items_user_id ON portfolio_items(user_id);
```

#### Badge Computation (SQL)

```sql
SELECT
  pi.*,
  (pi.verified_gig_id IS NOT NULL AND g.status = 'COMPLETED') AS is_verified
FROM portfolio_items pi
LEFT JOIN gigs g ON pi.verified_gig_id = g.id
WHERE pi.user_id = :user_id
ORDER BY pi.created_at DESC;
```

### Queue / Event Changes

None.

### Dependencies

- `boto3>=1.34.0` — S3 presigned URL generation (add to `pyproject.toml`)

---

## Security Considerations

- All mutation endpoints (POST/PUT/DELETE) require valid JWT.
- `POST /v1/portfolio` requires FREELANCER role (prevents clients from creating portfolios).
- `PUT` and `DELETE` verify that the requesting user owns the item (`user_id == request.state.user_id`).
- Presigned URL generation requires FREELANCER auth so unauthenticated users can't generate upload
  tokens.
- S3 keys are server-generated (UUID-based), never client-supplied, preventing path traversal.
- `verified_gig_id` is checked against the DB — clients cannot fake a Verified badge by passing an
  arbitrary gig ID (the badge is computed server-side from the gig's actual `status`).
- `GET /v1/portfolio/{user_id}` is intentionally public to allow profile pages without auth.

---

## Observability

- **Logs**: `INFO` log on create/update/delete with `item_id` and `user_id`. `INFO` on presigned URL generation with `key`.
- **Metrics**: No new metrics at MVP scale.
- **Alerts**: None at MVP scale.

---

## Testing Plan

### Unit Tests (`tests/unit/test_portfolio_domain.py`)

- `create_portfolio_item` happy path
- `create_portfolio_item` with `verified_gig_id` that links to a COMPLETED gig → `is_verified: true`
- `get_portfolio_items` returns items ordered by `created_at DESC`
- `get_portfolio_items` badge computation (COMPLETED vs non-COMPLETED vs no gig)
- `update_portfolio_item` happy path
- `update_portfolio_item` forbidden for non-owner
- `update_portfolio_item` not found
- `delete_portfolio_item` happy path
- `delete_portfolio_item` forbidden for non-owner
- `delete_portfolio_item` not found

### Integration Tests (`tests/e2e/test_portfolio_api.py`)

- `POST /v1/portfolio` — freelancer creates item
- `POST /v1/portfolio` — client gets 403
- `POST /v1/portfolio` — unauthenticated gets 401
- `GET /v1/portfolio/{user_id}` — returns items ordered by created_at
- `GET /v1/portfolio/{user_id}` — no auth needed
- `GET /v1/portfolio/{user_id}` — unknown user returns empty list
- `PUT /v1/portfolio/{item_id}` — owner updates item
- `PUT /v1/portfolio/{item_id}` — non-owner gets 403
- `DELETE /v1/portfolio/{item_id}` — owner deletes item
- `DELETE /v1/portfolio/{item_id}` — non-owner gets 403
- `POST /v1/portfolio/upload-url` — freelancer gets presigned URL (boto3 mocked)
- `POST /v1/portfolio/upload-url` — unauthenticated gets 401

---

## Migration / Rollout Plan

- **Database migrations**: Yes — `0003_create_portfolio_items` creates the `portfolio_items` table
  and index. Backwards compatible (additive only).
- **Breaking changes**: No.
- **Feature flag**: No.
- **Rollback plan**: `alembic downgrade 0002` drops the `portfolio_items` table. No data loss
  to existing tables.

---

## Open Questions

| Question                                        | Owner | Status                                          |
| ----------------------------------------------- | ----- | ----------------------------------------------- |
| Should update allow changing `verified_gig_id`? | ao    | Closed — No, badge link is set at creation only |

---

## References

- Proto: `packages/schema/proto/api/v1/portfolio.proto`
- Related issue: #2
- AGENTS.md: `services/api/AGENTS.md`
