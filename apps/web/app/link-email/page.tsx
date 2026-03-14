"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Mail, ArrowRight, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { useAuthStore } from "@/lib/stores/auth";
import { linkEmail } from "@/lib/api/users";

export default function LinkEmailPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const setAuth = useAuthStore((s) => s.setAuth);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!token || !user) {
      router.replace("/auth");
    }
  }, [token, user, router]);

  // Redirect if email already linked
  useEffect(() => {
    if (user?.email) {
      router.replace("/onboarding");
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Email is required");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setIsLoading(true);
    try {
      await linkEmail(email, password);
      // Update the user in auth store with the new email
      if (user) {
        setAuth(token!, { ...user, email });
      }
      router.replace("/onboarding");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to link email";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  if (!token || !user) return null;

  return (
    <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4 py-16">
      <div className="w-full max-w-[640px] space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-neutral-800">
            Link Your Email
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            Add an email and password for notifications and account recovery
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 text-xs text-neutral-400">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500 text-white font-medium">
            <CheckCircle className="h-4 w-4" />
          </span>
          <span className="text-green-600 font-medium">Wallet Connected</span>
          <div className="h-px w-8 bg-neutral-300" />
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-500 text-white font-medium">
            2
          </span>
          <span className="font-medium text-primary-500">Link Email</span>
          <div className="h-px w-8 bg-neutral-300" />
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-200 text-neutral-500 font-medium">
            3
          </span>
          <span>Set Up Profile</span>
        </div>

        {/* Email Form */}
        <Card variant="bordered" className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <Mail className="h-5 w-5 text-primary-500" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-neutral-800">
                Email & Password
              </h2>
              <p className="text-sm text-neutral-500">
                Used for notifications, password recovery, and as an alternative
                login method
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              label="Password"
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Input
              label="Confirm Password"
              type="password"
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />

            {error && (
              <div className="flex items-start gap-2 rounded-md border border-error-500 bg-error-50 p-3">
                <AlertCircle className="mt-0.5 h-4 w-4 text-error-500" />
                <p className="text-sm text-error-500">{error}</p>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              loading={isLoading}
            >
              <ArrowRight className="h-5 w-5" />
              Continue to Profile Setup
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
