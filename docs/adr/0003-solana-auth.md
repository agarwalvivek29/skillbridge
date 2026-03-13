# 0003 Replace SIWE with Solana Message Signing

**Date**: 2026-03-13
**Status**: Accepted
**Deciders**: Project team
**Issue**: #72

## Context

SkillBridge originally used Sign-In with Ethereum (SIWE / EIP-4361) for wallet authentication, targeting Base L2 (an EVM chain). The project is migrating to Solana, which uses Ed25519 key pairs instead of secp256k1/ECDSA. The existing SIWE verification library (`siwe` + `eth-account`) cannot verify Solana wallet signatures.

## Decision

We will replace SIWE signature verification with Solana-native Ed25519 message signing:

1. Use `PyNaCl` (libsodium bindings) for Ed25519 signature verification
2. Use `base58` for decoding Solana public keys (base58-encoded, not hex)
3. Define a simple plaintext message format (nonce + timestamp) instead of EIP-4361 structured messages
4. Remove `siwe` and `eth-account` dependencies
5. Remove the `SIWE_DOMAIN` config parameter (domain binding is an EIP-4361 concept with no Solana equivalent)

## Consequences

### Positive

- Auth layer aligns with Solana wallet ecosystem
- Simpler message format (no EIP-4361 parsing overhead)
- `PyNaCl` is a well-maintained, widely-used cryptography library
- Smaller dependency footprint (removes `eth-account` and its transitive deps)

### Negative

- No structured message standard equivalent to EIP-4361 for Solana (we define our own format)
- Frontend must be updated to use Solana wallet adapters instead of wagmi/viem (separate issue)

### Neutral

- Nonce-based replay protection remains identical
- JWT issuance and middleware are unaffected

## Alternatives Considered

### Option A: `solders` Python package

The `solders` package provides Solana-native types including signature verification. Rejected because PyNaCl is more widely used, has fewer dependencies, and Ed25519 verification is framework-agnostic.

### Option B: Keep SIWE and add Solana as a second auth method

Would allow both Ethereum and Solana wallets. Rejected because the project is fully migrating to Solana; maintaining two verification paths adds complexity with no benefit.
