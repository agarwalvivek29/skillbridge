"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAccount, useConnect } from "wagmi";
import { Wallet, Mail, ArrowRight, Shield, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { InstallWalletPrompt } from "@/components/web3/InstallWalletPrompt";
import { NetworkSwitchPrompt } from "@/components/web3/NetworkSwitchPrompt";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/lib/stores/auth";

const TARGET_CHAIN_ID = Number(process.env.NEXT_PUBLIC_BASE_CHAIN_ID ?? 84532);

export default function AuthPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const { address, isConnected, chain } = useAccount();
  const { connect, connectors, isPending: isConnecting } = useConnect();
  const { step, error, isLoading, startSiwe, login, reset } = useAuth();

  const [showEmail, setShowEmail] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (token && user) {
      if (user.display_name) {
        router.replace("/dashboard");
      } else {
        router.replace("/onboarding");
      }
    }
  }, [token, user, router]);

  // Auto-advance to SIWE signing when wallet connects
  useEffect(() => {
    if (isConnected && address && step === "connect") {
      reset();
    }
  }, [isConnected, address, step, reset]);

  const hasWallet =
    typeof window !== "undefined" && typeof window.ethereum !== "undefined";
  const wrongNetwork = isConnected && chain && chain.id !== TARGET_CHAIN_ID;

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError(null);

    if (!email.trim()) {
      setEmailError("Email is required");
      return;
    }
    if (!password) {
      setEmailError("Password is required");
      return;
    }

    await login(email, password);
  };

  return (
    <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4 py-16">
      <div className="w-full max-w-[640px] space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-neutral-800">
            Sign in to SkillBridge
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            Connect your wallet or use email to get started
          </p>
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
                Recommended for Web3 users
              </p>
            </div>
          </div>

          {!hasWallet ? (
            <InstallWalletPrompt />
          ) : wrongNetwork ? (
            <NetworkSwitchPrompt />
          ) : !isConnected ? (
            /* Step 1: Connect wallet */
            <div className="space-y-3">
              {connectors.map((connector) => (
                <Button
                  key={connector.uid}
                  variant="web3"
                  size="lg"
                  className="w-full"
                  loading={isConnecting}
                  onClick={() => connect({ connector })}
                >
                  <Wallet className="h-5 w-5" />
                  Connect with {connector.name}
                </Button>
              ))}
            </div>
          ) : step === "sign" || step === "connect" ? (
            /* Step 2: Sign SIWE message */
            <div className="space-y-4">
              <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
                <div className="flex items-start gap-3">
                  <Shield className="mt-0.5 h-5 w-5 text-primary-500" />
                  <div>
                    <p className="text-sm font-medium text-neutral-700">
                      Verify your identity
                    </p>
                    <p className="mt-1 text-sm text-neutral-500">
                      Sign a message with your wallet to prove ownership of{" "}
                      <span className="font-mono text-xs text-neutral-600">
                        {address?.slice(0, 6)}...{address?.slice(-4)}
                      </span>
                    </p>
                  </div>
                </div>
              </div>
              <Button
                variant="web3"
                size="lg"
                className="w-full"
                loading={isLoading}
                onClick={startSiwe}
              >
                <ArrowRight className="h-5 w-5" />
                Sign Message to Continue
              </Button>
            </div>
          ) : step === "verify" ? (
            /* Step 3: Verifying */
            <div className="flex flex-col items-center gap-3 py-4">
              <Spinner size="lg" />
              <p className="text-sm text-neutral-500">
                Verifying your signature...
              </p>
            </div>
          ) : null}

          {/* Wallet error display — only show for wallet-related errors */}
          {error && step !== "connect" && (
            <div className="flex items-start gap-2 rounded-md border border-error-500 bg-error-50 p-3">
              <AlertCircle className="mt-0.5 h-4 w-4 text-error-500" />
              <div className="flex-1">
                <p className="text-sm text-error-500">{error}</p>
                <button
                  onClick={reset}
                  className="mt-1 text-sm font-medium text-error-600 underline hover:no-underline"
                >
                  Try again
                </button>
              </div>
            </div>
          )}
        </Card>

        {/* Divider */}
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-neutral-200" />
          <span className="text-sm text-neutral-400">or</span>
          <div className="h-px flex-1 bg-neutral-200" />
        </div>

        {/* Email Auth */}
        <Card variant="bordered" className="space-y-4">
          <button
            onClick={() => setShowEmail(!showEmail)}
            className="flex w-full items-center gap-3"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <Mail className="h-5 w-5 text-primary-500" />
            </div>
            <div className="text-left">
              <h2 className="text-lg font-semibold text-neutral-800">
                Email Sign-In
              </h2>
              <p className="text-sm text-neutral-500">Use email and password</p>
            </div>
            <ArrowRight
              className={`ml-auto h-5 w-5 text-neutral-400 transition-transform ${
                showEmail ? "rotate-90" : ""
              }`}
            />
          </button>

          {showEmail && (
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <Input
                label="Email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={
                  emailError && !email.trim() ? "Email is required" : undefined
                }
              />
              <Input
                label="Password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                error={
                  emailError && email.trim() && !password
                    ? "Password is required"
                    : undefined
                }
              />
              {error && step === "connect" && (
                <p className="text-sm text-error-500">{error}</p>
              )}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full"
                loading={isLoading}
              >
                Sign In
              </Button>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
