"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Scale, Clock, AlertTriangle } from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Spinner,
  StatusBadge,
  EmptyState,
  Breadcrumb,
} from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { fetchArbitrationQueue } from "@/lib/api/disputes";
import type { ArbitrationCase } from "@/types/dispute";

function ArbitrationQueueContent() {
  const router = useRouter();
  const toast = useToast();

  const [cases, setCases] = useState<ArbitrationCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"assigned" | "all">("assigned");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchArbitrationQueue(filter);
      setCases(data);
    } catch {
      toast.error("Failed to load arbitration queue");
    } finally {
      setLoading(false);
    }
  }, [filter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-6">
      <Breadcrumb items={[{ label: "Arbitration" }]} />

      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-web3-50">
            <Scale className="h-5 w-5 text-web3-500" />
          </div>
          <h1 className="text-2xl font-bold text-neutral-800">
            Arbitration Queue
          </h1>
        </div>
        <div className="flex gap-2">
          <Button
            variant={filter === "assigned" ? "primary" : "ghost"}
            size="sm"
            onClick={() => setFilter("assigned")}
          >
            Assigned to Me
          </Button>
          <Button
            variant={filter === "all" ? "primary" : "ghost"}
            size="sm"
            onClick={() => setFilter("all")}
          >
            All Open
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      ) : cases.length === 0 ? (
        <EmptyState
          icon={Scale}
          title="No disputes to review"
          description={
            filter === "assigned"
              ? "You have no disputes assigned for arbitration."
              : "There are no open disputes awaiting arbitration."
          }
          className="mt-8"
        />
      ) : (
        <div className="mt-6 space-y-3">
          {cases.map((c) => (
            <Card
              key={c.id}
              variant="bordered"
              className="cursor-pointer transition-shadow hover:shadow-lg hover:border-primary-200"
              onClick={() => router.push(`/arbitration/${c.dispute_id}`)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-neutral-800">
                      Dispute #{c.dispute_id.slice(0, 8)}
                    </p>
                    <StatusBadge status={c.status} />
                  </div>
                  <p className="mt-1 text-sm text-neutral-600">
                    {c.gig_title} &middot; {c.milestone_title}
                  </p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {c.client_name} vs {c.freelancer_name}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-neutral-500">
                    Filed {new Date(c.filed_date).toLocaleDateString()}
                  </p>
                  <div className="mt-1 flex items-center gap-1 text-xs text-warning-600">
                    <Clock className="h-3 w-3" />
                    Due {new Date(c.deadline).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ArbitrationPage() {
  return (
    <AuthGuard>
      <ArbitrationQueueContent />
    </AuthGuard>
  );
}
