"use client";

import { Pencil } from "lucide-react";
import { Card, StatusBadge } from "@/components/ui";
import type { GigFormData } from "./page";

interface Props {
  data: GigFormData;
  onEdit: (step: number) => void;
}

export function PreviewStep({ data, onEdit }: Props) {
  const total = data.milestones.reduce(
    (sum, m) => sum + (parseFloat(m.amount) || 0),
    0,
  );

  return (
    <div className="space-y-6">
      <Card variant="bordered">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-neutral-800">
              {data.title || "Untitled Gig"}
            </h2>
            <div className="mt-2 flex flex-wrap gap-2">
              {data.category && (
                <span className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-600">
                  {data.category}
                </span>
              )}
              <StatusBadge status="DRAFT" />
            </div>
          </div>
          <button
            onClick={() => onEdit(0)}
            className="rounded p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
            aria-label="Edit details"
          >
            <Pencil className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 whitespace-pre-wrap text-sm text-neutral-600">
          {data.description || "No description provided."}
        </div>

        {data.skills.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {data.skills.map((skill) => (
              <span
                key={skill}
                className="rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700"
              >
                {skill}
              </span>
            ))}
          </div>
        )}

        {data.deadline && (
          <p className="mt-3 text-sm text-neutral-500">
            Deadline: {new Date(data.deadline).toLocaleDateString()}
          </p>
        )}
      </Card>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-neutral-800">Milestones</h3>
          <button
            onClick={() => onEdit(1)}
            className="rounded p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
            aria-label="Edit milestones"
          >
            <Pencil className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          {data.milestones.map((m, i) => (
            <Card key={m.id} variant="flat">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-semibold text-neutral-700">
                    {i + 1}. {m.name || "Untitled milestone"}
                  </p>
                  {m.description && (
                    <p className="mt-1 text-sm text-neutral-500">
                      {m.description}
                    </p>
                  )}
                  {m.acceptance_criteria && (
                    <p className="mt-1 text-xs text-neutral-400">
                      Acceptance: {m.acceptance_criteria}
                    </p>
                  )}
                </div>
                <span className="whitespace-nowrap text-sm font-semibold text-neutral-900">
                  {m.amount || "0"} {m.currency}
                </span>
              </div>
            </Card>
          ))}
        </div>

        <div className="mt-4 rounded-lg bg-neutral-50 p-4">
          <div className="flex items-center justify-between">
            <span className="font-medium text-neutral-600">Total Budget</span>
            <span className="text-lg font-bold text-neutral-900">
              {total.toFixed(2)} {data.milestones[0]?.currency ?? "USDC"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
