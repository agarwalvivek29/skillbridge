/**
 * @proto packages/schema/proto/api/v1/user.proto — User, UserPublic
 *
 * Field mappings:
 *   display_name     ← proto User.name / UserPublic.name
 *   wallet_address   = proto User.wallet_address
 *   email            = proto User.email (not on UserPublic)
 *   bio              = proto User.bio
 *   avatar_url       = proto User.avatar_url
 *   role             = proto User.role (enum UserRole mapped to string union)
 *   created_at       = proto User.created_at (Timestamp → ISO string)
 *
 * Proto fields NOT mapped to this interface:
 *   User.status, User.skills, User.hourly_rate_wei, User.updated_at
 *
 * Frontend-only fields (not in proto):
 *   (none — all fields derive from proto)
 */
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
