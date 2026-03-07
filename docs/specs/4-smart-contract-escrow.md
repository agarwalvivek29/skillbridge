# Spec: Smart Contract Escrow on Base L2

**Issue**: #4
**Status**: Approved
**Author**: ao agent
**Date**: 2026-03-07
**Services Affected**: `contracts`, `api`

---

## Summary

Deploy `EscrowFactory` and `GigEscrow` Solidity contracts on Base L2. When a client funds a gig, the total budget is locked in a `GigEscrow` instance deployed by the factory. Funds are released per-milestone when the client (or API oracle) calls `completeMilestone(index)`. Disputes can be raised and resolved by an arbitration address.

---

## Background and Motivation

SkillBridge needs trustless fund escrow so that clients are confident funds will only be released on delivery, and freelancers are confident they'll be paid for approved work. Without on-chain escrow, the platform requires off-platform trust. Base L2 provides low gas costs and EVM compatibility.

---

## Scope

### In Scope

- `EscrowFactory` contract — single deployed instance that creates `GigEscrow` contracts
- `GigEscrow` contract — per-gig instance holding funds, tracking milestones, releasing payments
- `deposit()` — client locks total budget
- `completeMilestone(uint256 index)` — releases per-milestone amount to freelancer
- `raiseDispute(uint256 index)` — locks milestone pending arbitration
- `resolveDispute(uint256 index, bool payFreelancer)` — arbitration contract resolves dispute
- Emergency withdrawal requiring both client + freelancer signatures
- Foundry fuzz tests for all fund-handling functions
- ABI export to `services/contracts/abi/`
- Foundry deploy scripts for Base Sepolia

### Out of Scope

- Deployment to Base Mainnet (requires explicit human approval)
- Upgradeable proxy patterns (explicitly excluded in v1)
- Off-chain arbitration UI or dispute management service
- ERC-20 token support (v1 is ETH/native asset only)
- `api` service web3.py integration (tracked separately)

---

## Acceptance Criteria

- [ ] Given a gig is created, when `createEscrow(client, freelancer, milestoneCount, amounts)` is called, then a new `GigEscrow` contract is deployed and its address emitted via `EscrowCreated`
- [ ] Given an escrow is deployed, when `deposit()` is called with the exact total budget in ETH, then the contract emits `EscrowFunded` and `getBalance()` returns the deposited amount
- [ ] Given an escrow is funded, when `completeMilestone(index)` is called by the client or API oracle, then the milestone amount is transferred to the freelancer and `MilestoneCompleted` is emitted
- [ ] Given a milestone is in progress, when `raiseDispute(index)` is called by client or freelancer, then the milestone is locked and `DisputeRaised` is emitted
- [ ] Given a dispute is raised, when `resolveDispute(index, true)` is called by the arbitration address, then funds go to freelancer; when called with `false`, funds are refunded to client
- [ ] Emergency withdrawal (`emergencyWithdraw`) requires signatures from both client and freelancer
- [ ] All fund-handling functions have Foundry fuzz tests (deposit amounts, milestone indices, addresses)
- [ ] `forge test` passes with zero failures
- [ ] ABIs exported to `services/contracts/abi/EscrowFactory.json` and `GigEscrow.json` and committed

---

## Technical Design

### Architecture Overview

```
[api service / client wallet]
         │
         ▼
  EscrowFactory (deployed once)
         │  createEscrow(client, freelancer, milestoneCount, amounts)
         ▼
  GigEscrow (deployed per gig)
    ├── deposit()               ← client sends ETH = sum(amounts)
    ├── completeMilestone(i)    ← client or oracle releases milestone i
    ├── raiseDispute(i)         ← client or freelancer locks milestone i
    ├── resolveDispute(i, pay)  ← arbitration address resolves
    └── emergencyWithdraw()     ← requires both signatures (multisig)
```

### Contract: EscrowFactory

```solidity
// Deploys one GigEscrow per gig
function createEscrow(
    address client,
    address freelancer,
    uint256 milestoneCount,
    uint256[] calldata amounts
) external returns (address escrowAddress);

event EscrowCreated(
    address indexed escrowAddress,
    address indexed client,
    address indexed freelancer,
    uint256 totalAmount
);
```

### Contract: GigEscrow

**State**:

