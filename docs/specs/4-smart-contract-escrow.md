# Spec: Smart Contract Escrow on Base L2

> Copy this file to `docs/specs/[ISSUE-NUMBER]-[feature-name].md` and fill it in.
> The spec must be completed and linked in the GitHub Issue before implementation begins.

**Issue**: #4
**Status**: Approved
**Author**: Claude Code (ao)
**Date**: 2026-03-07
**Services Affected**: `services/contracts`, `services/api`

---

## Summary

Deploy `EscrowFactory` and `GigEscrow` Solidity contracts on Base L2 to enable trustless fund locking and per-milestone release for SkillBridge gigs. Supports both native ETH and ERC-20 (USDC) payment. A 5% platform fee (500 basis points) is deducted from each milestone payout and sent to the platform fee recipient.

---

## Background and Motivation

SkillBridge's core value proposition is trustless escrow — neither the client nor the freelancer needs to trust each other; the smart contract enforces payment. Without this contract layer, SkillBridge is just another centralized marketplace. This is the foundation every other feature (work submission, milestone approval, dispute resolution) depends on.

---

## Scope

### In Scope

- `EscrowFactory.sol` — single deployed instance; creates one `GigEscrow` per gig
- `GigEscrow.sol` — per-gig escrow contract with full milestone lifecycle
- Support for ETH (native) and ERC-20 (USDC) deposits
- Platform fee (configurable basis points, default 500 = 5%) deducted on each milestone payout
- `deposit()` — client locks total budget; emits `EscrowFunded`
- `completeMilestone(index)` — releases net amount to freelancer + fee to platform; emits `FundsReleased`
- `raiseDispute(index)` — locks a milestone pending arbitration; emits `DisputeRaised`
- `resolveDispute(index, resolution, freelancerSplitAmount)` — arbitrator resolves with PAY_FREELANCER, REFUND_CLIENT, or SPLIT outcome
- Emergency withdrawal (2-of-2 multisig: client + freelancer) for force majeure situations
- Foundry fuzz tests covering all fund-handling paths (ETH and ERC-20)
- ABI export to `services/contracts/abi/` for consumption by `services/api` via web3.py

### Out of Scope

