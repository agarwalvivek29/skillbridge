# Spec: Replace SIWE with Solana Message Signing

> **Issue**: #72
> **Status**: Approved
> **Author**: ao agent
> **Date**: 2026-03-13
> **Services Affected**: `services/api`, `apps/web`

---

## Summary

Replace Sign-In with Ethereum (SIWE / EIP-4361) wallet authentication with Solana wallet message signing (Ed25519). The nonce flow remains identical; only the signature verification algorithm and wallet address format change.

---

## Background and Motivation

The project is migrating from Ethereum/Base L2 to Solana. The wallet authentication flow must use Ed25519 signatures (Solana's native signing scheme) instead of secp256k1/ECDSA (Ethereum). This aligns the auth layer with the new blockchain target.

---

## Scope

### In Scope

- Replace `siwe` + `eth-account` signature verification with `PyNaCl` + `base58` Ed25519 verification in `services/api`
- Update nonce endpoint to accept base58 Solana addresses instead of `0x`-prefixed hex addresses
- Update `pyproject.toml` dependencies (remove `siwe`, `eth-account`; add `PyNaCl`, `base58`)
- Remove `siwe_domain` from config (not needed for Solana message signing)
- Update unit tests (`test_siwe.py` -> Solana signature tests)
- Update e2e tests to use Ed25519 test keypairs
- Update proto comment (cosmetic: "SIWE" -> "Solana message signing")
- Update `ARCHITECTURE.md` auth strategy section
- Update `AGENTS.md` for the api service
- Update `.env.example` (remove `SIWE_DOMAIN`)

### Out of Scope

- Frontend wallet integration changes (separate issue)
- Solana smart contract escrow migration
- Mobile wallet support

---

## Acceptance Criteria

- [ ] `GET /v1/auth/nonce?wallet_address=<base58_addr>` accepts base58 Solana addresses (32-44 chars)
- [ ] `POST /v1/auth/wallet` verifies Ed25519 signature using PyNaCl, issues JWT
- [ ] Invalid Ed25519 signatures are rejected with 401
- [ ] Nonce message format uses "Solana account" wording
- [ ] `siwe` and `eth-account` are removed from dependencies
- [ ] `PyNaCl` and `base58` are added to dependencies
- [ ] `SIWE_DOMAIN` config removed
- [ ] Unit tests cover: valid Ed25519 signature, wrong address, wrong nonce, garbage signature
- [ ] E2E tests cover: wallet login happy path, invalid signature rejection, nonce consumption
- [ ] All existing email auth tests still pass

---

## Technical Design

### Signature Verification

```python
import nacl.signing
import base58
import base64

def verify_solana_signature(message: str, signature: str, wallet_address: str) -> bool:
    pubkey_bytes = base58.b58decode(wallet_address)
    sig_bytes = base64.b64decode(signature)
    verify_key = nacl.signing.VerifyKey(pubkey_bytes)
    verify_key.verify(message.encode('utf-8'), sig_bytes)
    return True
```

### Nonce Message Format

```
SkillBridge wants you to sign in with your Solana account:
{base58_wallet_address}

Nonce: {random_nonce}
Issued At: {iso_timestamp}
```

### Dependencies

Removed: `siwe>=4.0.0`, `eth-account>=0.11.0`
Added: `PyNaCl>=1.5.0`, `base58>=2.1.0`

---

## Security Considerations

- Ed25519 signatures are at least as secure as secp256k1/ECDSA
- Nonce replay protection unchanged (nonce consumed on use, 10-min TTL)
- No domain binding (Solana message signing has no EIP-4361 equivalent); nonce + timestamp provide replay protection

---

## Testing Plan

### Unit Tests

- `test_solana_auth.py`: valid signature, wrong address, wrong nonce, garbage signature, non-matching message

### E2E Tests

- `test_auth.py`: full wallet login flow with Ed25519 test keypair

---

## References

- Related ADR: [ADR 0003](../adr/0003-solana-auth.md)
- Proto: `packages/schema/proto/api/v1/auth.proto`
- Issue: #72
