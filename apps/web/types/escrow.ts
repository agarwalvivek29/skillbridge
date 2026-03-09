export interface EscrowTx {
  to: string;
  data: string;
  value: string;
}

export interface EscrowInfo {
  contract_address: string | null;
  total_funded: string;
  balance: string;
  token: string;
}
