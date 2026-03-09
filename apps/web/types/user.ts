// View model for API JSON responses. Proto source: packages/schema/proto/api/v1/user.proto
// Enums re-exported from @/types/proto; enriched fields are web-layer only.

export { UserRole, UserStatus } from "./proto";

export interface User {
  id: string;
  wallet_address: string;
  email: string | null;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  role: "CLIENT" | "FREELANCER";
  created_at: string;
}
