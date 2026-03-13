export interface EscrowTx {
  /** Base64-encoded serialized Solana transaction */
  serialized_tx: string;
}

export interface EscrowInfo {
  program_address: string | null;
  total_funded: string;
  balance: string;
  token: string;
}
