"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  Clock,
  CheckCircle,
  Upload,
  FileText,
  ExternalLink,
  ShieldCheck,
  ShieldX,
  Users,
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
import { fetchDispute, submitEvidence } from "@/lib/api/disputes";
import { getUploadUrl } from "@/lib/api/submissions";
import type { Dispute, DisputeEvidence } from "@/types/dispute";

function DisputeDetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);

  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [loading, setLoading] = useState(true);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  // Evidence submission
  const [evidenceBody, setEvidenceBody] = useState("");
  const [evidenceFiles, setEvidenceFiles] = useState<File[]>([]);
  const [submittingEvidence, setSubmittingEvidence] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchDispute(params.id);
      if (!isMounted.current) return;
      setDispute(data);
    } catch {
      if (isMounted.current) toast.error("Failed to load dispute");
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [params.id, toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmitEvidence() {
    if (!evidenceBody.trim()) {
      toast.error("Please add a description for your evidence");
      return;
    }

    setSubmittingEvidence(true);
    try {
      const fileKeys: string[] = [];
      for (const file of evidenceFiles) {
        const { upload_url, file_key } = await getUploadUrl(file.name);
        await fetch(upload_url, {
          method: "PUT",
          body: file,
          headers: { "Content-Type": file.type },
        });
        fileKeys.push(file_key);
      }

      await submitEvidence(params.id, {
        body: evidenceBody.trim(),
        file_keys: fileKeys,
      });

      toast.success("Evidence submitted");
      setEvidenceBody("");
      setEvidenceFiles([]);
      load();
    } catch {
      toast.error("Failed to submit evidence");
    } finally {
      setSubmittingEvidence(false);
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

  const isParty =
    user?.id === dispute.client_id || user?.id === dispute.freelancer_id;
  const canSubmitEvidence = isParty && dispute.status === "OPEN";

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <Breadcrumb
        items={[
          { label: "Gigs", href: "/gigs" },
          { label: dispute.gig_title, href: `/gigs/${dispute.gig_id}/manage` },
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
            Filed {new Date(dispute.created_at).toLocaleDateString()} &middot;{" "}
            Milestone:{" "}
            <button
              onClick={() =>
                router.push(
                  `/gigs/${dispute.gig_id}/milestones/${dispute.milestone_id}`,
                )
              }
              className="font-medium text-primary-600 hover:text-primary-700"
            >
              {dispute.milestone_title}
            </button>
          </p>
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

      {/* AI Review Evidence */}
      {dispute.include_ai_review && dispute.ai_review_verdict && (
        <Card variant="bordered" className="mt-4">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-neutral-700">
              <ShieldCheck className="h-4 w-4 text-primary-500" />
              AI Review Evidence
            </h3>
            {dispute.ai_review_verdict === "PASS" ? (
              <Badge variant="success">PASS</Badge>
            ) : (
              <Badge variant="error">FAIL</Badge>
            )}
          </div>
          <p className="mt-2 text-sm text-neutral-600">
            Score: {dispute.ai_review_score}/100
          </p>
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

      {/* Evidence Thread */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold text-neutral-800">
          Evidence ({dispute.evidence.length})
        </h3>
        {dispute.evidence.length === 0 ? (
          <p className="mt-3 text-sm text-neutral-500">
            No evidence submitted yet.
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
                    <p className="text-xs text-neutral-500">
                      {ev.author_role.charAt(0).toUpperCase() +
                        ev.author_role.slice(1)}{" "}
                      &middot; {new Date(ev.created_at).toLocaleDateString()} at{" "}
                      {new Date(ev.created_at).toLocaleTimeString()}
                    </p>
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
                            {new URL(key).hostname}
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

      {/* Submit Evidence Form */}
      {canSubmitEvidence && (
        <Card variant="bordered" className="mt-6">
          <h3 className="text-sm font-semibold text-neutral-700">
            Submit Evidence
          </h3>
          <div className="mt-3 space-y-3">
            <Textarea
              placeholder="Describe your evidence..."
              value={evidenceBody}
              onChange={(e) => setEvidenceBody(e.target.value)}
            />
            <div>
              <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-primary-600 hover:text-primary-700">
                <Upload className="h-4 w-4" />
                Attach files
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) =>
                    setEvidenceFiles(Array.from(e.target.files ?? []))
                  }
                />
              </label>
              {evidenceFiles.length > 0 && (
                <p className="mt-1 text-xs text-neutral-500">
                  {evidenceFiles.length} file
                  {evidenceFiles.length !== 1 ? "s" : ""} selected
                </p>
              )}
            </div>
            <Button
              variant="primary"
              size="sm"
              loading={submittingEvidence}
              onClick={handleSubmitEvidence}
            >
              Submit Evidence
            </Button>
          </div>
        </Card>
      )}

      {/* Timeline */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold text-neutral-800">Timeline</h3>
        <div className="mt-3 relative border-l-2 border-neutral-200 pl-6">
          {dispute.timeline.map((event, i) => (
            <div key={event.id} className="relative mb-4 last:mb-0">
              <div className="absolute -left-[31px] flex h-5 w-5 items-center justify-center rounded-full bg-white border-2 border-neutral-200">
                {event.status === "RESOLVED" ? (
                  <CheckCircle className="h-3 w-3 text-success-500" />
                ) : event.status === "ARBITRATION" ? (
                  <Users className="h-3 w-3 text-web3-500" />
                ) : (
                  <Clock className="h-3 w-3 text-neutral-400" />
                )}
              </div>
              <div>
                <StatusBadge status={event.status} />
                <p className="mt-1 text-sm text-neutral-600">{event.note}</p>
                <p className="mt-0.5 text-xs text-neutral-400">
                  {new Date(event.created_at).toLocaleDateString()} at{" "}
                  {new Date(event.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

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
          <div className="mt-3 flex gap-4 text-sm">
            {dispute.resolution.amount_released !== "0" && (
              <span className="text-success-600">
                Released: {dispute.resolution.amount_released}
              </span>
            )}
            {dispute.resolution.amount_refunded !== "0" && (
              <span className="text-primary-600">
                Refunded: {dispute.resolution.amount_refunded}
              </span>
            )}
          </div>
        </Card>
      )}

      {/* Arbitrators */}
      {dispute.arbitrators.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-neutral-700">
            Arbitrators Assigned
          </h3>
          <div className="mt-2 flex -space-x-2">
            {dispute.arbitrators.map((arb) => (
              <Avatar
                key={arb.id}
                name={dispute.status === "RESOLVED" ? arb.name : undefined}
                walletAddress={
                  dispute.status !== "RESOLVED" ? arb.id : undefined
                }
                src={dispute.status === "RESOLVED" ? arb.avatar_url : undefined}
                size="sm"
              />
            ))}
          </div>
          {dispute.status !== "RESOLVED" && (
            <p className="mt-1 text-xs text-neutral-400">
              Identities hidden until resolution
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function DisputeDetailPage() {
  return (
    <AuthGuard>
      <DisputeDetailContent />
    </AuthGuard>
  );
}
