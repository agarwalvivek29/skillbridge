"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ShieldCheck,
  ShieldX,
  Loader2,
  RefreshCw,
  FileText,
  Clock,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Spinner,
  Badge,
  Breadcrumb,
  EmptyState,
} from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { useAuthStore } from "@/lib/stores/auth";
import { fetchMilestone, fetchReviewReport } from "@/lib/api/submissions";
import type { ReviewReport, MilestoneDetail } from "@/types/submission";

function ScoreGauge({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? "#22C55E" : score >= 40 ? "#F59E0B" : "#EF4444";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle
          cx="60"
          cy="60"
          r="45"
          fill="none"
          stroke="#E5E7EB"
          strokeWidth="8"
        />
        <circle
          cx="60"
          cy="60"
          r="45"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform="rotate(-90 60 60)"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <span className="absolute text-2xl font-bold text-neutral-800">
        {score}
      </span>
    </div>
  );
}

function ReviewContent() {
  const params = useParams<{ id: string; milestoneId: string }>();
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);

  const [milestone, setMilestone] = useState<MilestoneDetail | null>(null);
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(true);
  const [reportState, setReportState] = useState<
    "loading" | "pending" | "found" | "empty"
  >("loading");
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const loadMilestone = useCallback(async () => {
    try {
      const data = await fetchMilestone(params.milestoneId);
      if (!isMounted.current) return null;
      setMilestone(data);
      return data;
    } catch {
      if (isMounted.current) toast.error("Failed to load milestone");
      return null;
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [params.milestoneId, toast]);

  const loadReport = useCallback(async (ms: MilestoneDetail) => {
    if (!isMounted.current) return;
    setReportLoading(true);
    const latestSubmission =
      ms.submissions.length > 0
        ? ms.submissions[ms.submissions.length - 1]
        : null;

    if (!latestSubmission) {
      if (isMounted.current) {
        setReportState("empty");
        setReportLoading(false);
      }
      return;
    }

    // No review for file-only submissions
    if (!latestSubmission.repo_url) {
      if (isMounted.current) {
        setReportState("empty");
        setReportLoading(false);
      }
      return;
    }

    try {
      const r = await fetchReviewReport(latestSubmission.id);
      if (!isMounted.current) return;
      if (r.verdict === "PENDING") {
        setReportState("pending");
      } else {
        setReport(r);
        setReportState("found");
      }
    } catch {
      if (isMounted.current) setReportState("empty");
    } finally {
      if (isMounted.current) setReportLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMilestone().then((ms) => {
      if (ms) loadReport(ms);
    });
  }, [loadMilestone, loadReport]);

  async function handleRefresh() {
    if (milestone) {
      await loadReport(milestone);
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

  // Render markdown body simply by splitting paragraphs and headings
  function renderMarkdown(body: string) {
    const lines = body.split("\n");
    const elements: React.ReactNode[] = [];

    lines.forEach((line, i) => {
      if (line.startsWith("### ")) {
        elements.push(
          <h4 key={i} className="mt-4 text-sm font-semibold text-neutral-800">
            {line.slice(4)}
          </h4>,
        );
      } else if (line.startsWith("## ")) {
        elements.push(
          <h3 key={i} className="mt-5 text-base font-semibold text-neutral-800">
            {line.slice(3)}
          </h3>,
        );
      } else if (line.startsWith("# ")) {
        elements.push(
          <h2 key={i} className="mt-6 text-lg font-bold text-neutral-800">
            {line.slice(2)}
          </h2>,
        );
      } else if (line.startsWith("- ") || line.startsWith("* ")) {
        elements.push(
          <li key={i} className="ml-4 text-sm text-neutral-600">
            {line.slice(2)}
          </li>,
        );
      } else if (line.startsWith("```")) {
        // Skip code fence markers; content between them rendered as-is
      } else if (line.trim() === "") {
        elements.push(<div key={i} className="h-2" />);
      } else {
        elements.push(
          <p key={i} className="text-sm text-neutral-600">
            {line}
          </p>,
        );
      }
    });

    return elements;
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <Breadcrumb
        items={[
          { label: "Gigs", href: "/gigs" },
          { label: milestone.gig_title, href: `/gigs/${params.id}/manage` },
          {
            label: milestone.title,
            href: `/gigs/${params.id}/milestones/${params.milestoneId}`,
          },
          { label: "AI Review" },
        ]}
      />

      <div className="mt-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-neutral-800">
          AI Code Review Report
        </h1>
        {report && (
          <div className="flex items-center gap-2">
            <Badge variant="info">{report.model_version}</Badge>
            <span className="text-sm text-neutral-500">
              {new Date(report.created_at).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>

      {/* Loading state */}
      {reportLoading && (
        <div className="mt-12 flex min-h-[40vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      )}

      {/* Pending state */}
      {!reportLoading && reportState === "pending" && (
        <div className="mt-12">
          <Card variant="bordered" className="text-center">
            <div className="py-8">
              <Loader2 className="mx-auto h-10 w-10 animate-spin text-neutral-400" />
              <h3 className="mt-4 text-lg font-semibold text-neutral-700">
                AI review in progress
              </h3>
              <p className="mt-1 text-sm text-neutral-500">
                The AI is analyzing the pull request. Check back soon.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={handleRefresh}
              >
                <RefreshCw className="mr-1.5 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Empty state — no review for file submission */}
      {!reportLoading && reportState === "empty" && (
        <div className="mt-12">
          <EmptyState
            icon={FileText}
            title="No AI review for this submission"
            description="AI code reviews are only available for pull request submissions."
            actionLabel="Back to Milestone"
            onAction={() =>
              router.push(`/gigs/${params.id}/milestones/${params.milestoneId}`)
            }
          />
        </div>
      )}

      {/* Report found */}
      {!reportLoading && reportState === "found" && report && (
        <div className="mt-6 space-y-6">
          {/* Verdict banner */}
          {report.verdict === "PASS" ? (
            <div className="flex items-center gap-4 rounded-lg bg-success-50 p-4">
              <ShieldCheck className="h-8 w-8 text-success-600" />
              <div>
                <p className="text-lg font-semibold text-success-600">
                  Code Review Passed
                </p>
                <p className="text-sm text-success-800/80">
                  The submission meets the quality standards.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-4 rounded-lg bg-error-50 p-4">
              <ShieldX className="h-8 w-8 text-error-600" />
              <div>
                <p className="text-lg font-semibold text-error-600">
                  Changes Required
                </p>
                <p className="text-sm text-error-800/80">
                  The submission needs revisions before approval.
                </p>
              </div>
            </div>
          )}

          {/* Score gauge */}
          <Card variant="bordered" className="flex items-center gap-6">
            <ScoreGauge score={report.score} />
            <div>
              <p className="text-sm font-medium text-neutral-500">
                Quality Score
              </p>
              <p className="text-3xl font-bold text-neutral-800">
                {report.score}
                <span className="text-lg text-neutral-400">/100</span>
              </p>
            </div>
          </Card>

          {/* Review body */}
          <Card variant="bordered">
            <h3 className="flex items-center gap-2 text-base font-semibold text-neutral-800">
              <FileText className="h-5 w-5 text-neutral-400" />
              Review Details
            </h3>
            <div className="mt-3">{renderMarkdown(report.body)}</div>
          </Card>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-3">
            {isClient && report.verdict === "PASS" && (
              <Button
                variant="web3"
                onClick={() =>
                  router.push(
                    `/gigs/${params.id}/milestones/${params.milestoneId}`,
                  )
                }
              >
                Approve Milestone
              </Button>
            )}
            {isFreelancer && report.verdict === "FAIL" && (
              <Button
                variant="primary"
                onClick={() =>
                  router.push(
                    `/gigs/${params.id}/milestones/${params.milestoneId}/submit`,
                  )
                }
              >
                Submit Revision
              </Button>
            )}
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
      )}
    </div>
  );
}

export default function AIReviewPage() {
  return (
    <AuthGuard>
      <ReviewContent />
    </AuthGuard>
  );
}
