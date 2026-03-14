"use client";
import { formatAmountWithCurrency } from "@/lib/format";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle,
  Circle,
  Clock,
  FileText,
  GitPullRequest,
  Upload,
  Shield,
  ChevronDown,
  ChevronRight,
  User,
  DollarSign,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { Avatar } from "@/components/ui/Avatar";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  getWorkspace,
  type WorkspaceData,
  type WorkspaceSubmission,
} from "@/lib/api/workspace";
import { cn } from "@/lib/utils";

const milestoneStatusIcon: Record<string, typeof CheckCircle> = {
  PAID: CheckCircle,
  APPROVED: CheckCircle,
  SUBMITTED: Upload,
  UNDER_REVIEW: Clock,
  IN_PROGRESS: Circle,
  PENDING: Circle,
};

function MilestoneTimeline({
  milestones,
  submissions,
  gigId,
}: {
  milestones: WorkspaceData["gig"]["milestones"];
  submissions: WorkspaceSubmission[];
  gigId: string;
}) {
  const [expanded, setExpanded] = useState<string | null>(
    milestones.find(
      (m) =>
        m.status === "IN_PROGRESS" ||
        m.status === "SUBMITTED" ||
        m.status === "UNDER_REVIEW" ||
        m.status === "REVISION_REQUESTED",
    )?.id ??
      milestones[0]?.id ??
      null,
  );

  return (
    <div className="space-y-0">
      {milestones.map((m, i) => {
        const Icon = milestoneStatusIcon[m.status] ?? Circle;
        const isExpanded = expanded === m.id;
        const msSubmissions = submissions.filter(
          (s) => s.milestone_id === m.id,
        );
        const isActive =
          m.status === "IN_PROGRESS" ||
          m.status === "SUBMITTED" ||
          m.status === "UNDER_REVIEW" ||
          m.status === "REVISION_REQUESTED";
        const isDone = m.status === "PAID" || m.status === "APPROVED";

        return (
          <div key={m.id} className="relative">
            {/* Vertical line */}
            {i < milestones.length - 1 && (
              <div
                className={cn(
                  "absolute left-4 top-10 h-full w-0.5",
                  isDone ? "bg-success-500" : "bg-neutral-200",
                )}
              />
            )}

            <button
              onClick={() => setExpanded(isExpanded ? null : m.id)}
              className="flex w-full items-start gap-3 rounded-lg p-3 text-left transition-colors hover:bg-neutral-50"
            >
              <div
                className={cn(
                  "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                  isDone
                    ? "bg-success-50 text-success-500"
                    : isActive
                      ? "bg-primary-50 text-primary-500"
                      : "bg-neutral-100 text-neutral-400",
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-neutral-800">
                    {m.title}
                  </h3>
                  <StatusBadge status={m.status} />
                </div>
                <p className="mt-0.5 text-xs text-neutral-500">
                  {formatAmountWithCurrency(
                    m.amount,
                    m.currency || gig.currency,
                  )}
                </p>
              </div>
              {isExpanded ? (
                <ChevronDown className="mt-1 h-4 w-4 text-neutral-400" />
              ) : (
                <ChevronRight className="mt-1 h-4 w-4 text-neutral-400" />
              )}
            </button>

            {isExpanded && (
              <div className="ml-11 space-y-4 pb-4">
                {m.description && (
                  <p className="text-sm text-neutral-600">{m.description}</p>
                )}

                {/* Submit button for current milestone */}
                {isActive && (
                  <Link href={`/gigs/${gigId}/milestones/${m.id}/submit`}>
                    <Button variant="primary" size="sm">
                      <Upload className="mr-1.5 h-4 w-4" />
                      Submit Work
                    </Button>
                  </Link>
                )}

                {/* Submissions */}
                {msSubmissions.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-medium text-neutral-500 uppercase">
                      Submissions
                    </h4>
                    {msSubmissions.map((s) => (
                      <Card key={s.id} variant="flat" className="p-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {s.repo_url ? (
                              <GitPullRequest className="h-4 w-4 text-primary-500" />
                            ) : (
                              <FileText className="h-4 w-4 text-neutral-400" />
                            )}
                            <span className="text-xs text-neutral-600">
                              {s.repo_url
                                ? "PR Submission"
                                : `${s.file_keys.length} file(s)`}
                            </span>
                            <span className="text-xs text-neutral-400">
                              {new Date(s.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          {s.review_verdict && (
                            <Badge
                              variant={
                                s.review_verdict === "PASS"
                                  ? "success"
                                  : "error"
                              }
                            >
                              <Shield className="mr-1 h-3 w-3" />
                              {s.review_verdict}
                            </Badge>
                          )}
                        </div>
                        {s.notes && (
                          <p className="mt-2 text-xs text-neutral-500">
                            {s.notes}
                          </p>
                        )}
                        {s.repo_url && (
                          <a
                            href={s.repo_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1 inline-block text-xs text-primary-600 hover:text-primary-700"
                          >
                            View PR
                          </a>
                        )}
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function WorkspaceContent() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<WorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getWorkspace(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6">
        <EmptyState
          icon={FileText}
          title="Workspace not found"
          description={error ?? "Could not load workspace data."}
        />
      </div>
    );
  }

  const { gig, submissions } = data;
  const completedCount = gig.milestones.filter(
    (m) => m.status === "PAID" || m.status === "APPROVED",
  ).length;

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-8 md:px-6">
      {/* Gig summary */}
      <Card className="mb-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-xl font-bold text-neutral-800">{gig.title}</h1>
            <div className="mt-2 flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-sm text-neutral-500">
                <User className="h-4 w-4" />
                {gig.client_name ?? "Client"}
              </div>
              <StatusBadge status={gig.status} />
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-neutral-800">
              {formatAmountWithCurrency(gig.total_amount, gig.currency)}
            </div>
            <p className="text-xs text-neutral-500">
              {completedCount}/{gig.milestones.length} milestones completed
            </p>
          </div>
        </div>
      </Card>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Milestone tracker */}
        <div className="lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold text-neutral-800">
            Milestone Tracker
          </h2>
          <Card>
            <MilestoneTimeline
              milestones={gig.milestones}
              submissions={submissions}
              gigId={gig.id}
            />
          </Card>
        </div>

        {/* Sidebar info */}
        <div className="space-y-6">
          <Card>
            <h3 className="text-sm font-semibold text-neutral-800">
              Gig Summary
            </h3>
            <div className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-neutral-500">Total Budget</span>
                <span className="font-medium text-neutral-700">
                  {formatAmountWithCurrency(gig.total_amount, gig.currency)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-500">Milestones</span>
                <span className="font-medium text-neutral-700">
                  {gig.milestones.length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-500">Status</span>
                <StatusBadge status={gig.status} />
              </div>
              {gig.deadline && (
                <div className="flex justify-between">
                  <span className="text-neutral-500">Deadline</span>
                  <span className="font-medium text-neutral-700">
                    {new Date(gig.deadline).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-neutral-800">Skills</h3>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {gig.skills.map((skill) => (
                <Badge key={skill} variant="default">
                  {skill}
                </Badge>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <AuthGuard>
      <WorkspaceContent />
    </AuthGuard>
  );
}
