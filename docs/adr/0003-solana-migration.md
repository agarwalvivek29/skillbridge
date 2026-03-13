# 0003 Migrate Blockchain Layer from Base L2 (Solidity) to Solana (Rust/Anchor)

**Date**: 2026-03-13
**Status**: Accepted
**Deciders**: agarwalvivek29
**Issue**: #67
**Supersedes**: Blockchain section of [ADR 0002](./0002-tech-stack.md)

## Context

The SkillBridge contracts service was originally planned for Base L2 using Solidity and Foundry (see ADR 0002). During development, several blockers and opportunities emerged:

1. **Testnet token scarcity**: ETH Sepolia testnet tokens are increasingly hard to obtain. Faucets are rate-limited and unreliable, blocking development velocity. Solana devnet tokens are free and unlimited via `solana airdrop`.
2. **Local development friction**: Running a local Base L2 node requires Anvil with forking or a full node setup. Solana's `solana-test-validator` starts instantly with zero configuration and provides a fully functional local cluster.
3. **Team expertise**: The team has Rust expertise that aligns naturally with Solana's Anchor framework. Solidity expertise is limited.
4. **Transaction finality**: Solana provides sub-second finality (~400ms) compared to Base L2's ~2 second block times. For escrow operations (fund, release, dispute), faster finality directly improves user experience.
5. **Program architecture**: Solana's Program Derived Address (PDA) pattern is a cleaner fit for per-gig escrow accounts than the EVM factory pattern. PDAs are deterministically derived from seeds (e.g., gig ID) without deploying a new contract per gig.

These factors together make Solana a better fit for SkillBridge's development timeline, team composition, and user experience goals.

## Decision

We will migrate the blockchain layer from Solidity on Base L2 (Foundry) to Rust/Anchor on Solana.

Specifically:

- **Framework**: Anchor (Solana's dominant smart contract framework) replaces Foundry
- **Language**: Rust replaces Solidity for on-chain programs
- **Account model**: PDAs (Program Derived Addresses) replace the EscrowFactory + GigEscrow factory pattern. A single `gig_escrow` Anchor program manages all escrow accounts via PDAs derived from gig identifiers.
- **Token standard**: SPL tokens replace ERC-20. Native SOL replaces native ETH for non-stablecoin payments.
- **Wallet signing**: Ed25519 signing replaces ECDSA/secp256k1. Sign-in with Solana (wallet signs a nonce message, api verifies Ed25519 signature) replaces SIWE (EIP-4361).
- **Wallet ecosystem**: Phantom, Solflare, and Backpack replace MetaMask and Coinbase Wallet. The frontend uses `@solana/web3.js` and `@solana/wallet-adapter` instead of `wagmi/viem`.
- **Networks**: `solana-test-validator` (localnet) for development, devnet for staging, mainnet-beta for production.

## Consequences

### Positive

- **Easier local development**: `solana-test-validator` starts in seconds with zero configuration. Free devnet tokens via `solana airdrop` eliminate testnet token scarcity.
- **Rust expertise alignment**: The team's existing Rust skills transfer directly to Anchor program development.
- **Sub-second finality**: ~400ms slot times mean escrow operations (fund, release) confirm almost instantly, improving UX over Base L2's ~2 second blocks.
- **PDA pattern simplicity**: Deterministic account derivation from seeds (gig ID) is simpler and cheaper than deploying a new contract per gig via a factory. No factory contract needed.
- **Free devnet tokens**: `solana airdrop` provides unlimited devnet SOL, unblocking development.
- **Lower transaction costs**: Solana transactions cost ~$0.00025, comparable to Base L2 but with no bridging friction.

### Negative

- **Smaller DeFi ecosystem**: Solana's DeFi ecosystem is smaller than EVM's. Fewer composability options with existing protocols, though not critical for SkillBridge's escrow use case.
- **Fewer Solana developers in market**: The pool of developers familiar with Solana/Anchor is smaller than the EVM developer pool, which could affect future hiring.
- **Anchor framework maturity**: While Anchor is the dominant Solana framework, it is less mature than Foundry/Hardhat in terms of tooling, debugging, and community resources.
- **Existing EVM documentation and proto definitions**: Requires updating all documentation, specs, and proto definitions that reference Base L2/Solidity concepts.

### Neutral

- **Different wallet ecosystem**: Phantom/Solflare/Backpack replace MetaMask/Coinbase Wallet. Both ecosystems are mature and widely adopted by their respective user bases.
- **Different signing algorithm**: Ed25519 replaces ECDSA/secp256k1. Both are well-supported; the change is transparent to end users.

## Alternatives Considered

### Option A: Stay on Base L2 (Solidity/Foundry)

Keep the original tech stack decision from ADR 0002. Rejected because: testnet token scarcity is actively blocking development, the team lacks deep Solidity expertise, and the factory pattern adds unnecessary deployment complexity. The Coinbase ecosystem alignment benefit does not outweigh these practical blockers.

### Option B: Move to another EVM L2 (Arbitrum, Optimism)

Migrate to a different EVM L2 that might have better testnet faucet availability. Rejected because: testnet token scarcity is a systemic EVM problem affecting all L2s. Moving to another EVM chain does not solve the core issue and does not leverage the team's Rust expertise.

### Option C: Cosmos SDK or Sui

Build on an alternative non-EVM chain. Rejected because: both have significantly smaller ecosystems, fewer wallet options, and less developer tooling than Solana. Sui's Move language has a much smaller developer community. Cosmos requires running a full application-specific chain, which is overkill for a single escrow program.
