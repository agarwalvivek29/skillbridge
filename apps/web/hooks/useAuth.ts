"use client";

import { useCallback, useState } from "react";
import { useAccount, useSignMessage } from "wagmi";
import { useAuthStore } from "@/lib/stores/auth";
import { fetchNonce, authenticateSiwe, loginWithEmail } from "@/lib/api/auth";

type AuthStep = "connect" | "sign" | "verify" | "done";

interface UseAuthReturn {
  step: AuthStep;
  error: string | null;
  isLoading: boolean;
  startSiwe: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  reset: () => void;
}

function buildSiweMessage(params: {
  domain: string;
  address: string;
  uri: string;
  chainId: number;
  nonce: string;
  issuedAt: string;
}): string {
  return [
    `${params.domain} wants you to sign in with your Ethereum account:`,
    params.address,
    "",
    "Sign in to SkillBridge",
    "",
    `URI: ${params.uri}`,
    `Version: 1`,
    `Chain ID: ${params.chainId}`,
    `Nonce: ${params.nonce}`,
    `Issued At: ${params.issuedAt}`,
  ].join("\n");
}

export function useAuth(): UseAuthReturn {
  const { address, chainId, isConnected } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [step, setStep] = useState<AuthStep>(isConnected ? "sign" : "connect");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const startSiwe = useCallback(async () => {
    if (!address || !chainId) {
      setError("Wallet not connected");
      return;
    }

    const expectedChainId = parseInt(
      process.env.NEXT_PUBLIC_BASE_CHAIN_ID ?? "84532",
    );
    if (chainId !== expectedChainId) {
      setError("Please switch to the Base network before signing in");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      setStep("sign");
      const { nonce } = await fetchNonce();

      const domain =
        process.env.NEXT_PUBLIC_SIWE_DOMAIN ??
        (typeof window !== "undefined" ? window.location.host : "localhost");
      const uri =
        typeof window !== "undefined"
          ? window.location.origin
          : "http://localhost:3000";

      const message = buildSiweMessage({
        domain,
        address,
        uri,
        chainId,
        nonce,
        issuedAt: new Date().toISOString(),
      });

      const signature = await signMessageAsync({ message });

      setStep("verify");
      const result = await authenticateSiwe(message, signature);

      setAuth(result.access_token, result.user);
      setStep("done");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      if (msg.includes("User rejected") || msg.includes("denied")) {
        setError("Signature rejected. Please try again.");
      } else {
        setError(msg);
      }
      setStep("sign");
    } finally {
      setIsLoading(false);
    }
  }, [address, chainId, signMessageAsync, setAuth]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      setIsLoading(true);

      try {
        setStep("verify");
        const result = await loginWithEmail(email, password);
        setAuth(result.access_token, result.user);
        setStep("done");
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Login failed";
        setError(msg);
        setStep("connect");
      } finally {
        setIsLoading(false);
      }
    },
    [setAuth],
  );

  const reset = useCallback(() => {
    setError(null);
    setStep(isConnected ? "sign" : "connect");
  }, [isConnected]);

  return { step, error, isLoading, startSiwe, login, reset };
}
