"use client";

import { Plus, Trash2 } from "lucide-react";
import { Input, Textarea, Select, Button, Card } from "@/components/ui";
import type { GigFormData, MilestoneFormData } from "./page";

const CURRENCIES = [
  { value: "USDC", label: "USDC" },
  { value: "ETH", label: "ETH" },
];

interface Props {
  data: GigFormData;
  errors: Record<string, string>;
  onChange: (data: GigFormData) => void;
}

export function MilestonesStep({ data, errors, onChange }: Props) {
  function addMilestone() {
    const m: MilestoneFormData = {
      id: crypto.randomUUID(),
      name: "",
      description: "",
      acceptance_criteria: "",
      amount: "",
      currency: "USDC",
    };
    onChange({ ...data, milestones: [...data.milestones, m] });
  }

  function removeMilestone(id: string) {
    if (data.milestones.length <= 1) return;
    onChange({
      ...data,
      milestones: data.milestones.filter((m) => m.id !== id),
    });
  }

  function updateMilestone(id: string, updates: Partial<MilestoneFormData>) {
    onChange({
      ...data,
      milestones: data.milestones.map((m) =>
        m.id === id ? { ...m, ...updates } : m,
      ),
    });
  }

  const total = data.milestones.reduce(
    (sum, m) => sum + (parseFloat(m.amount) || 0),
    0,
  );

  const primaryCurrency = data.milestones[0]?.currency ?? "USDC";

  return (
    <div className="space-y-4">
      {errors.milestones && (
        <p className="text-sm text-error-500">{errors.milestones}</p>
      )}

      {data.milestones.map((m, i) => (
        <Card key={m.id} variant="flat" className="relative">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-neutral-700">
              Milestone {i + 1}
            </h3>
            {data.milestones.length > 1 && (
              <button
                onClick={() => removeMilestone(m.id)}
                className="rounded p-1 text-neutral-400 hover:bg-error-50 hover:text-error-500"
                aria-label="Remove milestone"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="space-y-3">
            <Input
              label="Name"
              placeholder="e.g. Smart contract development"
              value={m.name}
              error={errors[`milestone_${i}_name`]}
              onChange={(e) => updateMilestone(m.id, { name: e.target.value })}
            />

            <Textarea
              label="Description"
              placeholder="What work is included in this milestone?"
              value={m.description}
              onChange={(e) =>
                updateMilestone(m.id, { description: e.target.value })
              }
            />

            <Textarea
              label="Acceptance Criteria"
              placeholder="How will you verify this milestone is complete?"
              value={m.acceptance_criteria}
              onChange={(e) =>
                updateMilestone(m.id, {
                  acceptance_criteria: e.target.value,
                })
              }
            />

            <div className="flex gap-3">
              <div className="flex-1">
                <Input
                  label="Budget"
                  type="number"
                  placeholder="0.00"
                  min="0"
                  step="0.01"
                  value={m.amount}
                  error={errors[`milestone_${i}_amount`]}
                  onChange={(e) =>
                    updateMilestone(m.id, { amount: e.target.value })
                  }
                />
              </div>
              <div className="w-28">
                <Select
                  label="Currency"
                  options={CURRENCIES}
                  value={m.currency}
                  onChange={(e) =>
                    updateMilestone(m.id, { currency: e.target.value })
                  }
                />
              </div>
            </div>
          </div>
        </Card>
      ))}

      <Button variant="outline" size="sm" onClick={addMilestone}>
        <Plus className="h-4 w-4" />
        Add Milestone
      </Button>

      <div className="rounded-lg bg-neutral-50 p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-neutral-600">Total Budget</span>
          <span className="text-lg font-bold text-neutral-900">
            {total.toFixed(2)} {primaryCurrency}
          </span>
        </div>
      </div>
    </div>
  );
}
