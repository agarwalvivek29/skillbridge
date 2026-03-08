"use client";

import { useState } from "react";
import { User, Wallet, Bell, Shield, LogOut, Save } from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Tabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Badge } from "@/components/ui/Badge";
import { AddressDisplay } from "@/components/web3/AddressDisplay";
import { useAuthStore } from "@/lib/stores/auth";
import { apiPut } from "@/lib/api/client";
import { cn } from "@/lib/utils";

function ProfileSettings() {
  const user = useAuthStore((s) => s.user);
  const setAuth = useAuthStore((s) => s.setAuth);
  const token = useAuthStore((s) => s.token);
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [bio, setBio] = useState(user?.bio ?? "");
  const [skills, setSkills] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await apiPut<typeof user>("/v1/users/profile", {
        display_name: displayName,
        bio,
        skills: skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      if (token && updated) setAuth(token, updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // Error handled silently
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-neutral-700">
          Avatar
        </label>
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-100 text-2xl font-semibold text-primary-700">
            {displayName?.charAt(0)?.toUpperCase() ?? "?"}
          </div>
          <input
            type="file"
            accept="image/*"
            className="text-sm text-neutral-600"
          />
        </div>
      </div>
      <Input
        label="Display Name"
        value={displayName}
        onChange={(e) => setDisplayName(e.target.value)}
      />
      <Textarea
        label="Bio"
        value={bio}
        onChange={(e) => setBio(e.target.value)}
        placeholder="Tell us about yourself..."
      />
      <Input
        label="Skills (comma separated)"
        value={skills}
        onChange={(e) => setSkills(e.target.value)}
        placeholder="React, Solidity, TypeScript"
      />
      <div className="flex items-center gap-3">
        <Button type="submit" variant="primary" loading={saving}>
          <Save className="mr-1.5 h-4 w-4" />
          Save Changes
        </Button>
        {saved && (
          <span className="text-sm text-success-600">Changes saved!</span>
        )}
      </div>
    </form>
  );
}

function WalletSettings() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-sm font-semibold text-neutral-800">
          Connected Wallet
        </h3>
        <div className="mt-3 flex items-center justify-between">
          {user?.wallet_address ? (
            <AddressDisplay address={user.wallet_address} />
          ) : (
            <span className="text-sm text-neutral-500">
              No wallet connected
            </span>
          )}
          <Badge variant="success">Connected</Badge>
        </div>
      </Card>
      <Card>
        <h3 className="text-sm font-semibold text-neutral-800">
          Additional Wallets
        </h3>
        <p className="mt-2 text-sm text-neutral-500">
          Connect additional wallets to link them to your account.
        </p>
        <Button variant="outline" size="sm" className="mt-3">
          <Wallet className="mr-1.5 h-4 w-4" />
          Connect Another Wallet
        </Button>
      </Card>
    </div>
  );
}

function NotificationSettings() {
  const notificationTypes = [
    { key: "PROPOSAL_RECEIVED", label: "New proposals" },
    { key: "PROPOSAL_ACCEPTED", label: "Proposal accepted" },
    { key: "SUBMISSION_RECEIVED", label: "New submissions" },
    { key: "REVIEW_COMPLETE", label: "AI review complete" },
    { key: "MILESTONE_APPROVED", label: "Milestone approved" },
    { key: "REVISION_REQUESTED", label: "Revision requested" },
    { key: "DISPUTE_FILED", label: "Disputes" },
    { key: "DISPUTE_RESOLVED", label: "Dispute resolved" },
  ];

  const [toggles, setToggles] = useState<Record<string, boolean>>(
    Object.fromEntries(notificationTypes.map((t) => [t.key, true])),
  );
  const [emailEnabled, setEmailEnabled] = useState(false);

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-sm font-semibold text-neutral-800">
          In-App Notifications
        </h3>
        <div className="mt-4 space-y-3">
          {notificationTypes.map((type) => (
            <label key={type.key} className="flex items-center justify-between">
              <span className="text-sm text-neutral-700">{type.label}</span>
              <button
                type="button"
                role="switch"
                aria-checked={toggles[type.key]}
                onClick={() =>
                  setToggles((prev) => ({
                    ...prev,
                    [type.key]: !prev[type.key],
                  }))
                }
                className={cn(
                  "relative h-6 w-10 rounded-full transition-colors",
                  toggles[type.key] ? "bg-primary-600" : "bg-neutral-300",
                )}
              >
                <span
                  className={cn(
                    "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                    toggles[type.key] ? "left-[18px]" : "left-0.5",
                  )}
                />
              </button>
            </label>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-neutral-800">
          Email Notifications
        </h3>
        <label className="mt-4 flex items-center justify-between">
          <span className="text-sm text-neutral-700">
            Receive email for important updates
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={emailEnabled}
            onClick={() => setEmailEnabled(!emailEnabled)}
            className={cn(
              "relative h-6 w-10 rounded-full transition-colors",
              emailEnabled ? "bg-primary-600" : "bg-neutral-300",
            )}
          >
            <span
              className={cn(
                "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                emailEnabled ? "left-[18px]" : "left-0.5",
              )}
            />
          </button>
        </label>
      </Card>
    </div>
  );
}

function SecuritySettings() {
  const clearAuth = useAuthStore((s) => s.clearAuth);

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-sm font-semibold text-neutral-800">
          Active Sessions
        </h3>
        <p className="mt-2 text-sm text-neutral-500">
          You are currently signed in on this device.
        </p>
        <div className="mt-4 flex items-center justify-between rounded-md border border-neutral-200 px-4 py-3">
          <div className="flex items-center gap-3">
            <Shield className="h-5 w-5 text-success-500" />
            <div>
              <p className="text-sm font-medium text-neutral-800">
                Current Session
              </p>
              <p className="text-xs text-neutral-500">Active now</p>
            </div>
          </div>
          <Badge variant="success">Active</Badge>
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-neutral-800">Sign Out</h3>
        <p className="mt-2 text-sm text-neutral-500">
          Sign out of all active sessions.
        </p>
        <Button
          variant="destructive"
          size="sm"
          className="mt-4"
          onClick={clearAuth}
        >
          <LogOut className="mr-1.5 h-4 w-4" />
          Sign Out All Sessions
        </Button>
      </Card>
    </div>
  );
}

function SettingsContent() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-neutral-800">Settings</h1>
      <Tabs
        tabs={[
          {
            value: "profile",
            label: "Profile",
            content: <ProfileSettings />,
          },
          {
            value: "wallet",
            label: "Wallet",
            content: <WalletSettings />,
          },
          {
            value: "notifications",
            label: "Notifications",
            content: <NotificationSettings />,
          },
          {
            value: "security",
            label: "Security",
            content: <SecuritySettings />,
          },
        ]}
      />
    </div>
  );
}

export default function SettingsPage() {
  return (
    <AuthGuard>
      <DashboardLayout>
        <SettingsContent />
      </DashboardLayout>
    </AuthGuard>
  );
}