- `address public client`
- `address public freelancer`
- `address public arbitrator` (set by factory owner / API oracle address)
- `MilestoneStatus[] public milestones` — PENDING | COMPLETED | DISPUTED | REFUNDED
- `uint256[] public amounts`
- `bool public funded`
- `mapping(address => bool) public emergencyApprovals`

**Functions**:

```solidity
function deposit() external payable;
function completeMilestone(uint256 index) external;
function raiseDispute(uint256 index) external;
function resolveDispute(uint256 index, bool payFreelancer) external;
function approveEmergencyWithdraw() external;  // client or freelancer approves
function emergencyWithdraw() external;          // executes when both approved
function getBalance() external view returns (uint256);
function getMilestone(uint256 index) external view returns (MilestoneStatus, uint256);
```

**Events**:

```solidity
event EscrowFunded(address indexed escrow, uint256 totalAmount);
event MilestoneCompleted(uint256 indexed index, address indexed freelancer, uint256 amount);
event DisputeRaised(uint256 indexed index, address indexed raisedBy);
event DisputeResolved(uint256 indexed index, bool paidFreelancer, uint256 amount);
event EmergencyWithdrawApproved(address indexed approver);
event EmergencyWithdrawExecuted(uint256 clientAmount, uint256 freelancerAmount);
```

### Milestone Status Enum

```
PENDING → COMPLETED (via completeMilestone)
PENDING → DISPUTED  (via raiseDispute)
DISPUTED → COMPLETED (via resolveDispute(true))
DISPUTED → REFUNDED  (via resolveDispute(false))
```

### Access Control

| Function                     | Allowed callers              |
| ---------------------------- | ---------------------------- |
| `deposit()`                  | client only                  |
| `completeMilestone()`        | client or arbitrator         |
| `raiseDispute()`             | client or freelancer         |
| `resolveDispute()`           | arbitrator only              |
| `approveEmergencyWithdraw()` | client or freelancer         |
| `emergencyWithdraw()`        | anyone (after both approved) |

### Dependencies

- Foundry (`forge-std`) for testing
- No OpenZeppelin in v1 to minimize complexity and audit surface
- Base Sepolia RPC for testnet deployment

---

## Security Considerations

- Reentrancy: use checks-effects-interactions pattern; send ETH last
- Integer overflow: Solidity ^0.8.24 has built-in overflow protection
- Access control: every state-changing function checks `msg.sender`
- Emergency withdrawal: requires both parties to approve — prevents unilateral drain
- No upgradeable proxies: immutable contract logic reduces attack surface
- Arbitrator address set at construction; cannot be changed post-deploy

---

## Observability

- All state transitions emit events — `api` service indexes these to track escrow state
- No on-chain logging beyond events

---

## Testing Plan

### Unit / Fuzz Tests (Foundry)

- `EscrowFactory.t.sol`: fuzz `createEscrow` with random addresses and amounts arrays
- `GigEscrow.t.sol`:
  - Fuzz `deposit()` with random amounts (test overpay/underpay revert)
  - Fuzz `completeMilestone` with random valid/invalid indices
  - Test all milestone state transitions
  - Test dispute flow (raise + resolve both ways)
  - Test emergency withdrawal with both / one / zero approvals
  - Test reentrancy (via malicious receiver contract)

### Manual Testing Steps

1. `forge test` — all pass
2. Deploy to Base Sepolia anvil fork: `forge script script/Deploy.s.sol --fork-url $BASE_RPC_URL`
3. Interact via `cast` to verify events and balance

---

## Migration / Rollout Plan

- **Database migrations**: No (contracts are on-chain)
- **Breaking changes**: No (new contracts)
- **Feature flag**: No
- **Rollback plan**: Contracts are immutable. Emergency withdrawal ensures funds can be recovered.

---

## Open Questions

| Question                                                               | Owner | Status                                          |
| ---------------------------------------------------------------------- | ----- | ----------------------------------------------- |
| Who is the arbitrator address in v1 — an API oracle key or a multisig? | Team  | Open (defaulting to API oracle key for v1)      |
| Should emergency withdrawal split funds 50/50 or allow custom split?   | Team  | Open (defaulting to return all funds to client) |

---

## References

- Related ADR: [ADR 0002](../adr/0002-tech-stack.md) — Base L2 and Foundry decision
- Issue: #4
- AGENTS.md: `services/contracts/AGENTS.md`
