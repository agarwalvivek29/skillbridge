"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Button } from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { createGig, type CreateGigPayload } from "@/lib/api/gigs";
import { GigDetailsStep } from "./GigDetailsStep";
import { MilestonesStep } from "./MilestonesStep";
import { PreviewStep } from "./PreviewStep";

export interface GigFormData {
  title: string;
  description: string;
  category: string;
  skills: string[];
  deadline: string;
  milestones: MilestoneFormData[];
}

export interface MilestoneFormData {
  id: string;
  name: string;
  description: string;
  acceptance_criteria: string;
  amount: string;
  currency: string;
}

const STEPS = ["Details", "Milestones", "Preview", "Submit"];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2 py-6">
      {STEPS.map((label, i) => {
        const completed = i < current;
        const active = i === current;
        return (
          <div key={label} className="flex items-center gap-2">
            {i > 0 && (
              <div
                className={cn(
                  "h-px w-8 sm:w-12",
                  completed ? "bg-success-500" : "bg-neutral-300",
                )}
              />
            )}
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold",
                  completed && "bg-success-500 text-white",
                  active && "bg-primary-600 text-white",
                  !completed &&
                    !active &&
                    "border border-neutral-300 text-neutral-400",
                )}
              >
                {completed ? <Check className="h-4 w-4" /> : i + 1}
              </div>
              <span
                className={cn(
                  "hidden text-sm font-medium sm:inline",
                  active ? "text-neutral-900" : "text-neutral-400",
                )}
              >
                {label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function GigWizardContent() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [formData, setFormData] = useState<GigFormData>({
    title: "",
    description: "",
    category: "",
    skills: [],
    deadline: "",
    milestones: [
      {
        id: crypto.randomUUID(),
        name: "",
        description: "",
        acceptance_criteria: "",
        amount: "",
        currency: "USDC",
      },
    ],
  });

  function validateStep0(): boolean {
    const e: Record<string, string> = {};
    if (!formData.title.trim()) e.title = "Title is required";
    if (!formData.description.trim()) e.description = "Description is required";
    if (!formData.category) e.category = "Select a category";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function validateStep1(): boolean {
    const e: Record<string, string> = {};
    if (formData.milestones.length === 0) {
      e.milestones = "At least one milestone is required";
    }
    for (let i = 0; i < formData.milestones.length; i++) {
      const m = formData.milestones[i];
      if (!m.name.trim()) e[`milestone_${i}_name`] = "Name is required";
      if (!m.amount || parseFloat(m.amount) <= 0)
        e[`milestone_${i}_amount`] = "Valid amount required";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleNext() {
    if (step === 0 && !validateStep0()) return;
    if (step === 1 && !validateStep1()) return;
    setStep((s) => Math.min(s + 1, 3));
  }

  function handleBack() {
    setStep((s) => Math.max(s - 1, 0));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setErrors({});
    try {
      const payload: CreateGigPayload = {
        title: formData.title,
        description: formData.description,
        category: formData.category,
        skills: formData.skills,
        deadline: formData.deadline || null,
        milestones: formData.milestones.map((m) => ({
          title: m.name,
          description: m.description,
          acceptance_criteria: m.acceptance_criteria,
          amount: m.amount,
          currency: m.currency,
        })),
      };
      const gig = await createGig(payload);
      toast.success("Gig created! Now fund the escrow.");
      router.push(`/gigs/${gig.id}/fund`);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create gig";
      toast.error(message);
      if (message.includes("title")) setErrors({ title: message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-neutral-800">Post a New Gig</h1>
      <StepIndicator current={step} />

      <div className="mt-4">
        {step === 0 && (
          <GigDetailsStep
            data={formData}
            errors={errors}
            onChange={setFormData}
          />
        )}
        {step === 1 && (
          <MilestonesStep
            data={formData}
            errors={errors}
            onChange={setFormData}
          />
        )}
        {(step === 2 || step === 3) && (
          <PreviewStep data={formData} onEdit={setStep} />
        )}
      </div>

      <div className="mt-8 flex justify-between border-t border-neutral-200 pt-4">
        {step > 0 ? (
          <Button variant="ghost" onClick={handleBack} disabled={submitting}>
            Back
          </Button>
        ) : (
          <div />
        )}
        {step < 2 && <Button onClick={handleNext}>Continue</Button>}
        {step === 2 && (
          <Button onClick={() => setStep(3)}>Review & Submit</Button>
        )}
        {step === 3 && (
          <Button onClick={handleSubmit} loading={submitting}>
            Submit Gig
          </Button>
        )}
      </div>
    </div>
  );
}

export default function NewGigPage() {
  return (
    <AuthGuard>
      <GigWizardContent />
    </AuthGuard>
  );
}
