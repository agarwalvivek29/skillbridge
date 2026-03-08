"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  Upload,
  Link2,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Spinner,
  Select,
  Textarea,
  Input,
  Breadcrumb,
} from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { useAuthStore } from "@/lib/stores/auth";
import { fetchMilestone } from "@/lib/api/submissions";
import { getUploadUrl } from "@/lib/api/submissions";
import { createDispute } from "@/lib/api/disputes";
import type { MilestoneDetail } from "@/types/submission";
import type { DisputeReason } from "@/types/dispute";

const REASON_OPTIONS = [
  {
    value: "WORK_DOESNT_MEET_REQUIREMENTS",
    label: "Work doesn't meet requirements",
  },
  { value: "CLIENT_UNRESPONSIVE", label: "Client unresponsive" },
  { value: "SCOPE_CREEP", label: "Scope creep" },
  { value: "PAYMENT_WITHHELD", label: "Payment withheld" },
  { value: "OTHER", label: "Other" },
];

type Step = "form" | "confirm" | "submitted";

function DisputeFormContent() {
  const params = useParams<{ id: string; milestoneId: string }>();
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);

  const [milestone, setMilestone] = useState<MilestoneDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<Step>("form");
  const [submitting, setSubmitting] = useState(false);
  const [disputeId, setDisputeId] = useState<string | null>(null);

  // Form fields
  const [reason, setReason] = useState<DisputeReason | "">("");
  const [description, setDescription] = useState("");
  const [evidenceFiles, setEvidenceFiles] = useState<File[]>([]);
  const [evidenceLinks, setEvidenceLinks] = useState<string[]>([""]);
  const [includeAiReview, setIncludeAiReview] = useState(true);
  const [uploadedKeys, setUploadedKeys] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);

  const loadMilestone = useCallback(async () => {
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
    loadMilestone();
  }, [loadMilestone]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    setEvidenceFiles((prev) => [...prev, ...files]);
  }

  function removeFile(index: number) {
    setEvidenceFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function addLinkField() {
    setEvidenceLinks((prev) => [...prev, ""]);
  }

  function updateLink(index: number, value: string) {
    setEvidenceLinks((prev) => prev.map((l, i) => (i === index ? value : l)));
  }

  function removeLinkField(index: number) {
    setEvidenceLinks((prev) => prev.filter((_, i) => i !== index));
  }

  function validateForm(): string | null {
    if (!reason) return "Please select a reason for the dispute.";
    if (description.length < 200) {
      return `Description must be at least 200 characters (currently ${description.length}).`;
    }
    return null;
  }

  function handleNext() {
    const error = validateForm();
    if (error) {
      toast.error(error);
      return;
    }
    setStep("confirm");
  }

  async function handleSubmit() {
    setSubmitting(true);
    try {
      // Upload files first
      let fileKeys = [...uploadedKeys];
      if (evidenceFiles.length > 0) {
        setUploading(true);
        for (const file of evidenceFiles) {
          const { upload_url, file_key } = await getUploadUrl(file.name);
          await fetch(upload_url, {
            method: "PUT",
            body: file,
            headers: { "Content-Type": file.type },
          });
          fileKeys.push(file_key);
        }
        setUploadedKeys(fileKeys);
        setUploading(false);
      }

      // Add evidence links as file_keys (the API can handle URL strings)
      const allLinks = evidenceLinks.filter((l) => l.trim());
      const allKeys = [...fileKeys, ...allLinks];

      const dispute = await createDispute({
        milestone_id: params.milestoneId,
        reason: reason as DisputeReason,
        description,
        evidence_file_keys: allKeys,
        include_ai_review: includeAiReview && !!milestone?.latest_review,
      });

      setDisputeId(dispute.id);
      setStep("submitted");
    } catch {
      toast.error("Failed to file dispute");
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

  if (!milestone) {
    return (
      <div className="py-20 text-center text-neutral-500">
        Milestone not found.
      </div>
    );
  }

  const hasAiReview = !!milestone.latest_review;

  // Step: Submitted
  if (step === "submitted" && disputeId) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 md:px-6">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success-50">
            <CheckCircle className="h-8 w-8 text-success-500" />
          </div>
          <h1 className="text-2xl font-bold text-neutral-800">Dispute Filed</h1>
          <p className="mt-2 text-neutral-500">
            Dispute ID:{" "}
            <span className="font-mono font-semibold">
              #{disputeId.slice(0, 8)}
            </span>
          </p>
          <p className="mt-4 text-sm text-neutral-600">
            Both parties have been notified. Arbitrators will review your
            dispute within 48 hours.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Button
              variant="primary"
              onClick={() => router.push(`/disputes/${disputeId}`)}
            >
              View Dispute Details
              <ArrowRight className="ml-1.5 h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              onClick={() =>
                router.push(
                  `/gigs/${params.id}/milestones/${params.milestoneId}`,
                )
              }
            >
              Back to Milestone
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Step: Confirmation
  if (step === "confirm") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
        <Breadcrumb
          items={[
            { label: "Gigs", href: "/gigs" },
            { label: milestone.gig_title, href: `/gigs/${params.id}/manage` },
            {
              label: milestone.title,
              href: `/gigs/${params.id}/milestones/${params.milestoneId}`,
            },
            { label: "Raise Dispute" },
          ]}
        />

        <h1 className="mt-4 text-2xl font-bold text-neutral-800">
          Confirm Dispute
        </h1>

        <Card variant="bordered" className="mt-6">
          <h3 className="text-sm font-semibold text-neutral-700">Reason</h3>
          <p className="mt-1 text-sm text-neutral-600">
            {REASON_OPTIONS.find((o) => o.value === reason)?.label}
          </p>

          <h3 className="mt-4 text-sm font-semibold text-neutral-700">
            Description
          </h3>
          <p className="mt-1 whitespace-pre-wrap text-sm text-neutral-600">
            {description}
          </p>

          {evidenceFiles.length > 0 && (
            <>
              <h3 className="mt-4 text-sm font-semibold text-neutral-700">
                Files ({evidenceFiles.length})
              </h3>
              <ul className="mt-1 space-y-1">
                {evidenceFiles.map((f, i) => (
                  <li key={i} className="text-sm text-neutral-600">
                    {f.name}
                  </li>
                ))}
              </ul>
            </>
          )}

          {evidenceLinks.filter((l) => l.trim()).length > 0 && (
            <>
              <h3 className="mt-4 text-sm font-semibold text-neutral-700">
                Evidence Links
              </h3>
              <ul className="mt-1 space-y-1">
                {evidenceLinks
                  .filter((l) => l.trim())
                  .map((l, i) => (
                    <li key={i} className="text-sm text-primary-600 break-all">
                      {l}
                    </li>
                  ))}
              </ul>
            </>
          )}

          {hasAiReview && includeAiReview && (
            <div className="mt-4 flex items-center gap-2 text-sm text-neutral-600">
              <ShieldCheck className="h-4 w-4 text-primary-500" />
              AI review report will be included as evidence
            </div>
          )}
        </Card>

        {/* Warning */}
        <div className="mt-4 rounded-lg border border-warning-200 bg-warning-50 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning-500" />
            <p className="text-sm text-[#92400E]">
              Raising a dispute will freeze the milestone and notify both
              parties. Arbitrators will review within 48 hours.
            </p>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-3">
          <Button variant="ghost" onClick={() => setStep("form")}>
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Back
          </Button>
          <Button
            variant="destructive"
            loading={submitting || uploading}
            onClick={handleSubmit}
          >
            {uploading ? "Uploading files..." : "File Dispute"}
          </Button>
        </div>
      </div>
    );
  }

  // Step: Form
  return (
    <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
      <Breadcrumb
        items={[
          { label: "Gigs", href: "/gigs" },
          { label: milestone.gig_title, href: `/gigs/${params.id}/manage` },
          {
            label: milestone.title,
            href: `/gigs/${params.id}/milestones/${params.milestoneId}`,
          },
          { label: "Raise Dispute" },
        ]}
      />

      <div className="mt-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-error-50">
          <AlertTriangle className="h-5 w-5 text-error-500" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-800">
            Raise a Dispute
          </h1>
          <p className="text-sm text-neutral-500">
            {milestone.title} &middot; {milestone.amount} {milestone.currency}
          </p>
        </div>
      </div>

      <div className="mt-8 space-y-6">
        {/* Reason */}
        <Select
          label="Reason for dispute"
          placeholder="Select a reason..."
          options={REASON_OPTIONS}
          value={reason}
          onChange={(e) => setReason(e.target.value as DisputeReason)}
        />

        {/* Description */}
        <Textarea
          label="Detailed description"
          placeholder="Describe the issue in detail. Include specific examples, dates, and any relevant context. Minimum 200 characters."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          helperText={`${description.length}/200 minimum characters`}
          error={
            description.length > 0 && description.length < 200
              ? `${200 - description.length} more characters needed`
              : undefined
          }
          className="min-h-[180px]"
        />

        {/* Evidence files */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-neutral-700">
            Evidence files
          </label>
          <div className="rounded-lg border border-dashed border-neutral-300 p-4">
            <div className="flex flex-col items-center gap-2">
              <Upload className="h-6 w-6 text-neutral-400" />
              <label className="cursor-pointer text-sm font-medium text-primary-600 hover:text-primary-700">
                Choose files
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileChange}
                />
              </label>
              <p className="text-xs text-neutral-400">
                Screenshots, documents, or other evidence
              </p>
            </div>
            {evidenceFiles.length > 0 && (
              <div className="mt-3 space-y-2">
                {evidenceFiles.map((file, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-md bg-neutral-50 px-3 py-2"
                  >
                    <span className="truncate text-sm text-neutral-600">
                      {file.name}
                    </span>
                    <button
                      onClick={() => removeFile(i)}
                      className="ml-2 text-xs text-error-500 hover:text-error-600"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Evidence links */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-neutral-700">
            Evidence links
          </label>
          <div className="space-y-2">
            {evidenceLinks.map((link, i) => (
              <div key={i} className="flex items-center gap-2">
                <Link2 className="h-4 w-4 shrink-0 text-neutral-400" />
                <Input
                  placeholder="https://github.com/..."
                  value={link}
                  onChange={(e) => updateLink(i, e.target.value)}
                  className="flex-1"
                />
                {evidenceLinks.length > 1 && (
                  <button
                    onClick={() => removeLinkField(i)}
                    className="text-xs text-error-500 hover:text-error-600"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
          <button
            onClick={addLinkField}
            className="mt-2 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            + Add another link
          </button>
        </div>

        {/* AI Review checkbox */}
        {hasAiReview && (
          <label className="flex items-start gap-3 rounded-lg border border-neutral-200 bg-neutral-50 p-4 cursor-pointer">
            <input
              type="checkbox"
              checked={includeAiReview}
              onChange={(e) => setIncludeAiReview(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <p className="text-sm font-medium text-neutral-700">
                Include AI review report as evidence
              </p>
              <p className="mt-0.5 text-xs text-neutral-500">
                The AI review scored this submission{" "}
                {milestone.latest_review?.score}/100 with verdict:{" "}
                {milestone.latest_review?.verdict}
              </p>
            </div>
          </label>
        )}

        {/* Continue button */}
        <div className="flex items-center gap-3 pt-2">
          <Button
            variant="ghost"
            onClick={() =>
              router.push(`/gigs/${params.id}/milestones/${params.milestoneId}`)
            }
          >
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleNext}>
            Continue to Review
            <ArrowRight className="ml-1.5 h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function RaiseDisputePage() {
  return (
    <AuthGuard>
      <DisputeFormContent />
    </AuthGuard>
  );
}
