"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useWallet } from "@solana/wallet-adapter-react";
import { useWalletModal } from "@solana/wallet-adapter-react-ui";
import { WalletReadyState } from "@solana/wallet-adapter-base";
import { Wallet, Shield, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { InstallWalletPrompt } from "@/components/web3/InstallWalletPrompt";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/lib/stores/auth";

export default function AuthPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const { publicKey, connected, wallets, signMessage } = useWallet();
  const { setVisible } = useWalletModal();
  const { step, error, isLoading, startSiwe, reset } = useAuth();

  const [mounted, setMounted] = useState(false);
  const autoSignTriggered = useRef(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Redirect if already authenticated
  useEffect(() => {
    if (token && user) {
      if (!user.email) {
        router.replace("/link-email");
      } else if (!user.display_name) {
        router.replace("/onboarding");
      } else {
        router.replace("/dashboard");
      }
    }
  }, [token, user, router]);

  // Auto-sign as soon as wallet connects AND signMessage is available.
  // Short delay lets the wallet connection modal fully close before
  // triggering the signature popup — Edge drops it without the delay.
  useEffect(() => {
    console.log("[auth] effect check:", {
      connected,
      publicKey: publicKey?.toBase58()?.slice(0, 8),
      signMessage: typeof signMessage,
      token: !!token,
      isLoading,
      autoSignTriggered: autoSignTriggered.current,
    });

    if (
      connected &&
      publicKey &&
      signMessage &&
      !token &&
      !isLoading &&
      !autoSignTriggered.current
    ) {
      console.log("[auth] all conditions met — scheduling startSiwe in 500ms");
      autoSignTriggered.current = true;
      const timer = setTimeout(() => {
        console.log("[auth] firing startSiwe now");
        startSiwe();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [connected, publicKey, signMessage, token, isLoading, startSiwe]);

  // Reset the auto-sign guard if there's an error so retry works
  useEffect(() => {
    if (error) {
      console.log("[auth] error detected, resetting autoSignTriggered:", error);
      autoSignTriggered.current = false;
    }
  }, [error]);

  const hasWallet =
    mounted && wallets.some((w) => w.readyState === WalletReadyState.Installed);

  return (
    <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4 py-16">
      <div className="w-full max-w-[640px] space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-neutral-800">
            Sign in to SkillBridge
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            Connect your Solana wallet to get started
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 text-xs text-neutral-400">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-500 text-white font-medium">
            1
          </span>
          <span className="font-medium text-primary-500">Connect & Sign</span>
          <div className="h-px w-8 bg-neutral-300" />
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-200 text-neutral-500 font-medium">
            2
          </span>
          <span>Link Email</span>
          <div className="h-px w-8 bg-neutral-300" />
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-200 text-neutral-500 font-medium">
            3
          </span>
          <span>Set Up Profile</span>
        </div>

        {/* Wallet Auth */}
        <Card variant="bordered" className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-web3-50">
              <Wallet className="h-5 w-5 text-web3-500" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-neutral-800">
                Wallet Sign-In
              </h2>
              <p className="text-sm text-neutral-500">
                One click — connect and verify in a single step
              </p>
            </div>
          </div>

          {!hasWallet ? (
            <InstallWalletPrompt />
          ) : !connected ? (
            /* Not connected — show connect button */
            <div className="space-y-4">
              <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
                <div className="flex items-start gap-3">
                  <Shield className="mt-0.5 h-5 w-5 text-primary-500" />
                  <div>
                    <p className="text-sm font-medium text-neutral-700">
                      Secure sign-in
                    </p>
                    <p className="mt-1 text-sm text-neutral-500">
                      Select your wallet, then approve a signature to verify
                      ownership. No funds are transferred.
                    </p>
                  </div>
                </div>
              </div>
              <Button
                variant="web3"
                size="lg"
                className="w-full"
                onClick={() => setVisible(true)}
              >
                <Wallet className="h-5 w-5" />
                Connect Wallet & Sign In
              </Button>
            </div>
          ) : isLoading || step === "verify" ? (
            /* Signing / verifying in progress */
            <div className="flex flex-col items-center gap-3 py-6">
              <Spinner size="lg" />
              <p className="text-sm text-neutral-500">
                {step === "verify"
                  ? "Verifying your signature..."
                  : "Requesting signature from wallet..."}
              </p>
            </div>
          ) : step === "done" ? (
            /* Authenticated — redirecting */
            <div className="flex flex-col items-center gap-3 py-6">
              <CheckCircle className="h-10 w-10 text-green-500" />
              <p className="text-sm font-medium text-neutral-700">
                Signed in successfully! Redirecting...
              </p>
            </div>
          ) : null}

          {/* Error state with retry */}
          {error && (
            <div className="flex items-start gap-2 rounded-md border border-error-500 bg-error-50 p-3">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-error-500" />
              <div className="flex-1">
                <p className="text-sm text-error-500">{error}</p>
                <button
                  onClick={() => {
                    reset();
                    startSiwe();
                  }}
                  className="mt-1 text-sm font-medium text-error-600 underline hover:no-underline"
                >
                  Try again
                </button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
