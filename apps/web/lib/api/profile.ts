import { apiGet } from "./client";
import type { PublicProfile } from "@/types/profile";

export function getPublicProfile(address: string): Promise<PublicProfile> {
  return apiGet<PublicProfile>(`/v1/users/${address}/profile`);
}
