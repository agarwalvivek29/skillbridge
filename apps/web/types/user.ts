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
