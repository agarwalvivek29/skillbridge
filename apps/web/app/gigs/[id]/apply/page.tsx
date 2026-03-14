"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { Send, CheckCircle2, Clock } from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Textarea,
  Input,
  Spinner,
  StatusBadge,
} from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import {
  fetchGig,
  fetchMyProposal,
  submitProposal,
  type SubmitProposalPayload,
} from "@/lib/api/gigs";
import type { Gig } from "@/types/gig";
import type { Proposal } from "@/types/proposal";

function ApplyContent() {
  const params = useParams<{ id: string }>();
  const toast = useToast();

  const [gig, setGig] = useState<Gig | null>(null);
  const [existing, setExisting] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const [coverLetter, setCoverLetter] = useState("");
  const [proposedRate, setProposedRate] = useState("");
  const [timeline, setTimeline] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const [g, myProposal] = await Promise.all([
          fetchGig(params.id),
          fetchMyProposal(params.id).catch(() => null),
        ]);
        if (controller.signal.aborted) return;
        setGig(g);
        setExisting(myProposal);
        if (g) {
          const initialTimeline: Record<string, string> = {};
          g.milestones.forEach((m) => {
            initialTimeline[m.id] = "";
          });
          setTimeline(initialTimeline);
        }
      } catch {
        if (!controller.signal.aborted) toast.error("Failed to load gig");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    load();
    return () => controller.abort();
  }, [params.id, toast]);

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (coverLetter.length < 500) {
      e.coverLetter = `Cover letter must be at least 500 characters (${coverLetter.length}/500)`;
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit() {
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload: SubmitProposalPayload = {
        cover_letter: coverLetter,
        proposed_rate: proposedRate || undefined,
        timeline: Object.entries(timeline)
          .filter(([, date]) => date)
          .map(([milestoneId, date]) => ({
            milestone_id: milestoneId,
            estimated_delivery: date,
          })),
      };
      await submitProposal(params.id, payload);
      setSubmitted(true);
      toast.success("Proposal submitted!");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to submit proposal";
      toast.error(message);
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

  if (!gig) {
    return (
      <div className="py-20 text-center text-neutral-500">Gig not found.</div>
    );
  }

  // Already applied — show existing proposal
  if (existing) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
        <h1 className="text-2xl font-bold text-neutral-800">Your Proposal</h1>
        <p className="mt-1 text-sm text-neutral-500">for {gig.title}</p>

        <Card variant="bordered" className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <StatusBadge status={existing.status} />
            <span className="text-xs text-neutral-500">
              Submitted {new Date(existing.created_at).toLocaleDateString()}
            </span>
          </div>

          <h3 className="text-sm font-semibold text-neutral-700">
            Cover Letter
          </h3>
          <p className="mt-1 whitespace-pre-wrap text-sm text-neutral-600">
            {existing.cover_letter}
          </p>

          {existing.proposed_rate && (
            <div className="mt-3">
              <h3 className="text-sm font-semibold text-neutral-700">
                Proposed Rate
              </h3>
              <p className="mt-0.5 text-sm text-neutral-600">
                {existing.proposed_rate}
              </p>
            </div>
          )}

          {existing.timeline.length > 0 && (
            <div className="mt-3">
              <h3 className="text-sm font-semibold text-neutral-700">
                Timeline
              </h3>
              <div className="mt-1 space-y-1">
                {existing.timeline.map((t) => (
                  <div
                    key={t.milestone_id}
                    className="flex items-center gap-2 text-sm text-neutral-600"
                  >
                    <Clock className="h-3 w-3 text-neutral-400" />
                    {new Date(t.estimated_delivery).toLocaleDateString()}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    );
  }

  // Success state after submission
  if (submitted) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
        <Card variant="bordered">
          <div className="flex flex-col items-center gap-4 py-8">
            <div className="rounded-full bg-success-50 p-4">
              <CheckCircle2 className="h-10 w-10 text-success-500" />
            </div>
            <h2 className="text-xl font-bold text-neutral-800">
              Proposal Submitted!
            </h2>
            <p className="text-center text-sm text-neutral-500">
              You&apos;ll be notified when the client responds.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-neutral-800">Submit Proposal</h1>
      <p className="mt-1 text-sm text-neutral-500">for {gig.title}</p>

      <div className="mt-6 space-y-5">
        <div>
          <Textarea
            label="Cover Letter"
            placeholder="Explain why you're the best fit for this gig. Include relevant experience, your approach, and what makes you stand out..."
            value={coverLetter}
            error={errors.coverLetter}
            onChange={(e) => setCoverLetter(e.target.value)}
          />
          <p className="mt-1 text-xs text-neutral-400">
            {coverLetter.length}/500 minimum characters
          </p>
        </div>

        <Input
          label="Proposed Rate"
          placeholder="e.g. 2.5 SOL total (optional)"
          value={proposedRate}
          onChange={(e) => setProposedRate(e.target.value)}
          helperText="Override the listed budget with your own rate"
        />

        {gig.milestones.length > 0 && (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-700">
              Estimated Delivery per Milestone
            </label>
            <div className="space-y-2">
              {gig.milestones.map((m, i) => (
                <div
                  key={m.id}
                  className="flex items-center gap-3 rounded-md bg-neutral-50 p-3"
                >
                  <span className="flex-1 text-sm text-neutral-600">
                    {i + 1}. {m.title}
                  </span>
                  <input
                    type="date"
                    className="h-9 rounded-md border border-neutral-300 px-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    value={timeline[m.id] || ""}
                    onChange={(e) =>
                      setTimeline({ ...timeline, [m.id]: e.target.value })
                    }
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="border-t border-neutral-200 pt-4">
          <Button
            onClick={handleSubmit}
            loading={submitting}
            className="w-full"
          >
            <Send className="mr-1 h-4 w-4" />
            Submit Proposal
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function ApplyPage() {
  return (
    <AuthGuard>
      <ApplyContent />
    </AuthGuard>
  );
}
