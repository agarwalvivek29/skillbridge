// View model for API JSON responses. Proto source: packages/schema/proto/contracts/v1/escrow.proto
// Enums re-exported from @/types/proto; enriched fields are web-layer only.

export { EscrowStatus } from "./proto";

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
