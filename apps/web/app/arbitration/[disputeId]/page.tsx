"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Scale,
  ShieldCheck,
  ShieldX,
  CheckCircle,
  Clock,
  Users,
  FileText,
  ExternalLink,
  ArrowRight,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Spinner,
  StatusBadge,
  Textarea,
  Avatar,
  Breadcrumb,
  Badge,
} from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { useAuthStore } from "@/lib/stores/auth";
import {
  fetchArbitrationDetail,
  fetchVotes,
  castVote,
} from "@/lib/api/disputes";
import type {
  Dispute,
  DisputeEvidence,
  ArbitrationVote,
  DisputeVerdict,
} from "@/types/dispute";

function ArbitrationReviewContent() {
  const params = useParams<{ disputeId: string }>();
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);

  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [votes, setVotes] = useState<ArbitrationVote[]>([]);
  const [loading, setLoading] = useState(true);

  // Vote form
  const [verdict, setVerdict] = useState<DisputeVerdict | null>(null);
  const [reasoning, setReasoning] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, v] = await Promise.all([
        fetchArbitrationDetail(params.disputeId),
        fetchVotes(params.disputeId),
      ]);
      setDispute(d);
      setVotes(v);
      if (user && v.some((vote) => vote.arbitrator_id === user.id)) {
        setHasVoted(true);
      }
    } catch {
      toast.error("Failed to load dispute");
    } finally {
      setLoading(false);
    }
  }, [params.disputeId, user, toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleVote() {
    if (!verdict) {
      toast.error("Please select a verdict");
      return;
    }
    if (!reasoning.trim()) {
      toast.error("Please provide your reasoning");
      return;
    }

    setSubmitting(true);
    try {
      await castVote(params.disputeId, {
        verdict,
        reasoning: reasoning.trim(),
      });
      toast.success("Vote submitted");
      setHasVoted(true);
      load();
    } catch {
      toast.error("Failed to submit vote");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!dispute) {
    return (
      <div className="py-20 text-center text-neutral-500">
        Dispute not found.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <Breadcrumb
        items={[
          { label: "Arbitration", href: "/arbitration" },
          { label: `Dispute #${dispute.id.slice(0, 8)}` },
        ]}
      />

      {/* Header */}
      <div className="mt-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-neutral-800">
              Dispute #{dispute.id.slice(0, 8)}
            </h1>
            <StatusBadge status={dispute.status} />
          </div>
          <p className="mt-1 text-sm text-neutral-500">
            {dispute.gig_title} &middot; {dispute.milestone_title}
          </p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-web3-50">
          <Scale className="h-5 w-5 text-web3-500" />
        </div>
      </div>

      {/* Parties */}
      <Card variant="bordered" className="mt-6">
        <h3 className="text-sm font-semibold text-neutral-700">Parties</h3>
        <div className="mt-3 flex items-center gap-6">
          <div className="flex items-center gap-3">
            <Avatar
              name={dispute.client_name}
              src={dispute.client_avatar_url}
              size="md"
            />
            <div>
              <p className="text-sm font-semibold text-neutral-800">
                {dispute.client_name}
              </p>
              <p className="text-xs text-neutral-500">Client</p>
            </div>
          </div>
          <span className="text-lg font-bold text-neutral-300">vs</span>
          <div className="flex items-center gap-3">
            <Avatar
              name={dispute.freelancer_name}
              src={dispute.freelancer_avatar_url}
              size="md"
            />
            <div>
              <p className="text-sm font-semibold text-neutral-800">
                {dispute.freelancer_name}
              </p>
              <p className="text-xs text-neutral-500">Freelancer</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Dispute description */}
      <Card variant="bordered" className="mt-4">
        <h3 className="text-sm font-semibold text-neutral-700">
          Dispute Reason
        </h3>
        <Badge variant="warning" className="mt-2">
          {dispute.reason.replace(/_/g, " ")}
        </Badge>
        <p className="mt-3 whitespace-pre-wrap text-sm text-neutral-600">
          {dispute.description}
        </p>
      </Card>

      {/* AI Review Evidence */}
      {dispute.include_ai_review && dispute.ai_review_verdict && (
        <Card
          variant="bordered"
          className="mt-4 border-primary-200 bg-primary-50/50"
        >
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-neutral-700">
              {dispute.ai_review_verdict === "PASS" ? (
                <ShieldCheck className="h-4 w-4 text-success-500" />
              ) : (
                <ShieldX className="h-4 w-4 text-error-500" />
              )}
              AI Review Report
            </h3>
            {dispute.ai_review_verdict === "PASS" ? (
              <Badge variant="success">
                PASS — {dispute.ai_review_score}/100
              </Badge>
            ) : (
              <Badge variant="error">
                FAIL — {dispute.ai_review_score}/100
              </Badge>
            )}
          </div>
          {dispute.ai_review_summary && (
            <p className="mt-2 whitespace-pre-wrap text-sm text-neutral-600">
              {dispute.ai_review_summary}
            </p>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="mt-2"
            onClick={() =>
              router.push(
                `/gigs/${dispute.gig_id}/milestones/${dispute.milestone_id}/review`,
              )
            }
          >
            View Full Report
            <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </Card>
      )}

      {/* All Evidence */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold text-neutral-800">
          Evidence from Both Parties ({dispute.evidence.length})
        </h3>
        {dispute.evidence.length === 0 ? (
          <p className="mt-3 text-sm text-neutral-500">
            No evidence submitted.
          </p>
        ) : (
          <div className="mt-3 space-y-3">
            {dispute.evidence.map((ev: DisputeEvidence) => (
              <Card key={ev.id} variant="flat">
                <div className="flex items-center gap-3">
                  <Avatar name={ev.author_name} size="sm" />
                  <div>
                    <p className="text-sm font-semibold text-neutral-700">
                      {ev.author_name}
                    </p>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          ev.author_role === "client" ? "primary" : "success"
                        }
                      >
                        {ev.author_role}
                      </Badge>
                      <span className="text-xs text-neutral-500">
                        {new Date(ev.created_at).toLocaleDateString()} at{" "}
                        {new Date(ev.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm text-neutral-600">
                  {ev.body}
                </p>
                {ev.file_keys.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {ev.file_keys.map((key, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 rounded-md bg-neutral-100 px-2 py-1 text-xs text-neutral-600"
                      >
                        <FileText className="h-3 w-3" />
                        {key.includes("://") ? (
                          <a
                            href={key}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:text-primary-700"
                          >
                            Link
                            <ExternalLink className="ml-0.5 inline h-3 w-3" />
                          </a>
                        ) : (
                          key.split("/").pop()
                        )}
                      </span>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Voting Section */}
      {!hasVoted && dispute.status !== "RESOLVED" && (
        <Card variant="bordered" className="mt-6 border-web3-200">
          <h3 className="flex items-center gap-2 text-base font-semibold text-neutral-800">
            <Scale className="h-5 w-5 text-web3-500" />
            Cast Your Vote
          </h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <button
              onClick={() => setVerdict("client")}
              className={`rounded-lg border-2 p-4 text-center transition-colors ${
                verdict === "client"
                  ? "border-primary-500 bg-primary-50"
                  : "border-neutral-200 hover:border-neutral-300"
              }`}
            >
              <p className="text-sm font-semibold text-neutral-800">
                Rule for Client
              </p>
              <p className="mt-1 text-xs text-neutral-500">
                {dispute.client_name}
              </p>
            </button>
            <button
              onClick={() => setVerdict("freelancer")}
              className={`rounded-lg border-2 p-4 text-center transition-colors ${
                verdict === "freelancer"
                  ? "border-success-500 bg-success-50"
                  : "border-neutral-200 hover:border-neutral-300"
              }`}
            >
              <p className="text-sm font-semibold text-neutral-800">
                Rule for Freelancer
              </p>
              <p className="mt-1 text-xs text-neutral-500">
                {dispute.freelancer_name}
              </p>
            </button>
          </div>
          <div className="mt-4">
            <Textarea
              label="Reasoning (required)"
              placeholder="Explain your decision based on the evidence..."
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
            />
          </div>
          <div className="mt-4">
            <Button
              variant="web3"
              loading={submitting}
              onClick={handleVote}
              disabled={!verdict || !reasoning.trim()}
            >
              Submit Vote
            </Button>
          </div>
        </Card>
      )}

      {/* Voted confirmation */}
      {hasVoted && dispute.status !== "RESOLVED" && (
        <div className="mt-6 rounded-lg bg-success-50 p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-success-500" />
            <p className="text-sm font-medium text-success-800">
              Your vote has been submitted
            </p>
          </div>
          <p className="mt-1 text-sm text-success-800/80">
            Waiting for other arbitrators to vote.
          </p>
        </div>
      )}

      {/* Deliberation — other votes (anonymized) */}
      {votes.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-neutral-800">
            Arbitrator Votes ({votes.length})
          </h3>
          <div className="mt-3 space-y-3">
            {votes.map((vote, i) => (
              <Card key={i} variant="flat">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Avatar
                      name={
                        dispute.status === "RESOLVED"
                          ? vote.arbitrator_name
                          : undefined
                      }
                      walletAddress={
                        dispute.status !== "RESOLVED"
                          ? `0x${String(i + 1).padStart(4, "0")}`
                          : undefined
                      }
                      size="sm"
                    />
                    <p className="text-sm font-semibold text-neutral-700">
                      {dispute.status === "RESOLVED"
                        ? vote.arbitrator_name
                        : `Arbitrator ${i + 1}`}
                    </p>
                  </div>
                  <Badge
                    variant={vote.verdict === "client" ? "primary" : "success"}
                  >
                    {vote.verdict === "client" ? "Client" : "Freelancer"}
                  </Badge>
                </div>
                {dispute.status === "RESOLVED" && (
                  <p className="mt-2 text-sm text-neutral-600">
                    {vote.reasoning}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Resolution */}
      {dispute.status === "RESOLVED" && dispute.resolution && (
        <Card
          variant="bordered"
          className="mt-6 border-success-200 bg-success-50"
        >
          <h3 className="flex items-center gap-2 text-base font-semibold text-success-800">
            <CheckCircle className="h-5 w-5" />
            Resolution
          </h3>
          <p className="mt-2 text-sm text-success-800/80">
            Ruled in favor of:{" "}
            <span className="font-semibold">
              {dispute.resolution.winner === "client"
                ? dispute.client_name
                : dispute.freelancer_name}
            </span>
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm text-neutral-600">
            {dispute.resolution.reasoning}
          </p>
        </Card>
      )}
    </div>
  );
}

export default function ArbitrationReviewPage() {
  return (
    <AuthGuard>
      <ArbitrationReviewContent />
    </AuthGuard>
  );
}
