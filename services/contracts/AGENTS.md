# AGENTS.md — contracts

> Agent contract for the `contracts` service.
> Read this before modifying anything in this service directory.

---

## Service Overview

**Name**: `contracts`
**Purpose**: Solidity smart contracts deployed on Base L2. Owns the trustless escrow logic for SkillBridge gigs. `EscrowFactory` deploys a `GigEscrow` per gig; `GigEscrow` locks client funds on creation, tracks milestones, and releases funds when milestones are completed. Called by the `api` service via web3.py.
**Language**: Solidity ^0.8.24
**Toolchain**: Foundry (forge, cast, anvil)
**Network**: Base L2 (Base Sepolia for dev/testing, Base Mainnet for production)
**Created**: 2026-03-07
**ADR**: `docs/adr/0002-tech-stack.md`

---

## Tech Stack

- **Language**: Solidity ^0.8.24
- **Toolchain**: Foundry (forge test, forge build, forge deploy)
- **Network**: Base L2 (EVM-compatible, low gas fees)
- **Testing**: Foundry (forge test with fuzzing)
- **Protocol**: On-chain (no HTTP server — called via ABI + web3.py from api)

---

## Repository Layout

```
services/contracts/
├── src/
│   ├── EscrowFactory.sol   # Deploys GigEscrow instances
│   ├── GigEscrow.sol       # Per-gig escrow: deposit, milestone tracking, fund release
│   └── interfaces/         # IEscrowFactory.sol, IGigEscrow.sol
├── test/
│   ├── EscrowFactory.t.sol
│   └── GigEscrow.t.sol     # Includes fuzz tests for fund accounting
├── script/
│   ├── Deploy.s.sol        # Foundry deploy script
│   └── DeployBase.s.sol    # Base Sepolia / Mainnet deployment config
├── out/                    # Compiled artifacts (gitignored)
├── abi/                    # Exported ABIs for web3.py (committed)
│   ├── EscrowFactory.json
│   └── GigEscrow.json
├── foundry.toml
├── .env.example
└── README.md
```

---

## Key Entry Points

- **EscrowFactory**: `src/EscrowFactory.sol` — single deployed instance; creates GigEscrow contracts
- **GigEscrow**: `src/GigEscrow.sol` — per-gig contract; holds funds; `completeMilestone()` releases payment
- **ABIs**: `abi/` — JSON ABIs imported by the `api` service

---

## Environment Variables

| Variable | Description |
|---|---|
| `PRIVATE_KEY` | Deployer wallet private key (never commit) |
| `BASE_RPC_URL` | Base L2 RPC endpoint |
| `BASESCAN_API_KEY` | For contract verification on Basescan |

---

## Contract Interfaces

### EscrowFactory
```solidity
function createEscrow(
    address client,
    address freelancer,
    uint256 milestoneCount,
    uint256[] calldata amounts  // wei per milestone
) external returns (address escrowAddress);
```

### GigEscrow
```solidity
function deposit() external payable;
function completeMilestone(uint256 index) external;  // called by client or api oracle
function raiseDispute(uint256 index) external;
function resolveDispute(uint256 index, bool payFreelancer) external;  // arbitration
function getBalance() external view returns (uint256);
```

---

## ABI Export

After any contract change, regenerate ABIs for the api service:

```bash
cd services/contracts
forge build
cp out/EscrowFactory.sol/EscrowFactory.json abi/
cp out/GigEscrow.sol/GigEscrow.json abi/
```

Commit the updated ABI files — the `api` service reads from `abi/`.

---

## Testing

```bash
cd services/contracts
forge test          # run all tests
forge test -vvv     # verbose output
forge coverage      # coverage report
```

**Required**: All fund-handling functions must have fuzz tests. No PR merges if `forge test` fails.

---

## Deployment

```bash
# Base Sepolia (testnet)
forge script script/DeployBase.s.sol --rpc-url $BASE_SEPOLIA_RPC_URL --broadcast --verify

# Base Mainnet — REQUIRES human approval before running
forge script script/DeployBase.s.sol --rpc-url $BASE_RPC_URL --broadcast --verify
```

Store deployed contract addresses in `api`'s `.env` (`ESCROW_FACTORY_ADDRESS`).

---

## Constraints

- No upgradeable proxies in v1 — keep contracts simple and auditable
- Emergency withdrawal function allowed only with both client + freelancer signatures
- All state transitions must emit events (for the api to index)
- Never store off-chain data (URLs, text) in contract storage — only addresses and amounts

---

## Forbidden Actions for Agents

- Deploying to Base Mainnet without explicit human approval
- Removing the emergency withdrawal function
- Adding upgradeable proxy patterns without an ADR
- Changing function signatures without updating ABI files and the api service

---

## Agent Capabilities

Agents may use any available MCP servers, skills, and tools as needed.

### MCP Servers in Use

| MCP Server | Purpose | Added by |
|---|---|---|
| (none yet) | | |

---

## Related ADRs

- [ADR 0001](../../docs/adr/0001-monorepo-structure.md) — Monorepo structure
- [ADR 0002](../../docs/adr/0002-tech-stack.md) — Tech stack decisions
