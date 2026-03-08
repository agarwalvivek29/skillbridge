"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  ListChecks,
  Users,
  FileText,
  Settings,
  AlertTriangle,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Spinner,
  StatusBadge,
  EmptyState,
  Tabs,
  Modal,
} from "@/components/ui";
import { ProposalCard } from "@/components/proposals/ProposalCard";
import { useToast } from "@/hooks/useToast";
import {
  fetchGig,
  fetchGigProposals,
  fetchGigSubmissions,
  deleteGig,
  type GigSubmission,
} from "@/lib/api/gigs";
import type { Gig } from "@/types/gig";
import type { Proposal } from "@/types/proposal";

function ManageContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();

  const [gig, setGig] = useState<Gig | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [submissions, setSubmissions] = useState<GigSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const load = useCallback(async () => {
    try {
      const [g, p, s] = await Promise.all([
        fetchGig(params.id),
        fetchGigProposals(params.id)
          .then((r) => r.proposals)
          .catch(() => []),
        fetchGigSubmissions(params.id).catch(() => []),
      ]);
      setGig(g);
      setProposals(p);
      setSubmissions(s);
    } catch {
      toast.error("Failed to load gig");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  function handleProposalUpdate(updated: Proposal) {
    setProposals((prev) =>
      prev.map((p) => (p.id === updated.id ? updated : p)),
    );
    load();
  }

  async function handleCancel() {
    setCancelling(true);
    try {
      await deleteGig(params.id);
      toast.success("Gig cancelled");
      router.push("/gigs");
    } catch {
      toast.error("Failed to cancel gig");
    } finally {
      setCancelling(false);
      setCancelOpen(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!gig) {
    return (
      <div className="py-20 text-center text-neutral-500">Gig not found.</div>
    );
  }

  const completedMilestones = gig.milestones.filter(
    (m) => m.status === "APPROVED" || m.status === "PAID",
  ).length;

  const overviewTab = (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card variant="flat">
          <p className="text-sm text-neutral-500">Status</p>
          <div className="mt-1">
            <StatusBadge status={gig.status} />
          </div>
        </Card>
        <Card variant="flat">
          <p className="text-sm text-neutral-500">Total Budget</p>
          <p className="mt-1 text-xl font-bold text-neutral-900">
            {gig.total_amount} {gig.currency}
          </p>
        </Card>
        <Card variant="flat">
          <p className="text-sm text-neutral-500">Milestones</p>
          <p className="mt-1 text-xl font-bold text-neutral-900">
            {completedMilestones} / {gig.milestones.length}
          </p>
        </Card>
      </div>

      <Card variant="bordered">
        <h3 className="font-semibold text-neutral-800">Description</h3>
        <p className="mt-2 whitespace-pre-wrap text-sm text-neutral-600">
          {gig.description}
        </p>
      </Card>
    </div>
  );

  const milestonesTab = (
    <div className="space-y-3">
      {gig.milestones.length === 0 ? (
        <EmptyState
          icon={ListChecks}
          title="No milestones"
          description="This gig has no milestones defined."
        />
      ) : (
        gig.milestones.map((m, i) => (
          <button
            key={m.id}
            onClick={() => router.push(`/gigs/${params.id}/milestones/${m.id}`)}
            className="w-full rounded-lg border border-neutral-200 bg-white p-4 text-left transition-shadow hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-neutral-700">
                  {i + 1}. {m.title}
                </p>
                {m.description && (
                  <p className="mt-0.5 text-sm text-neutral-500 line-clamp-1">
                    {m.description}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-neutral-900">
                  {m.amount} {m.currency}
                </span>
                <StatusBadge status={m.status} />
              </div>
            </div>
          </button>
        ))
      )}
    </div>
  );

  const proposalsTab = (
    <div className="space-y-4">
      {proposals.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No proposals yet"
          description="Proposals from freelancers will appear here."
        />
      ) : (
        proposals.map((p) => (
          <ProposalCard
            key={p.id}
            proposal={p}
            onUpdate={handleProposalUpdate}
          />
        ))
      )}
    </div>
  );

  const submissionsTab = (
    <div className="space-y-3">
      {submissions.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No submissions"
          description="Work submissions will appear here as milestones are completed."
        />
      ) : (
        submissions.map((s) => (
          <Card key={s.id} variant="flat">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-neutral-700">
                  {s.milestone_title}
                </p>
                <p className="text-xs text-neutral-500">
                  {new Date(s.created_at).toLocaleDateString()}
                </p>
              </div>
              <StatusBadge status={s.status} />
            </div>
            {s.notes && (
              <p className="mt-2 text-sm text-neutral-600">{s.notes}</p>
            )}
          </Card>
        ))
      )}
    </div>
  );

  const settingsTab = (
    <div className="space-y-6">
      <Card variant="bordered">
        <h3 className="font-semibold text-neutral-800">Gig Settings</h3>
        <p className="mt-1 text-sm text-neutral-500">
          Manage your gig configuration
        </p>
        <div className="mt-4">
          <Button
            variant="outline"
            onClick={() => router.push(`/gigs/${params.id}/edit`)}
          >
            Edit Gig Details
          </Button>
        </div>
      </Card>

      <Card variant="bordered" className="border-error-200">
        <h3 className="font-semibold text-error-600">Danger Zone</h3>
        <p className="mt-1 text-sm text-neutral-500">
          Cancel this gig. This cannot be undone.
        </p>
        <div className="mt-4">
          <Button variant="destructive" onClick={() => setCancelOpen(true)}>
            Cancel Gig
          </Button>
        </div>
      </Card>

      <Modal
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        title="Cancel Gig"
        footer={
          <>
            <Button variant="ghost" onClick={() => setCancelOpen(false)}>
              Keep Gig
            </Button>
            <Button
              variant="destructive"
              loading={cancelling}
              onClick={handleCancel}
            >
              Yes, Cancel Gig
            </Button>
          </>
        }
      >
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning-500" />
          <p className="text-sm text-neutral-600">
            Are you sure you want to cancel{" "}
            <strong>&quot;{gig.title}&quot;</strong>? Any escrowed funds will be
            returned, and active proposals will be rejected.
          </p>
        </div>
      </Modal>
    </div>
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 md:px-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800">{gig.title}</h1>
          <div className="mt-2 flex items-center gap-3">
            <StatusBadge status={gig.status} />
            <span className="text-sm text-neutral-500">
              {gig.milestones.length} milestone
              {gig.milestones.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </div>

      <Tabs
        tabs={[
          {
            value: "overview",
            label: "Overview",
            content: overviewTab,
          },
          {
            value: "milestones",
            label: "Milestones",
            content: milestonesTab,
          },
          {
            value: "proposals",
            label: `Proposals (${proposals.length})`,
            content: proposalsTab,
          },
          {
            value: "submissions",
            label: "Submissions",
            content: submissionsTab,
          },
          {
            value: "settings",
            label: "Settings",
            content: settingsTab,
          },
        ]}
      />
    </div>
  );
}

export default function ManageGigPage() {
  return (
    <AuthGuard>
      <ManageContent />
    </AuthGuard>
  );
}
