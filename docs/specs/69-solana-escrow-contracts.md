# Spec: Rewrite Escrow Contracts from Solidity to Rust/Anchor for Solana

**Issue**: #69
**Status**: Approved
**Author**: vivek
**Date**: 2026-03-13
**Services Affected**: contracts

---

## Summary

Migrate the SkillBridge escrow smart contract layer from Solidity/Foundry (Base L2) to Rust/Anchor (Solana). The new Anchor program preserves all existing escrow functionality (deposit, milestone completion with fee deduction, disputes, emergency withdrawal) while targeting Solana's runtime and PDA-based account model.

---

## Background and Motivation

Solana offers sub-second finality, significantly lower transaction costs ($0.00025 vs ~$0.01 on Base L2), and a growing DeFi ecosystem. The Anchor framework provides a mature, type-safe Rust SDK with automatic account validation, PDA derivation, and IDL generation -- reducing the surface area for smart contract bugs compared to raw Solidity.

This migration also positions SkillBridge for Solana-native wallet integrations (Phantom, Solflare) and SPL token support (USDC-SPL).

---

## Scope

### In Scope

- Remove all Solidity/Foundry files (src/, test/, foundry.toml, lib/, out/, abi/, cache/)
- Create Anchor workspace structure in services/contracts/
- Implement gig_escrow Anchor program with 7 instructions: initialize_escrow, deposit, complete_milestone, raise_dispute, resolve_dispute, sign_emergency_withdrawal, emergency_withdraw
- PDA-based escrow and vault accounts
- Support for both SOL and SPL token payments
- TypeScript test file with Anchor test structure
- Update .env.example for Solana configuration
- Update AGENTS.md for new toolchain

### Out of Scope

- EscrowFactory equivalent (Solana programs are singletons; escrow PDAs replace per-gig contract deployment)
- Deployment scripts (deferred until Solana toolchain is available in CI)
- Changes to the api service or web frontend (separate issues)
- Proto schema changes (the escrow.proto abstraction layer remains valid)

---

## Acceptance Criteria

- [ ] All Solidity/Foundry files are removed from services/contracts/
- [ ] Anchor workspace compiles (Anchor.toml, workspace Cargo.toml, program Cargo.toml are valid)
- [ ] gig_escrow program implements all 7 instructions with proper account validation
- [ ] Escrow PDA derived from seeds [b"escrow", gig_id.as_bytes()]
- [ ] Vault PDA derived from seeds [b"vault", escrow.key().as_ref()]
- [ ] Milestone statuses tracked as u8 enum (PENDING=0, COMPLETED=1, DISPUTED=2, RESOLVED=3)
- [ ] Platform fee deducted in basis points on complete_milestone
- [ ] Emergency withdrawal requires both client and freelancer signatures
- [ ] TypeScript test file covers all 7 instructions
- [ ] .env.example updated for Solana
- [ ] AGENTS.md updated to describe Anchor/Rust setup

---

## Technical Design

### Architecture Overview

The Solidity factory pattern (EscrowFactory deploys GigEscrow per gig) is replaced by a single deployed Anchor program that uses PDAs to create per-gig escrow accounts. Each gig gets:

1. An **Escrow PDA** storing gig metadata, milestone amounts/statuses, and party addresses
2. A **Vault PDA** holding SOL (or an associated token account for SPL tokens)

```
[Client Wallet] ---> initialize_escrow ---> [Escrow PDA] + [Vault PDA]
                ---> deposit           ---> funds locked in Vault
                ---> complete_milestone --> funds released to freelancer (minus fee)
[Either party]  ---> raise_dispute     ---> milestone locked
[Arbitrator]    ---> resolve_dispute   ---> funds distributed per resolution
[Both parties]  ---> sign_emergency_withdrawal + emergency_withdraw
```

### Account Structs

- `Escrow`: gig_id (String), client, freelancer, arbitrator, token_mint (Option<Pubkey>), milestone_amounts (Vec<u64>), milestone_statuses (Vec<u8>), platform_fee_bps (u16), fee_recipient, total_deposited (u64), total_released (u64), is_funded (bool), client_emergency_signed (bool), freelancer_emergency_signed (bool), bump (u8)

### Dependencies

- anchor-lang 0.30.1
- anchor-spl 0.30.1
- @coral-xyz/anchor (TypeScript tests)
- @solana/web3.js (TypeScript tests)

---

## Security Considerations

- PDA seeds ensure each gig has a unique, deterministic escrow address
- All instructions validate signer authority (client, arbitrator, or client-or-freelancer)
- Vault PDA is program-owned; funds cannot be withdrawn without program authorization
- Emergency withdrawal requires 2-of-2 consent (both parties sign)
- Overflow checks enabled in release profile

---

## Testing Plan

### Unit Tests

- Rust: anchor program instruction handlers (compile-time validation via Anchor constraints)

### Integration Tests

- TypeScript: full lifecycle tests using @coral-xyz/anchor test framework
  - Initialize escrow
  - Deposit SOL
  - Complete milestone with fee verification
  - Raise dispute
  - Resolve dispute (all 3 outcomes)
  - Emergency withdrawal flow

---

## Migration / Rollout Plan

- **Breaking changes**: Yes -- complete replacement of contract layer. The api service will need a new integration module (separate issue).
- **Rollback plan**: Revert this PR to restore Solidity contracts.

---

## References

- Related ADR: docs/adr/0003-solana-migration.md
- Related issues: #69
- Anchor documentation: https://www.anchor-lang.com/
