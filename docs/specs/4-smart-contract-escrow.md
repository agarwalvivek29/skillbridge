# Spec: Smart Contract Escrow on Solana

**Issue**: #4
**Status**: Approved
**Date**: 2026-03-13
**Services Affected**: `services/contracts`, `services/api`

---

## Summary

Deploy a `gig_escrow` Anchor program on Solana to enable trustless fund locking and per-milestone release for SkillBridge gigs. Supports both native SOL and SPL token (USDC) payment. A 5% platform fee (500 basis points) is deducted from each milestone payout and sent to the platform fee recipient. Uses PDAs (Program Derived Addresses) to derive per-gig escrow accounts deterministically — no factory contract needed.

---

## Background and Motivation

SkillBridge's core value proposition is trustless escrow — neither the client nor the freelancer needs to trust each other; the smart contract enforces payment. Without this contract layer, SkillBridge is just another centralized marketplace. This is the foundation every other feature (work submission, milestone approval, dispute resolution) depends on.

The migration from Base L2 (Solidity/Foundry) to Solana (Rust/Anchor) is documented in [ADR 0003](../adr/0003-solana-migration.md). Key motivations: free devnet tokens unblock development, PDA pattern is simpler than factory pattern, sub-second finality improves UX, and team Rust expertise aligns.

---

## Scope

### In Scope

- `gig_escrow` Anchor program — a single deployed program managing all escrow accounts via PDAs
- PDA derivation: escrow account PDA derived from seeds `[b"escrow", gig_id.to_le_bytes()]`
- Support for SOL (native) and SPL token (USDC) deposits
- Platform fee (configurable basis points, default 500 = 5%) deducted on each milestone payout
- `initialize_escrow` — creates PDA escrow account for a gig; sets client, freelancer, token mint, milestone amounts, fee config
- `deposit` — client locks total budget into escrow PDA; emits `EscrowFunded` event
- `complete_milestone(index)` — releases net amount to freelancer + fee to platform; emits `FundsReleased` event
- `raise_dispute(index)` — locks a milestone pending arbitration; emits `DisputeRaised` event
- `resolve_dispute(index, resolution, freelancer_split_amount)` — arbitrator resolves with PayFreelancer, RefundClient, or Split outcome
- Emergency withdrawal (requires both client + freelancer to sign `sign_emergency_withdrawal` before `emergency_withdraw` executes)
- Anchor tests covering all fund-handling paths (SOL and SPL token)
- IDL export to `services/contracts/target/idl/` for consumption by `services/api` via `anchorpy` or `solana-py`

### Out of Scope

