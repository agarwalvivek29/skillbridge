# Spec: Blind Mutual Ratings and Reviews

**Issue**: #11
**Status**: Approved
**Author**: agent-ratings
**Date**: 2026-03-09
**Services Affected**: api

---

## Summary

Implement a blind mutual rating system where both client and freelancer rate each other after a gig completes. Reviews are hidden until both parties submit or a 7-day window closes, preventing retaliation bias.

---

## Background and Motivation

Ratings are essential for marketplace trust. A blind-reveal system prevents the common problem where the second rater retaliates based on seeing the first rating. Each completed gig produces exactly 2 Review records: client rates freelancer and freelancer rates client.

---

## Scope

### In Scope

- `POST /v1/gigs/{gig_id}/review` -- create a review (auth required, gig participant)
- `GET /v1/gigs/{gig_id}/reviews` -- list reviews for a gig (visible only)
- `GET /v1/users/{user_id}/reviews` -- list all visible reviews for a user profile
- Blind-reveal logic: `is_visible = false` until both submit OR 7-day window closes
- `ReviewModel` DB table and migration
- Reputation update (guarded -- try/except if reputation table absent)
- Notification hook for REVIEW_RECEIVED

### Out of Scope

- Editing or deleting reviews after submission
- Admin moderation of reviews
- Review disputes

---

## Acceptance Criteria

- [x] Given a COMPLETED gig, when the client submits a review, then a Review record is created with is_visible=false
- [x] Given both client and freelancer have submitted reviews for a gig, then both reviews become is_visible=true
- [x] Given only one party submits and 7 days pass, then GET endpoints treat the review as visible (checked at read time)
- [x] Given a user tries to review a gig they are not a participant of, then 403 is returned
- [x] Given a user tries to review a non-COMPLETED gig, then 409 is returned
- [x] Given a user tries to submit a second review for the same gig, then 409 is returned
- [x] Given rating is outside 1-5, then 422 is returned
- [x] reviewer_id and reviewee_id are inferred server-side from JWT + gig roles

---

## Technical Design

### API Changes

#### New Endpoints

```
POST /v1/gigs/{gig_id}/review
Auth: required (JWT)
Request: { "rating": 4, "comment": "Great work!" }
Response: 201 { "id", "gig_id", "reviewer_id", "reviewee_id", "rating", "comment", "is_visible", "created_at" }

GET /v1/gigs/{gig_id}/reviews
Auth: required (JWT)
Response: 200 { "reviews": [...], "average_rating_x100": 450 }

GET /v1/users/{user_id}/reviews
Auth: none (public)
Response: 200 { "reviews": [...], "average_rating_x100": 450 }
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE reviews (
  id UUID PRIMARY KEY,
  gig_id UUID NOT NULL REFERENCES gigs(id),
  reviewer_id UUID NOT NULL REFERENCES users(id),
  reviewee_id UUID NOT NULL REFERENCES users(id),
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment TEXT NOT NULL DEFAULT '',
  is_visible BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (gig_id, reviewer_id)
);
```

### Dependencies

- Soft dependency on #10 (reputation table) for updating average_rating_x100
- Soft dependency on #12 (notifications) for REVIEW_RECEIVED notification

---

## Security Considerations

- reviewer_id inferred from JWT (never from request body)
- reviewee_id inferred from gig roles (never from request body)
- Only gig participants can submit reviews
- Reviews only allowed for COMPLETED gigs

---

## Testing Plan

### Unit Tests

- Blind-reveal: both submit -> both visible
- Blind-reveal: only one submits -> not visible
- 7-day window logic
- Duplicate review rejection
- Non-participant rejection
- Non-completed gig rejection

### Integration Tests (E2E)

- POST /v1/gigs/{gig_id}/review happy path
- GET /v1/gigs/{gig_id}/reviews with blind reveal
- GET /v1/users/{user_id}/reviews
- Auth and role checks

---

## Migration / Rollout Plan

- **Database migrations**: yes -- new `reviews` table (migration 0010)
- **Breaking changes**: no
- **Rollback plan**: drop `reviews` table

---

## References

- Related issues: #10 (reputation), #12 (notifications)
- Proto: `packages/schema/proto/api/v1/review.proto`
