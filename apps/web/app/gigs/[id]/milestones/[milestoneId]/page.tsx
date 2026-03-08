"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  FileText,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Clock,
  MessageSquare,
  ArrowRight,
} from "lucide-react";
import { useSendTransaction, useWaitForTransactionReceipt } from "wagmi";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Spinner,
  StatusBadge,
  Textarea,
  Modal,
  EmptyState,
  Breadcrumb,
} from "@/components/ui";
import { TxPending, TxSuccess, TxFailed } from "@/components/web3";
import { useToast } from "@/hooks/useToast";
import { useAuthStore } from "@/lib/stores/auth";
import {
  fetchMilestone,
  getReleaseTx,
  confirmRelease,
  requestRevision,
} from "@/lib/api/submissions";
import type { MilestoneDetail, Submission } from "@/types/submission";

function MilestoneContent() {
  const params = useParams<{ id: string; milestoneId: string }>();
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);

  const [milestone, setMilestone] = useState<MilestoneDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // Approve flow state
  const [approveOpen, setApproveOpen] = useState(false);
  const [approving, setApproving] = useState(false);
  const [txState, setTxState] = useState<
    "idle" | "pending" | "success" | "error"
  >("idle");
  const [txError, setTxError] = useState<string | null>(null);

  // Revision flow state
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [revisionFeedback, setRevisionFeedback] = useState("");
  const [revising, setRevising] = useState(false);

  const {
    sendTransaction,
    data: txHash,
    reset: resetTx,
    isPending: isSending,
  } = useSendTransaction();

  const { isSuccess: txConfirmed, isError: txFailed } =
    useWaitForTransactionReceipt({ hash: txHash });

  const load = useCallback(async () => {
    try {
      const data = await fetchMilestone(params.milestoneId);
      setMilestone(data);
    } catch {
      toast.error("Failed to load milestone");
    } finally {
      setLoading(false);
    }
  }, [params.milestoneId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  // Watch tx confirmation
  useEffect(() => {
    if (txConfirmed && txHash && txState === "pending") {
      setTxState("success");
      confirmRelease(params.milestoneId, txHash)
        .then(() => {
          toast.success("Funds released successfully");
          load();
        })
        .catch(() => toast.error("Failed to confirm release on server"));
    }
    if (txFailed && txState === "pending") {
      setTxState("error");
      setTxError("Transaction failed on chain");
    }
  }, [txConfirmed, txFailed, txHash, txState, params.milestoneId, toast, load]);

  async function handleApprove() {
    setApproving(true);
    try {
      const calldata = await getReleaseTx(params.milestoneId);
      setTxState("pending");
      setApproveOpen(false);
      sendTransaction(
        {
          to: calldata.to as `0x${string}`,
          data: calldata.data as `0x${string}`,
          value: BigInt(calldata.value),
        },
        {
          onError: (err) => {
            setTxState("error");
            setTxError(err.message ?? "Transaction rejected");
          },
        },
      );
    } catch {
      toast.error("Failed to prepare release transaction");
      setTxState("idle");
    } finally {
      setApproving(false);
    }
  }

  async function handleRevision() {
    if (!revisionFeedback.trim()) {
      toast.error("Please describe what needs to be fixed");
      return;
    }
    setRevising(true);
    try {
      await requestRevision(params.milestoneId, revisionFeedback.trim());
      toast.success("Revision requested");
      setRevisionOpen(false);
      setRevisionFeedback("");
      load();
    } catch {
      toast.error("Failed to request revision");
    } finally {
      setRevising(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!milestone) {
    return (
      <div className="py-20 text-center text-neutral-500">
        Milestone not found.
      </div>
    );
  }

  const isClient = user?.id === milestone.client_id;
  const isFreelancer = user?.id === milestone.freelancer_id;
  const canApprove =
    isClient &&
    (milestone.status === "SUBMITTED" || milestone.status === "UNDER_REVIEW");
  const canRevise =
    isClient &&
    (milestone.status === "SUBMITTED" || milestone.status === "UNDER_REVIEW");
  const canSubmit =
    isFreelancer &&
    (milestone.status === "PENDING" ||
      milestone.status === "IN_PROGRESS" ||
      milestone.status === "REVISION_REQUESTED");
  const canDispute =
    milestone.status === "SUBMITTED" || milestone.status === "UNDER_REVIEW";

  const latestSubmission =
    milestone.submissions.length > 0
      ? milestone.submissions[milestone.submissions.length - 1]
      : null;

  // If tx is in progress, show tx states
  if (txState === "pending") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <TxPending txHash={txHash} />
      </div>
    );
  }
  if (txState === "success" && txHash) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <TxSuccess
          txHash={txHash}
          onContinue={() => {
            setTxState("idle");
            resetTx();
            load();
          }}
        />
      </div>
    );
  }
  if (txState === "error") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <TxFailed
          error={txError ?? "Transaction failed"}
          onRetry={() => {
            setTxState("idle");
            setTxError(null);
            resetTx();
          }}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <Breadcrumb
        items={[
          { label: "Gigs", href: "/gigs" },
          { label: milestone.gig_title, href: `/gigs/${params.id}/manage` },
          { label: milestone.title },
        ]}
      />

      {/* Header */}
      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800">
            {milestone.title}
          </h1>
          <div className="mt-2 flex items-center gap-3">
            <StatusBadge status={milestone.status} />
            <span className="text-sm text-neutral-500">
              {milestone.amount} {milestone.currency}
            </span>
          </div>
        </div>
      </div>

      {/* Revision feedback banner */}
      {milestone.status === "REVISION_REQUESTED" &&
        milestone.revision_feedback && (
          <div className="mt-4 rounded-lg border border-warning-200 bg-warning-50 p-4">
            <div className="flex items-start gap-3">
              <MessageSquare className="mt-0.5 h-5 w-5 shrink-0 text-warning-400" />
              <div>
                <p className="text-sm font-medium text-warning-800">
                  Changes Requested
                </p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-warning-800/80">
                  {milestone.revision_feedback}
                </p>
              </div>
            </div>
            {canSubmit && (
              <Button
                variant="primary"
                size="sm"
                className="mt-3"
                onClick={() =>
                  router.push(
                    `/gigs/${params.id}/milestones/${params.milestoneId}/submit`,
                  )
                }
              >
                Submit New Version
              </Button>
            )}
          </div>
        )}

      {/* Freelancer status messages */}
      {isFreelancer && milestone.status === "SUBMITTED" && (
        <div className="mt-4 rounded-lg bg-primary-50 p-4">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary-500" />
            <p className="text-sm font-medium text-primary-700">
              Awaiting Review
            </p>
          </div>
          <p className="mt-1 text-sm text-primary-600">
            Your submission is being reviewed by the client.
          </p>
        </div>
      )}

      {isFreelancer && milestone.status === "APPROVED" && (
        <div className="mt-4 rounded-lg bg-success-50 p-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-success-500" />
            <p className="text-sm font-medium text-success-800">Approved</p>
          </div>
          <p className="mt-1 text-sm text-success-800/80">
            This milestone has been approved. Funds will be released shortly.
          </p>
        </div>
      )}

      {milestone.status === "PAID" && (
        <div className="mt-4 rounded-lg bg-success-50 p-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-success-500" />
            <p className="text-sm font-medium text-success-800">Paid</p>
          </div>
          <p className="mt-1 text-sm text-success-800/80">
            Funds have been released for this milestone.
          </p>
        </div>
      )}

      {/* Milestone Info */}
      <Card variant="bordered" className="mt-6">
        <h3 className="text-sm font-semibold text-neutral-700">Description</h3>
        <p className="mt-1 whitespace-pre-wrap text-sm text-neutral-600">
          {milestone.description}
        </p>
        {milestone.acceptance_criteria && (
          <>
            <h3 className="mt-4 text-sm font-semibold text-neutral-700">
              Acceptance Criteria
            </h3>
            <p className="mt-1 whitespace-pre-wrap text-sm text-neutral-600">
              {milestone.acceptance_criteria}
            </p>
          </>
        )}
      </Card>

      {/* AI Review Report section */}
      {milestone.latest_review && (
        <Card variant="bordered" className="mt-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-neutral-700">
              AI Code Review
            </h3>
            <StatusBadge
              status={
                milestone.latest_review.verdict === "PASS"
                  ? "APPROVED"
                  : milestone.latest_review.verdict === "FAIL"
                    ? "REJECTED"
                    : "PENDING"
              }
            />
          </div>
          <p className="mt-2 text-sm text-neutral-600">
            Score: {milestone.latest_review.score}/100 &middot; Verdict:{" "}
            {milestone.latest_review.verdict}
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="mt-2"
            onClick={() =>
              router.push(
                `/gigs/${params.id}/milestones/${params.milestoneId}/review`,
              )
            }
          >
            View Full Report <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </Card>
      )}

      {/* Submission history */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold text-neutral-800">
          Submissions ({milestone.submissions.length})
        </h3>
        {milestone.submissions.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No submissions yet"
            description={
              isFreelancer
                ? "Submit your work to begin the review process."
                : "The freelancer has not submitted work yet."
            }
            actionLabel={canSubmit ? "Submit Work" : undefined}
            onAction={
              canSubmit
                ? () =>
                    router.push(
                      `/gigs/${params.id}/milestones/${params.milestoneId}/submit`,
                    )
                : undefined
            }
            className="mt-4"
          />
        ) : (
          <div className="mt-3 space-y-3">
            {milestone.submissions.map((sub: Submission, idx: number) => (
              <Card key={sub.id} variant="flat">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-neutral-700">
                      Revision #{sub.revision_number || idx + 1}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {new Date(sub.created_at).toLocaleDateString()} at{" "}
                      {new Date(sub.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                  <StatusBadge status={sub.status} />
                </div>
                {sub.repo_url && (
                  <a
                    href={sub.repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700"
                  >
                    <ExternalLink className="h-4 w-4" />
                    View Pull Request
                  </a>
                )}
                {sub.file_keys.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-neutral-500">
                      {sub.file_keys.length} file
                      {sub.file_keys.length !== 1 ? "s" : ""} uploaded
                    </p>
                  </div>
                )}
                {sub.notes && (
                  <p className="mt-2 text-sm text-neutral-600">{sub.notes}</p>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Action bar */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        {canApprove && (
          <Button variant="web3" onClick={() => setApproveOpen(true)}>
            Approve &amp; Release Funds
          </Button>
        )}
        {canRevise && (
          <Button variant="outline" onClick={() => setRevisionOpen(true)}>
            Request Revision
          </Button>
        )}
        {canSubmit && milestone.status !== "REVISION_REQUESTED" && (
          <Button
            variant="primary"
            onClick={() =>
              router.push(
                `/gigs/${params.id}/milestones/${params.milestoneId}/submit`,
              )
            }
          >
            Submit Work
          </Button>
        )}
        {canDispute && (
          <Button
            variant="ghost"
            onClick={() =>
              router.push(
                `/gigs/${params.id}/milestones/${params.milestoneId}/dispute`,
              )
            }
          >
            <AlertTriangle className="mr-1.5 h-4 w-4" />
            Raise Dispute
          </Button>
        )}
      </div>

      {/* Approve modal */}
      <Modal
        open={approveOpen}
        onClose={() => setApproveOpen(false)}
        title="Approve & Release Funds"
        footer={
          <>
            <Button variant="ghost" onClick={() => setApproveOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="web3"
              loading={approving || isSending}
              onClick={handleApprove}
            >
              Release Funds
            </Button>
          </>
        }
      >
        <p className="text-sm text-neutral-600">
          This will release{" "}
          <strong>
            {milestone.amount} {milestone.currency}
          </strong>{" "}
          to the freelancer. This action is irreversible.
        </p>
        <p className="mt-2 text-sm text-neutral-500">
          Are you sure you want to approve this milestone and release the funds?
        </p>
      </Modal>

      {/* Revision modal */}
      <Modal
        open={revisionOpen}
        onClose={() => setRevisionOpen(false)}
        title="Request Revision"
        footer={
          <>
            <Button variant="ghost" onClick={() => setRevisionOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={revising}
              onClick={handleRevision}
            >
              Submit Feedback
            </Button>
          </>
        }
      >
        <Textarea
          label="What needs to be fixed?"
          placeholder="Describe the changes needed..."
          value={revisionFeedback}
          onChange={(e) => setRevisionFeedback(e.target.value)}
        />
      </Modal>
    </div>
  );
}

export default function MilestoneDetailPage() {
  return (
    <AuthGuard>
      <MilestoneContent />
    </AuthGuard>
  );
}
