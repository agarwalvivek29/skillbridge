/**
 * @proto packages/schema/proto/contracts/v1/escrow.proto — EscrowContract
 *
 * Frontend-only / API-enriched fields:
 *   serialized_tx — API-enriched (base64-encoded Solana transaction for client signing)
 */
export interface EscrowTx {
  /** Base64-encoded serialized Solana transaction */
  serialized_tx: string;
}

/**
 * @proto packages/schema/proto/contracts/v1/escrow.proto — EscrowContract
 *
 * Field mappings:
 *   program_address ← proto EscrowContract.chain_address
 *   total_funded    ← proto EscrowContract.total_amount
 *   token           ← proto EscrowContract.token_address
 *
 * Frontend-only / API-enriched fields:
 *   balance — API-enriched (computed as total_amount - released_amount)
 *
 * Proto fields NOT mapped:
 *   EscrowContract.id, EscrowContract.gig_id, EscrowContract.network,
 *   EscrowContract.released_amount, EscrowContract.status,
 *   EscrowContract.platform_fee_basis_points, EscrowContract.platform_fee_amount,
 *   EscrowContract.platform_fee_recipient, EscrowContract.funding_tx_hash,
 *   EscrowContract.created_at, EscrowContract.funded_at, EscrowContract.settled_at
 */
export interface EscrowInfo {
  program_address: string | null;
  total_funded: string;
  balance: string;
  token: string;
}
