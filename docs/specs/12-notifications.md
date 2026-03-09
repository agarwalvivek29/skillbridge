# Spec: In-App and Email Notifications

**Issue**: #12
**Status**: Approved
**Author**: agent
**Date**: 2026-03-09
**Services Affected**: api

---

## Summary

Add a notification system to the `api` service that supports in-app notifications (REST + SSE real-time stream) and email delivery. Notifications are created by existing domain functions (proposals, submissions, milestones, reviews) and surfaced to users via paginated REST endpoints and a Server-Sent Events stream for real-time bell updates.

---

## Background and Motivation

Users need to know when important events happen on their gigs: new proposals, submission received, milestone approved, funds released, etc. Without notifications, users must poll the UI manually. The frontend notification bell and notification center pages are already implemented (PR #60) and expect the API shapes defined in `notification.proto`.

---

## Scope

### In Scope

- Domain service: `notification.create()` helper for emitting notifications
- REST endpoints: GET /v1/notifications (paginated, with unread_count), POST /v1/notifications/{id}/read, POST /v1/notifications/read-all
- SSE endpoint: GET /v1/notifications/stream for real-time push
- Email delivery via SendGrid for key notification types
- Email preference opt-out per user (notification_preferences table)
- Unit tests for domain functions
- E2E tests for all notification endpoints

### Out of Scope

- Push notifications (mobile)
- WebSocket (SSE is sufficient for MVP)
- DISPUTE_RAISED / DISPUTE_RESOLVED trigger wiring (soft dependency on #9)
- REVIEW_RECEIVED trigger wiring (soft dependency on #11)

---

## Acceptance Criteria

- [x] GET /v1/notifications returns paginated notifications with unread_count
- [x] GET /v1/notifications supports `unread=true` query param to filter unread only
- [x] GET /v1/notifications/stream returns SSE events when new notifications are created
- [x] POST /v1/notifications/{id}/read marks a single notification as read
- [x] POST /v1/notifications/read-all marks all notifications for the user as read
- [x] All 14 NotificationType enum values are defined and handled
- [x] notification.create() is called from existing domain functions for all unblocked types
- [x] Email sending via SendGrid for key events (configurable, opt-out per user)
- [x] SENDGRID_API_KEY and SENDGRID_FROM_EMAIL added to .env.example
- [x] Unit tests for notification domain functions
- [x] E2E tests for notification endpoints

---

## Technical Design

### Architecture Overview

```
[domain functions] --create()--> [NotificationModel in DB]
                                       |
                                       v
[GET /v1/notifications]  <-- paginated query
[GET /v1/notifications/stream] <-- SSE poll loop
[POST /v1/notifications/{id}/read] --> update read_at
[POST /v1/notifications/read-all] --> bulk update read_at
```

Notification creation already happens inline in domain functions (proposal.py, submission.py, milestone_approval.py, review.py). This spec adds:

1. A centralized `notification.create()` domain helper
2. REST + SSE endpoints for reading/managing notifications
3. Email delivery as a side-effect of create()

### API Changes

#### New Endpoints

```
GET /v1/notifications?limit=20&offset=0&unread=false
Response: { notifications: [...], unread_count: int }

GET /v1/notifications/stream
Response: text/event-stream (SSE)

POST /v1/notifications/{notification_id}/read
Response: { notification: {...} }

POST /v1/notifications/read-all
Response: { notifications: [...], unread_count: 0 }
```

### Data Model Changes

No new tables needed -- `notifications` table already exists (migration 0004).

A `notification_preferences` table will store per-user email opt-out preferences.

### Dependencies

- `sendgrid` Python package for email delivery

---

## Security Considerations

- All notification endpoints require JWT auth
- Users can only access their own notifications (user_id from JWT)
- SSE stream requires auth token as query param (EventSource limitation)
- No sensitive data in notification payloads (no passwords, tokens, etc.)

---

## Testing Plan

### Unit Tests

- `test_notification_domain.py`: create(), list, mark_read, mark_all_read

### E2E Tests

- `test_notification_api.py`: all 4 endpoints + SSE stream

---

## References

- Proto: `packages/schema/proto/api/v1/notification.proto`
- Frontend: PR #60 (notification bell + center pages)
- Related issues: #9 (disputes), #11 (ratings)
