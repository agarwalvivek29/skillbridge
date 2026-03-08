import { apiGet, apiPost } from "./client";
import type { User } from "@/types/user";

interface NonceResponse {
  nonce: string;
}

interface SiweAuthResponse {
  access_token: string;
  user: User;
}

interface LoginResponse {
  access_token: string;
  user: User;
}

export function fetchNonce(): Promise<NonceResponse> {
  return apiGet<NonceResponse>("/v1/auth/nonce");
}

export function authenticateSiwe(
  message: string,
  signature: string,
): Promise<SiweAuthResponse> {
  return apiPost<SiweAuthResponse>("/v1/auth/siwe", { message, signature });
}

export function loginWithEmail(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiPost<LoginResponse>("/v1/auth/login", { email, password });
}
