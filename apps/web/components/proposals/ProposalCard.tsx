"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Star,
  Shield,
} from "lucide-react";
import { Avatar, Button, Card, StatusBadge, Modal } from "@/components/ui";
import { Input } from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { acceptProposal, rejectProposal } from "@/lib/api/gigs";
import type { Proposal } from "@/types/proposal";

interface ProposalCardProps {
  proposal: Proposal;
  onUpdate: (proposal: Proposal) => void;
}

export function ProposalCard({ proposal, onUpdate }: ProposalCardProps) {
  const toast = useToast();
  const [expanded, setExpanded] = useState(false);
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectMessage, setRejectMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleAccept() {
    setLoading(true);
    try {
      const updated = await acceptProposal(proposal.id);
      onUpdate(updated);
      toast.success("Proposal accepted! Work can now begin.");
      setAcceptOpen(false);
    } catch {
      toast.error("Failed to accept proposal");
    } finally {
      setLoading(false);
    }
  }

  async function handleReject() {
    setLoading(true);
    try {
      const updated = await rejectProposal(
        proposal.id,
        rejectMessage || undefined,
      );
      onUpdate(updated);
      toast.info("Proposal rejected");
      setRejectOpen(false);
    } catch {
      toast.error("Failed to reject proposal");
    } finally {
      setLoading(false);
    }
  }

  const isPending = proposal.status === "PENDING";

  return (
    <>
      <Card variant="bordered">
        <div className="flex items-start gap-4">
          <Avatar
            name={proposal.freelancer_name ?? undefined}
            walletAddress={proposal.freelancer_wallet_address ?? undefined}
            size="md"
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-sm font-semibold text-neutral-800">
                {proposal.freelancer_name || "Anonymous"}
              </h3>
              <StatusBadge status={proposal.status} />
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-neutral-500">
              {proposal.freelancer_rating != null && (
                <span className="flex items-center gap-0.5">
                  <Star className="h-3 w-3 fill-secondary-400 text-secondary-400" />
                  {proposal.freelancer_rating.toFixed(1)}
                </span>
              )}
              {proposal.freelancer_reputation_score != null && (
                <span className="flex items-center gap-0.5">
                  <Shield className="h-3 w-3 text-web3-500" />
                  Rep: {proposal.freelancer_reputation_score}
                </span>
              )}
              {proposal.proposed_rate && (
                <span className="font-medium text-neutral-700">
                  Rate: {proposal.proposed_rate}
                </span>
              )}
            </div>

            {/* Cover letter preview/expand */}
            <div className="mt-2">
              <p
                className={
                  expanded
                    ? "whitespace-pre-wrap text-sm text-neutral-600"
                    : "line-clamp-2 text-sm text-neutral-600"
                }
              >
                {proposal.cover_letter}
              </p>
              {proposal.cover_letter.length > 200 && (
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="mt-1 flex items-center gap-0.5 text-xs font-medium text-primary-600 hover:text-primary-700"
                >
                  {expanded ? (
                    <>
                      Show less <ChevronUp className="h-3 w-3" />
                    </>
                  ) : (
                    <>
                      Read more <ChevronDown className="h-3 w-3" />
                    </>
                  )}
                </button>
              )}
            </div>

            {/* Timeline */}
            {proposal.timeline.length > 0 && (
              <div className="mt-2 text-xs text-neutral-500">
                Timeline: {proposal.timeline.length} milestone
                {proposal.timeline.length !== 1 ? "s" : ""} estimated
              </div>
            )}

            {/* Actions */}
            <div className="mt-3 flex items-center gap-2">
              {isPending && (
                <>
                  <Button size="sm" onClick={() => setAcceptOpen(true)}>
                    Accept
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setRejectOpen(true)}
                  >
                    Reject
                  </Button>
                </>
              )}
              <Link
                href={`/freelancers/${proposal.freelancer_id}`}
                className="ml-auto flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
              >
                View Portfolio <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>
      </Card>

      {/* Accept confirmation modal */}
      <Modal
        open={acceptOpen}
        onClose={() => setAcceptOpen(false)}
        title="Accept Proposal"
        footer={
          <>
            <Button variant="ghost" onClick={() => setAcceptOpen(false)}>
              Cancel
            </Button>
            <Button loading={loading} onClick={handleAccept}>
              Hire {proposal.freelancer_name || "this freelancer"}
            </Button>
          </>
        }
      >
        <p className="text-sm text-neutral-600">
          Hire <strong>{proposal.freelancer_name || "this freelancer"}</strong>{" "}
          for this gig? Other pending proposals will be automatically rejected.
        </p>
      </Modal>

      {/* Reject modal */}
      <Modal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title="Reject Proposal"
        footer={
          <>
            <Button variant="ghost" onClick={() => setRejectOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={loading}
              onClick={handleReject}
            >
              Reject
            </Button>
          </>
        }
      >
        <p className="mb-3 text-sm text-neutral-600">
          Optionally provide feedback to the freelancer:
        </p>
        <Input
          placeholder="Reason for rejection (optional)"
          value={rejectMessage}
          onChange={(e) => setRejectMessage(e.target.value)}
        />
      </Modal>
    </>
  );
}
