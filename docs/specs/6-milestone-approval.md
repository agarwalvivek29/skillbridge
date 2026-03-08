# Spec: Milestone Approval and Automatic Fund Release

**Issue**: #6
**Status**: Approved
**Author**: agarwalvivek29
**Date**: 2026-03-08
**Services Affected**: `services/api`

---

## Summary

After a milestone is approved — either automatically by the AI reviewer (issue #7) or manually by the client — the smart contract releases the net milestone amount to the freelancer's wallet. This spec covers the manual approval/revision endpoints and the on-chain fund release preparation and confirmation flow.

---

## Background and Motivation

Milestone approval is the core payment trigger on SkillBridge. Without it, clients have no way to manually review and approve work, and the on-chain escrow cannot be released. This feature closes the loop between work submission (issue #5) and payment (on-chain escrow from issue #4).

---

## Scope

### In Scope

- `POST /v1/milestones/{id}/approve` — manual client approval
- `POST /v1/milestones/{id}/request-revision` — client requests changes
- `GET /v1/milestones/{id}/release-tx` — return ABI-encoded calldata for `completeMilestone(index)`
- `POST /v1/milestones/{id}/confirm-release` — record tx_hash after client broadcasts
- `PAID` milestone status added to DB model and migration
- `release_tx_hash` column added to `escrow_contracts` table (migration 0007)
- Notifications for freelancer on all state transitions
- Dispute guard: 409 if milestone is DISPUTED

### Out of Scope

- Dispute raising/resolution (issue #9)
- AI auto-approval webhook (issue #7)
- Broadcasting the transaction server-side (client's browser signs via wagmi)

---

## Acceptance Criteria

- [ ] Given CLIENT role and milestone in UNDER_REVIEW or APPROVED status, when POST /approve, then milestone → APPROVED and notification created for freelancer
- [ ] Given CLIENT role and milestone in UNDER_REVIEW, when POST /request-revision with reason, then milestone → REVISION_REQUESTED and notification created
- [ ] Given CLIENT role and milestone APPROVED, when GET /release-tx, then returns contract_address, milestone_index, calldata, chain_id
- [ ] Given CLIENT role and milestone APPROVED, when POST /confirm-release with tx_hash, then milestone → PAID and notification created
- [ ] Given milestone is DISPUTED, when POST /approve or GET /release-tx, then 409 MILESTONE_DISPUTED
- [ ] Given non-CLIENT role, all four endpoints return 403

---

## Technical Design

### Architecture Overview

The flow is:

1. Client calls `POST /approve` → milestone marked APPROVED in DB
2. Client calls `GET /release-tx` → API returns ABI-encoded calldata for `GigEscrow.completeMilestone(index)`
3. Client's browser (wagmi/viem) signs and broadcasts the tx
4. Client calls `POST /confirm-release` with tx_hash → milestone marked PAID, tx_hash stored

No server-side private key management. The API never broadcasts transactions.

### API Changes

#### New Endpoints

```
POST /v1/milestones/{milestone_id}/approve
Request: {}
Response: { id, gig_id, status, order, ... }

POST /v1/milestones/{milestone_id}/request-revision
Request: { reason: string }
Response: { id, gig_id, status, order, ... }

GET /v1/milestones/{milestone_id}/release-tx
Response: {
  contract_address: string,
  milestone_index: int,    # 0-indexed (order - 1)
  chain_id: int,
  calldata: string         # 0x + hex(selector + abi-encoded uint256)
}

POST /v1/milestones/{milestone_id}/confirm-release
Request: { tx_hash: string }
Response: { id, gig_id, status, ... }
```

### Data Model Changes

#### New column on escrow_contracts table (migration 0007)

```sql
ALTER TABLE escrow_contracts ADD COLUMN release_tx_hash TEXT;
```

#### MilestoneModel status comment update

Add `PAID` to the status comment on `MilestoneModel`.

### Calldata Generation

For `completeMilestone(uint256 index)`:

- Selector: `0x5a36fb08` (keccak256("completeMilestone(uint256)")[:4])
- ABI-encode index as 32-byte big-endian uint256
- Total: 36 bytes hex with `0x` prefix

Pure Python — no web3 dependency required.

---

## Security Considerations

- All four endpoints require CLIENT role
- Caller must be the gig's client_id (not just any CLIENT-role user)
- Dispute guard prevents fund release when milestone is actively disputed
- tx_hash is stored but not verified on-chain (v1 limitation; trust client's claim)

---

## Observability

- **Logs**: INFO on each status transition with milestone_id and new status
- **Logs**: WARNING if EscrowContractModel not found during confirm-release

---

## Testing Plan

### Unit Tests

- `test_milestone_approval_domain.py` covering all transitions and error paths

### Integration Tests

- `test_milestone_approval_api.py` covering all four endpoints

### Manual Testing Steps

1. Create gig with milestone, assign freelancer, submit work
2. Client calls approve → check milestone.status == APPROVED
3. Client calls release-tx → verify calldata format
4. Client calls confirm-release → check milestone.status == PAID

---

## Migration / Rollout Plan

- **Database migrations**: Yes — migration 0007 adds `release_tx_hash` to `escrow_contracts`
- **Breaking changes**: No
- **Feature flag**: No
- **Rollback plan**: Run migration 0007 downgrade to remove the column

---

## References

- Related issues: #4 (escrow contract), #5 (work submission), #7 (AI review), #9 (disputes)
- Contract: `services/contracts/src/GigEscrow.sol` — `completeMilestone(uint256)`