- Upgradeable proxy patterns (v1 uses fixed contracts — no proxies)
- Deployment to Base Mainnet (requires explicit human approval)
- On-chain dispute arbitration voting (v1 is off-chain + arbitrator address)
- Integration with `services/api` web3.py client (Issue #6)
- Frontend wallet interactions (Issue #3 + Issue #5)

---

## Acceptance Criteria

- [ ] `EscrowFactory` deploys a `GigEscrow` per gig, storing client + freelancer addresses, `token_address` (address(0) for ETH, ERC-20 address for USDC), milestone amounts[], and `platform_fee_basis_points` (500 = 5%)
- [ ] Client calls `deposit()` to lock total budget; contract emits `EscrowFunded`
- [ ] `completeMilestone(index)` releases milestone amount minus platform fee to freelancer; fee goes to `platform_fee_recipient`; emits `FundsReleased(net_amount, platform_fee_amount)`
- [ ] `raiseDispute(index)` locks the milestone pending arbitration; emits `DisputeRaised`
- [ ] `resolveDispute(index, resolution, freelancer_split_amount)` handles PAY_FREELANCER, REFUND_CLIENT, or SPLIT outcomes
- [ ] Emergency withdrawal requires both client + freelancer to call `signEmergencyWithdrawal()` before `emergencyWithdraw()` executes
- [ ] All fund-handling functions covered by Foundry fuzz tests for both ETH and ERC-20 paths
- [ ] `forge test` passes with zero failures
- [ ] ABIs exported to `services/contracts/abi/EscrowFactory.json` and `services/contracts/abi/GigEscrow.json`

---

## Technical Design

### Architecture Overview

```
[api service — web3.py]
    │  createEscrow(client, freelancer, tokenAddress, milestoneAmounts, feeBps)
    ▼
[EscrowFactory] ──────────── deploys ──────────────▶ [GigEscrow #1]
    │                                                 [GigEscrow #2]
    │                                                 [GigEscrow #N]
    │
    │  completeMilestone(index)  ◀── called by api after client approves
    │  raiseDispute(index)        ◀── called by api when dispute raised
    │  resolveDispute(...)        ◀── called by api (arbitrator) after resolution
    ▼
[Freelancer wallet] ← netAmount
[Platform fee recipient] ← platformFeeAmount
```

### Contract Interfaces

#### EscrowFactory

```solidity
function createEscrow(
    address client,
    address freelancer,
    address tokenAddress,
    uint256[] calldata milestoneAmounts,
    uint256 platformFeeBasisPoints
) external returns (address escrowAddress);

function setFeeRecipient(address newRecipient) external; // owner only
```

#### GigEscrow

```solidity
// Deposit
function deposit() external payable; // ETH: payable; ERC-20: approve first

// Milestone lifecycle
function completeMilestone(uint256 index) external; // onlyClient
function raiseDispute(uint256 index) external;       // client or freelancer
function resolveDispute(
    uint256 index,
    DisputeResolution resolution,
    uint256 freelancerSplitAmount
) external; // onlyArbitrator

// Emergency withdrawal
function signEmergencyWithdrawal() external; // client or freelancer
function emergencyWithdraw() external;       // executable once both signed

// View
function getBalance() external view returns (uint256);
function getMilestoneStatus(uint256 index) external view returns (MilestoneStatus);
```

### Events

```solidity
event EscrowFunded(address indexed client, uint256 totalAmount, address tokenAddress);
event FundsReleased(uint256 indexed milestoneIndex, address indexed freelancer, uint256 netAmount, uint256 platformFeeAmount);
event DisputeRaised(uint256 indexed milestoneIndex, address indexed raisedBy);
event DisputeResolved(uint256 indexed milestoneIndex, DisputeResolution resolution, uint256 freelancerAmount, uint256 clientAmount);
event EmergencyWithdrawalSigned(address indexed signer);
event EmergencyWithdrawal(uint256 clientAmount);
```

### Enums

```solidity
enum MilestoneStatus { PENDING, COMPLETED, DISPUTED, RESOLVED }
enum DisputeResolution { PAY_FREELANCER, REFUND_CLIENT, SPLIT }
```

### Data Model Changes

No database changes in this issue — the `EscrowContract` proto entity is already defined in `packages/schema/proto/contracts/v1/escrow.proto`. The `api` service will store the deployed contract addresses after creation (tracked in Issue #3/Issue #6).

### Dependencies

- **Foundry** (forge 1.5.1+) — already installed
- **forge-std** — Foundry standard testing library, installed as git submodule in `lib/forge-std`
- No OpenZeppelin dependency — IERC20 interface defined inline to avoid external deps

---

## Security Considerations

- **Re-entrancy**: ETH transfers use `.call{value}()` with checks-effects-interactions pattern (state updated before transfer)
- **Integer overflow**: Solidity 0.8.24 has built-in overflow checks
- **Access control**: `deposit()` — only client; `completeMilestone()` — only client; `resolveDispute()` — only arbitrator (factory owner); `raiseDispute()` — client or freelancer
- **Fee cap**: `platformFeeBasisPoints` capped at 1000 (10%) to protect against misconfiguration
- **ETH vs ERC-20**: ETH path checks `msg.value == totalAmount`; ERC-20 path checks `msg.value == 0` to prevent accidental ETH lock
- **No upgradeable proxies**: Simplicity over upgradeability in v1; any bugs require redeployment
- **Emergency withdrawal**: Funds returned to client (depositor); both parties must sign to prevent unilateral drain

---

## Observability

- **Events**: All state transitions emit events; `api` service indexes these via web3.py event filter
- **Logs**: api service logs arbitration calls at INFO level
- **Alerts**: If `forge test` fails in CI, block the PR

---

## Testing Plan

### Foundry Tests (in `test/`)

- `GigEscrow.t.sol`
  - Unit: deposit ETH (correct amount, wrong amount, double deposit)
  - Unit: deposit ERC-20 (correct, insufficient allowance)
  - Unit: completeMilestone (ETH + ERC-20, platform fee math, only client)
  - Unit: raiseDispute (sets DISPUTED status, emits event)
  - Unit: resolveDispute (PAY_FREELANCER, REFUND_CLIENT, SPLIT)
  - Unit: emergency withdrawal (single sig, double sig, actually withdraws)
  - **Fuzz**: `testFuzz_completeMilestone_feeAccountingETH(uint256 amount)`
  - **Fuzz**: `testFuzz_completeMilestone_feeAccountingERC20(uint256 amount)`
  - **Fuzz**: `testFuzz_resolveDispute_split(uint256 freelancerSplit)`

- `EscrowFactory.t.sol`
  - Unit: createEscrow deploys new GigEscrow and emits event
  - Unit: setFeeRecipient (owner only, reverts for non-owner)

---

## Migration / Rollout Plan

- **Database migrations**: None required for this issue
- **Breaking changes**: No — contracts are newly deployed
- **Feature flag**: No
- **Rollback plan**: Redeploy EscrowFactory; existing GigEscrow contracts continue to function independently. Update `ESCROW_FACTORY_ADDRESS` in api `.env` to point to new factory.

---

## Open Questions

| Question                                                          | Owner    | Status                                                                   |
| ----------------------------------------------------------------- | -------- | ------------------------------------------------------------------------ |
| Should `resolveDispute` platform fee be charged on SPLIT payouts? | Platform | Open — v1 charges no fee on dispute resolutions (arbitration is the fee) |

---

## References

- Related ADR: [ADR 0002](../adr/0002-tech-stack.md) — Base L2 tech stack decision
- Proto definition: `packages/schema/proto/contracts/v1/escrow.proto`
- Related issues: #3 (Gig Creation), #5 (Work Submission), #6 (Milestone Approval + Fund Release)