- Deployment to mainnet-beta (requires explicit human approval)
- On-chain dispute arbitration voting (v1 is off-chain + arbitrator public key)
- Integration with `services/api` Solana client (Issue #6)
- Frontend wallet interactions (Issue #3 + Issue #5)

---

## Acceptance Criteria

- [ ] `gig_escrow` program initializes an escrow PDA per gig, storing client + freelancer public keys, `token_mint` (system program for SOL, SPL mint address for USDC), milestone amounts[], and `platform_fee_basis_points` (500 = 5%)
- [ ] Client calls `deposit` to lock total budget into escrow PDA; program emits `EscrowFunded` event
- [ ] `complete_milestone(index)` releases milestone amount minus platform fee to freelancer; fee goes to `platform_fee_recipient`; emits `FundsReleased { net_amount, platform_fee_amount }`
- [ ] `raise_dispute(index)` locks the milestone pending arbitration; emits `DisputeRaised`
- [ ] `resolve_dispute(index, resolution, freelancer_split_amount)` handles PayFreelancer, RefundClient, or Split outcomes
- [ ] Emergency withdrawal requires both client + freelancer to call `sign_emergency_withdrawal` before `emergency_withdraw` executes
- [ ] All fund-handling instructions covered by Anchor tests for both SOL and SPL token paths
- [ ] `anchor test` passes with zero failures
- [ ] IDL exported to `services/contracts/target/idl/gig_escrow.json`

---

## Technical Design

### Architecture Overview

```
[api service — solana-py / anchorpy]
    │  initialize_escrow(client, freelancer, token_mint, milestone_amounts, fee_bps)
    ▼
[gig_escrow program] ── derives PDA ──▶ [Escrow PDA #1 (seeds: "escrow" + gig_id)]
                                         [Escrow PDA #2 (seeds: "escrow" + gig_id)]
                                         [Escrow PDA #N (seeds: "escrow" + gig_id)]
    │
    │  complete_milestone(index)  ◀── called by api after client approves
    │  raise_dispute(index)       ◀── called by api when dispute raised
    │  resolve_dispute(...)       ◀── called by api (arbitrator) after resolution
    ▼
[Freelancer wallet] ← net_amount (SOL or SPL token)
[Platform fee recipient] ← platform_fee_amount
```

### Anchor Instruction Signatures

#### initialize_escrow

```rust
pub fn initialize_escrow(
    ctx: Context<InitializeEscrow>,
    gig_id: u64,
    milestone_amounts: Vec<u64>,
    platform_fee_basis_points: u16,
) -> Result<()>;
```

**Accounts**: `client` (signer), `freelancer` (readonly), `escrow` (PDA, init), `token_mint` (optional — system program for SOL), `platform_fee_recipient` (readonly), `system_program`

#### deposit

```rust
pub fn deposit(ctx: Context<Deposit>) -> Result<()>;
```

**Accounts**: `client` (signer), `escrow` (PDA, mut), `client_token_account` (if SPL), `escrow_token_account` (if SPL), `token_program` (if SPL), `system_program`

#### complete_milestone

```rust
pub fn complete_milestone(ctx: Context<CompleteMilestone>, index: u8) -> Result<()>;
```

**Accounts**: `client` (signer), `escrow` (PDA, mut), `freelancer` (mut), `platform_fee_recipient` (mut), token accounts (if SPL), `token_program` (if SPL), `system_program`

#### raise_dispute

```rust
pub fn raise_dispute(ctx: Context<RaiseDispute>, index: u8) -> Result<()>;
```

**Accounts**: `raiser` (signer — client or freelancer), `escrow` (PDA, mut)

#### resolve_dispute

```rust
pub fn resolve_dispute(
    ctx: Context<ResolveDispute>,
    index: u8,
    resolution: DisputeResolution,
    freelancer_split_amount: u64,
) -> Result<()>;
```

**Accounts**: `arbitrator` (signer), `escrow` (PDA, mut), `freelancer` (mut), `client` (mut), `platform_fee_recipient` (mut), token accounts (if SPL), `token_program` (if SPL), `system_program`

#### sign_emergency_withdrawal / emergency_withdraw

```rust
pub fn sign_emergency_withdrawal(ctx: Context<SignEmergency>) -> Result<()>;
pub fn emergency_withdraw(ctx: Context<EmergencyWithdraw>) -> Result<()>;
```

### Events

```rust
#[event]
pub struct EscrowFunded {
    pub client: Pubkey,
    pub total_amount: u64,
    pub token_mint: Pubkey,
}

#[event]
pub struct FundsReleased {
    pub milestone_index: u8,
    pub freelancer: Pubkey,
    pub net_amount: u64,
    pub platform_fee_amount: u64,
}

#[event]
pub struct DisputeRaised {
    pub milestone_index: u8,
    pub raised_by: Pubkey,
}

#[event]
pub struct DisputeResolved {
    pub milestone_index: u8,
    pub resolution: DisputeResolution,
    pub freelancer_amount: u64,
    pub client_amount: u64,
}

#[event]
pub struct EmergencyWithdrawalSigned {
    pub signer: Pubkey,
}

#[event]
pub struct EmergencyWithdrawal {
    pub client_amount: u64,
}
```

### Enums

```rust
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq)]
pub enum MilestoneStatus {
    Pending,
    Completed,
    Disputed,
    Resolved,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq)]
pub enum DisputeResolution {
    PayFreelancer,
    RefundClient,
    Split,
}
```

### Data Model Changes

No database changes in this issue — the `EscrowContract` proto entity is already defined in `packages/schema/proto/contracts/v1/escrow.proto`. The `api` service will store the escrow PDA addresses after creation (tracked in Issue #3/Issue #6).

### Dependencies

- **Anchor** (0.30+) — Solana program framework
- **Solana CLI** (1.18+) — `solana-test-validator` for local development
- **SPL Token** — for USDC and other SPL token support
- No external Solana program dependencies — SPL Token interface used directly

---

## Security Considerations

- **Account validation**: Anchor's account constraints (`#[account(...)]`) enforce PDA derivation, ownership, and signer checks at the framework level
- **PDA authority**: The escrow PDA is owned by the program; only the program can debit funds from it. No private key exists for a PDA.
- **Integer overflow**: Rust's default checked arithmetic prevents overflow in release mode; Anchor also performs checked math
- **Access control**: `deposit` — only client (signer check); `complete_milestone` — only client; `resolve_dispute` — only arbitrator (program authority); `raise_dispute` — client or freelancer
- **Fee cap**: `platform_fee_basis_points` capped at 1000 (10%) to protect against misconfiguration
- **SOL vs SPL token**: SOL path uses system program transfers; SPL path uses token program transfers. Instructions validate the correct path based on `token_mint`
- **No upgradeable programs**: Program is deployed as immutable in v1; any bugs require redeployment with a new program ID
- **Emergency withdrawal**: Funds returned to client (depositor); both parties must sign to prevent unilateral drain
- **Rent exemption**: All PDA accounts are initialized with sufficient lamports for rent exemption

---

## Observability

- **Events**: All state transitions emit Anchor events via `emit!()`; `api` service indexes these via Solana transaction logs
- **Logs**: api service logs arbitration calls at INFO level
- **Alerts**: If `anchor test` fails in CI, block the PR

---

## Testing Plan

### Anchor Tests (in `tests/`)

- `gig_escrow.ts` (TypeScript) or `gig_escrow.rs` (Rust)
  - Unit: initialize_escrow (valid params, invalid fee bps > 1000)
  - Unit: deposit SOL (correct amount, wrong amount, double deposit)
  - Unit: deposit SPL token (correct amount, insufficient balance)
  - Unit: complete_milestone (SOL + SPL, platform fee math, only client can call)
  - Unit: raise_dispute (sets Disputed status, emits event, client or freelancer can call)
  - Unit: resolve_dispute (PayFreelancer, RefundClient, Split)
  - Unit: emergency withdrawal (single sig, double sig, actually withdraws)
  - Integration: full lifecycle — initialize → deposit → complete all milestones → verify balances
  - Integration: dispute lifecycle — initialize → deposit → raise_dispute → resolve_dispute → verify splits
  - Edge case: attempt to complete already-completed milestone (should fail)
  - Edge case: attempt to raise dispute on completed milestone (should fail)
  - Edge case: non-client attempts complete_milestone (should fail)

---

## Migration / Rollout Plan

- **Database migrations**: None required for this issue
- **Breaking changes**: No — programs are newly deployed
- **Feature flag**: No
- **Rollback plan**: Deploy new program with new program ID; update `ESCROW_PROGRAM_ID` in api `.env` to point to new program.

---

## Open Questions

| Question                                                           | Owner    | Status                                                                   |
| ------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------ |
| Should `resolve_dispute` platform fee be charged on SPLIT payouts? | Platform | Open — v1 charges no fee on dispute resolutions (arbitration is the fee) |

---

## References

- Related ADR: [ADR 0003](../adr/0003-solana-migration.md) — Solana migration decision
- Proto definition: `packages/schema/proto/contracts/v1/escrow.proto`
- Related issues: #3 (Gig Creation), #5 (Work Submission), #6 (Milestone Approval + Fund Release)
