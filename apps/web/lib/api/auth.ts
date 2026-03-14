import { apiGet, apiPost } from "./client";
import type { User } from "@/types/user";

interface NonceResponse {
  nonce: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  user: User;
}

export function fetchNonce(walletAddress: string): Promise<NonceResponse> {
  return apiGet<NonceResponse>(
    `/v1/auth/nonce?wallet_address=${encodeURIComponent(walletAddress)}`,
  );
}

export function authenticateWallet(
  walletAddress: string,
  message: string,
  signature: string,
): Promise<AuthResponse> {
  return apiPost<AuthResponse>("/v1/auth/wallet", {
    wallet_address: walletAddress,
    message,
    signature,
  });
}

export function loginWithEmail(
  email: string,
  password: string,
): Promise<AuthResponse> {
  return apiPost<AuthResponse>("/v1/auth/email/login", { email, password });
}
