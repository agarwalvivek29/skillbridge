"use client";

import { useCallback, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
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

function buildSignInMessage(params: {
  domain: string;
  address: string;
  uri: string;
  nonce: string;
  issuedAt: string;
}): string {
  return [
    `${params.domain} wants you to sign in with your Solana account:`,
    params.address,
    "",
    "Sign in to SkillBridge",
    "",
    `URI: ${params.uri}`,
    `Version: 1`,
    `Nonce: ${params.nonce}`,
    `Issued At: ${params.issuedAt}`,
  ].join("\n");
}

export function useAuth(): UseAuthReturn {
  const { publicKey, connected, signMessage } = useWallet();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [step, setStep] = useState<AuthStep>(connected ? "sign" : "connect");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const startSiwe = useCallback(async () => {
    if (!publicKey || !signMessage) {
      setError("Wallet not connected or does not support message signing");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      setStep("sign");
      const { nonce } = await fetchNonce();

      const domain =
        process.env.NEXT_PUBLIC_AUTH_DOMAIN ??
        (typeof window !== "undefined" ? window.location.host : "localhost");
      const uri =
        typeof window !== "undefined"
          ? window.location.origin
          : "http://localhost:3000";

      const address = publicKey.toBase58();
      const message = buildSignInMessage({
        domain,
        address,
        uri,
        nonce,
        issuedAt: new Date().toISOString(),
      });

      const encodedMessage = new TextEncoder().encode(message);
      const signatureBytes = await signMessage(encodedMessage);
      const signature = btoa(String.fromCharCode(...signatureBytes));

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
  }, [publicKey, signMessage, setAuth]);

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
    setStep(connected ? "sign" : "connect");
  }, [connected]);

  return { step, error, isLoading, startSiwe, login, reset };
}
