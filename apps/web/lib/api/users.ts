import { apiPost } from "./client";
import type { User } from "@/types/user";

export interface ProfilePayload {
  role: "CLIENT" | "FREELANCER";
  display_name: string;
  bio: string;
  skills: string[];
  location?: string;
  avatar_url?: string;
  company_name?: string;
  website?: string;
  hourly_rate?: number;
  portfolio_url?: string;
  github_username?: string;
}

export function createProfile(payload: ProfilePayload): Promise<User> {
  return apiPost<User>("/v1/users/profile", payload);
}
