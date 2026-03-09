# Spec: On-Chain Reputation Contract

**Issue**: #10
**Status**: Approved
**Author**: team
**Date**: 2026-03-09
**Services Affected**: contracts, api

---

## Summary

Implement an on-chain Reputation contract that aggregates per-address stats (gigs completed, total earned, average AI score) updated on every `completeMilestone` event from GigEscrow. Provide a DB cache in the api service with a `GET /v1/reputation/{wallet_address}` endpoint for fast reads, synced from chain via background job.

---

## Background and Motivation

On-chain reputation is a core differentiator for SkillBridge: verified completion history is portable and cannot be faked. Without it, freelancers have no way to prove track record across platforms, and clients lack an objective quality signal. The Reputation contract stores immutable stats on Base L2, while the api service caches them in PostgreSQL for sub-second reads.

---

## Scope

### In Scope

- Solidity `Reputation` contract: stores per-address gigs_completed, total_earned, average_ai_score
- Updated automatically when GigEscrow emits `FundsReleased` (via factory relay)
- Public view functions for external reads
- DB migration `0008` for `reputation` table in api service
- `GET /v1/reputation/{wallet_address}` endpoint (auth required)
- Domain logic for get/upsert reputation
- Unit tests for domain functions
- E2E tests for the API endpoint
- Foundry tests for the Solidity contract

### Out of Scope

- Background sync job polling on-chain events (deferred to integration phase)
- average_rating_x100 and rating_count updates (handled by #11 ratings)
- Dispute rate calculation (handled when disputes data is available)

---

## Acceptance Criteria

- [ ] Reputation.sol stores gigs_completed, total_earned, average_ai_score per address
- [ ] Only authorized caller (factory/escrow) can update reputation
- [ ] Public view functions return per-address stats
- [ ] DB `reputation` table exists with all proto fields
- [ ] GET /v1/reputation/{wallet_address} returns reputation data or 404
- [ ] Unit tests cover domain logic (get, upsert)
- [ ] E2E tests cover the API endpoint
- [ ] Foundry tests cover the Solidity contract with fuzz tests

---

## Technical Design

### Architecture Overview

```
[GigEscrow] --completeMilestone()--> emits FundsReleased
[Reputation.sol] <-- updated by factory owner / oracle
[api] GET /v1/reputation/{wallet} --> reads from PostgreSQL cache
[api background job] polls chain events --> upserts reputation table
```

### API Changes

#### New Endpoints

```
GET /v1/reputation/{wallet_address}
Response: { reputation: { id, user_id, wallet_address, gigs_completed, ... } }
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE reputation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  wallet_address TEXT NOT NULL UNIQUE,
  gigs_completed INTEGER NOT NULL DEFAULT 0,
  gigs_as_client INTEGER NOT NULL DEFAULT 0,
  total_earned TEXT NOT NULL DEFAULT '0',
  average_ai_score INTEGER NOT NULL DEFAULT 0,
  dispute_rate_pct INTEGER NOT NULL DEFAULT 0,
  average_rating_x100 INTEGER NOT NULL DEFAULT 0,
  rating_count INTEGER NOT NULL DEFAULT 0,
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Security Considerations

- Reputation contract updates restricted to authorized caller only
- API endpoint requires authentication
- Wallet address validated as proper hex format

---

## Testing Plan

### Unit Tests

- domain/reputation.py: get_reputation, upsert_reputation

### Integration Tests

- E2E: GET /v1/reputation/{wallet_address} happy path + 404

### Foundry Tests

- Reputation.sol: record updates, access control, view functions, fuzz tests

---

## References

- Related issues: #4 (escrow contracts), #11 (ratings)
- Proto: `packages/schema/proto/api/v1/reputation.proto`
