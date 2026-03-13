# AGENTS.md — contracts

> Agent contract for the `contracts` service.
> Read this before modifying anything in this service directory.

---

## Service Overview

**Name**: `contracts`
**Purpose**: Anchor smart program deployed on Solana. Owns the trustless escrow logic for SkillBridge gigs. A single `gig_escrow` program uses PDAs (Program Derived Addresses) to create per-gig escrow accounts. Each escrow locks client funds on deposit, tracks milestones, and releases funds when milestones are completed or disputes are resolved. Called by the `api` service via @solana/web3.js or anchor client.
**Language**: Rust
**Toolchain**: Anchor 0.30.1 (anchor build, anchor test, anchor deploy)
**Network**: Solana (localhost for dev, Devnet for staging, Mainnet-beta for production)
**Created**: 2026-03-07 (migrated from Solidity on 2026-03-13)
**ADR**: `docs/adr/0002-tech-stack.md`, `docs/adr/0003-solana-migration.md`

---

## Tech Stack

- **Language**: Rust (2021 edition)
- **Framework**: Anchor 0.30.1
- **Token support**: anchor-spl 0.30.1 (for SPL token escrows)
- **Network**: Solana (sub-second finality, ~$0.00025/tx)
- **Testing**: TypeScript with @coral-xyz/anchor + mocha
- **Protocol**: On-chain (no HTTP server — called via Anchor IDL client from api)

---

## Repository Layout

```
services/contracts/
├── Anchor.toml                 # Anchor workspace config
├── Cargo.toml                  # Rust workspace (members = programs/*)
├── programs/
│   └── gig_escrow/
│       ├── Cargo.toml          # Program crate config
│       └── src/
│           └── lib.rs          # All escrow instructions + accounts + errors
├── tests/
│   └── gig_escrow.ts           # TypeScript integration tests
├── .env.example
├── .gitignore
└── AGENTS.md
```

---

## Key Entry Points

- **Program**: `programs/gig_escrow/src/lib.rs` — all 7 instructions, account structs, events, errors
- **Tests**: `tests/gig_escrow.ts` — full lifecycle integration tests

---

## Instructions

| Instruction                 | Who can call         | Description                                                |
| --------------------------- | -------------------- | ---------------------------------------------------------- |
| `initialize_escrow`         | Client               | Create escrow PDA for a gig with milestones                |
| `deposit`                   | Client               | Lock SOL or SPL tokens in the vault PDA                    |
| `complete_milestone`        | Client               | Release milestone funds to freelancer (minus platform fee) |
| `raise_dispute`             | Client or Freelancer | Lock a milestone in DISPUTED status                        |
| `resolve_dispute`           | Arbitrator           | Resolve: PAY_FREELANCER / REFUND_CLIENT / SPLIT            |
| `sign_emergency_withdrawal` | Client or Freelancer | Sign 2-of-2 consent for emergency withdrawal               |
| `emergency_withdraw`        | Client or Freelancer | Execute after both sign — returns all funds to client      |

---

## PDA Seeds

| PDA    | Seeds                               | Purpose                  |
| ------ | ----------------------------------- | ------------------------ |
| Escrow | `[b"escrow", gig_id.as_bytes()]`    | Per-gig escrow metadata  |
| Vault  | `[b"vault", escrow.key().as_ref()]` | Holds SOL for the escrow |

---

## Environment Variables

| Variable            | Description                                          |
| ------------------- | ---------------------------------------------------- |
| `SOLANA_RPC_URL`    | Solana RPC endpoint (default: http://localhost:8899) |
| `ESCROW_PROGRAM_ID` | Deployed program address (base58)                    |
| `ANCHOR_WALLET`     | Path to keypair JSON file                            |
| `FEE_RECIPIENT`     | Platform fee recipient wallet (base58)               |

---

## Building

```bash
cd services/contracts
anchor build
```

This compiles the program to `target/deploy/gig_escrow.so` and generates the IDL at `target/idl/gig_escrow.json`.

---

## Testing

```bash
cd services/contracts
anchor test
```

This starts a local Solana validator, deploys the program, and runs the TypeScript tests.

---

## Deployment

```bash
# Devnet
anchor deploy --provider.cluster devnet

# Mainnet-beta — REQUIRES human approval before running
anchor deploy --provider.cluster mainnet
```

Store the deployed program ID in `api`'s `.env` (`ESCROW_PROGRAM_ID`).

---

## Constraints

- No upgradeable programs in v1 — keep the program simple and auditable
- Emergency withdrawal function requires both client + freelancer 2-of-2 consent
- All state transitions must emit events (for the api to index)
- Never store off-chain data (URLs, text) in account storage — only addresses and amounts
- Maximum 20 milestones per escrow (account size constraint)

---

## Forbidden Actions for Agents

- Deploying to Mainnet-beta without explicit human approval
- Removing the emergency withdrawal instruction
- Adding upgradeable program patterns without an ADR
- Changing instruction interfaces without updating the api service integration

---

## Agent Capabilities

Agents may use any available MCP servers, skills, and tools as needed.

### MCP Servers in Use

| MCP Server | Purpose | Added by |
| ---------- | ------- | -------- |
| (none yet) |         |          |

---

## Related ADRs

- [ADR 0001](../../docs/adr/0001-monorepo-structure.md) — Monorepo structure
- [ADR 0002](../../docs/adr/0002-tech-stack.md) — Tech stack decisions
- [ADR 0003](../../docs/adr/0003-solana-migration.md) — Solana migration
