"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  Briefcase,
  Code,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Card } from "@/components/ui/Card";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { useAuthStore } from "@/lib/stores/auth";
import { createProfile, type ProfilePayload } from "@/lib/api/users";
import { cn } from "@/lib/utils";

type Role = "CLIENT" | "FREELANCER";

interface FormState {
  name: string;
  bio: string;
  skills: string[];
  location: string;
  company_name: string;
  website: string;
  hourly_rate: string;
  portfolio_url: string;
  github_username: string;
}

const INITIAL_FORM: FormState = {
  name: "",
  bio: "",
  skills: [],
  location: "",
  company_name: "",
  website: "",
  hourly_rate: "",
  portfolio_url: "",
  github_username: "",
};

const STEPS = [
  { label: "Role", value: 0 },
  { label: "Profile", value: 1 },
  { label: "Complete", value: 2 },
];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {STEPS.map((s, i) => (
        <div key={s.value} className="flex items-center gap-2">
          <div
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors",
              i < current
                ? "bg-success-500 text-white"
                : i === current
                  ? "bg-primary-600 text-white"
                  : "border border-neutral-300 text-neutral-400",
            )}
          >
            {i < current ? <CheckCircle className="h-4 w-4" /> : i + 1}
          </div>
          <span
            className={cn(
              "text-sm font-medium",
              i === current ? "text-neutral-800" : "text-neutral-400",
            )}
          >
            {s.label}
          </span>
          {i < STEPS.length - 1 && (
            <div className="mx-2 h-px w-8 bg-neutral-200" />
          )}
        </div>
      ))}
    </div>
  );
}

function OnboardingContent() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const token = useAuthStore((s) => s.token);

  const [currentStep, setCurrentStep] = useState(0);
  const [role, setRole] = useState<Role | null>(null);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [skillInput, setSkillInput] = useState("");
  const [errors, setErrors] = useState<
    Partial<Record<keyof FormState, string>>
  >({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const updateField = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const addSkill = () => {
    const tag = skillInput.trim();
    if (tag && !form.skills.includes(tag)) {
      setForm((prev) => ({ ...prev, skills: [...prev.skills, tag] }));
      setErrors((prev) => ({ ...prev, skills: undefined }));
    }
    setSkillInput("");
  };

  const removeSkill = (skill: string) => {
    setForm((prev) => ({
      ...prev,
      skills: prev.skills.filter((s) => s !== skill),
    }));
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addSkill();
    }
  };

  const validateProfile = (): boolean => {
    const newErrors: Partial<Record<keyof FormState, string>> = {};

    if (!form.name.trim()) {
      newErrors.name = "Display name is required";
    }
    if (!form.bio.trim()) {
      newErrors.bio = "Bio is required";
    }
    if (form.skills.length === 0) {
      newErrors.skills = "Add at least one skill";
    }
    if (role === "FREELANCER" && !form.hourly_rate) {
      newErrors.hourly_rate = "Hourly rate is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!role || !validateProfile()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const payload: ProfilePayload = {
        role,
        name: form.name.trim(),
        bio: form.bio.trim(),
        skills: form.skills,
        ...(form.location && { location: form.location.trim() }),
        ...(role === "CLIENT" &&
          form.company_name && { company_name: form.company_name.trim() }),
        ...(role === "CLIENT" &&
          form.website && { website: form.website.trim() }),
        ...(role === "FREELANCER" &&
          form.hourly_rate && {
            hourly_rate: parseFloat(form.hourly_rate),
          }),
        ...(role === "FREELANCER" &&
          form.portfolio_url && {
            portfolio_url: form.portfolio_url.trim(),
          }),
        ...(role === "FREELANCER" &&
          form.github_username && {
            github_username: form.github_username.trim(),
          }),
      };

      const updatedUser = await createProfile(payload);
      if (token) {
        setAuth(token, updatedUser);
      }
      setCurrentStep(2);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to create profile",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-[768px] space-y-8">
        <StepIndicator current={currentStep} />

        {/* Step 1: Role Selection */}
        {currentStep === 0 && (
          <div className="space-y-6">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-neutral-800">
                How will you use SkillBridge?
              </h1>
              <p className="mt-2 text-sm text-neutral-500">
                Choose your role. You can change this later.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <button
                onClick={() => setRole("CLIENT")}
                className={cn(
                  "group rounded-lg border-2 p-6 text-left transition-all hover:shadow-md",
                  role === "CLIENT"
                    ? "border-primary-500 bg-primary-50"
                    : "border-neutral-200 bg-white hover:border-primary-200",
                )}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                  <Briefcase className="h-6 w-6 text-primary-600" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-neutral-800">
                  I&apos;m hiring
                </h3>
                <p className="mt-1 text-sm text-neutral-500">
                  Post gigs, review work, and release payments through smart
                  contract escrow.
                </p>
              </button>

              <button
                onClick={() => setRole("FREELANCER")}
                className={cn(
                  "group rounded-lg border-2 p-6 text-left transition-all hover:shadow-md",
                  role === "FREELANCER"
                    ? "border-primary-500 bg-primary-50"
                    : "border-neutral-200 bg-white hover:border-primary-200",
                )}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-web3-100">
                  <Code className="h-6 w-6 text-web3-600" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-neutral-800">
                  I&apos;m a freelancer
                </h3>
                <p className="mt-1 text-sm text-neutral-500">
                  Find gigs, submit work, and earn with AI-verified deliveries
                  and on-chain reputation.
                </p>
              </button>
            </div>

            <div className="flex justify-end">
              <Button
                variant="primary"
                size="lg"
                disabled={!role}
                onClick={() => setCurrentStep(1)}
              >
                Continue
                <ArrowRight className="h-5 w-5" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Profile Setup */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-neutral-800">
                Set up your profile
              </h1>
              <p className="mt-2 text-sm text-neutral-500">
                Tell us about yourself.{" "}
                {role === "FREELANCER"
                  ? "Clients will see this when reviewing proposals."
                  : "Freelancers will see this on your gig listings."}
              </p>
            </div>

            <Card variant="bordered" className="space-y-5">
              <div className="flex items-center gap-3 border-b border-neutral-200 pb-4">
                <User className="h-5 w-5 text-primary-500" />
                <h2 className="text-lg font-semibold text-neutral-800">
                  Basic Info
                </h2>
              </div>

              <Input
                label="Display Name"
                placeholder="Your name or username"
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                error={errors.name}
              />

              <Textarea
                label="Bio"
                placeholder="Tell us about yourself and your experience..."
                value={form.bio}
                onChange={(e) => updateField("bio", e.target.value)}
                error={errors.bio}
              />

              {/* Skills tag input */}
              <div className="flex flex-col">
                <label className="mb-1.5 text-sm font-medium text-neutral-700">
                  Skills
                </label>
                <div className="flex flex-wrap gap-2">
                  {form.skills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700"
                    >
                      {skill}
                      <button
                        onClick={() => removeSkill(skill)}
                        className="ml-0.5 rounded-full p-0.5 hover:bg-primary-100"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <Input
                    placeholder="Type a skill and press Enter"
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={handleSkillKeyDown}
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="md"
                    onClick={addSkill}
                    disabled={!skillInput.trim()}
                  >
                    Add
                  </Button>
                </div>
                {errors.skills && (
                  <p className="mt-1.5 text-sm text-error-500">
                    {errors.skills}
                  </p>
                )}
              </div>

              <Input
                label="Location"
                placeholder="City, Country (optional)"
                value={form.location}
                onChange={(e) => updateField("location", e.target.value)}
              />
            </Card>

            {/* Role-specific fields */}
            {role === "CLIENT" && (
              <Card variant="bordered" className="space-y-5">
                <div className="flex items-center gap-3 border-b border-neutral-200 pb-4">
                  <Briefcase className="h-5 w-5 text-primary-500" />
                  <h2 className="text-lg font-semibold text-neutral-800">
                    Company Details
                  </h2>
                </div>
                <Input
                  label="Company Name"
                  placeholder="Your company or organization"
                  value={form.company_name}
                  onChange={(e) => updateField("company_name", e.target.value)}
                />
                <Input
                  label="Website"
                  placeholder="https://yourcompany.com"
                  value={form.website}
                  onChange={(e) => updateField("website", e.target.value)}
                />
              </Card>
            )}

            {role === "FREELANCER" && (
              <Card variant="bordered" className="space-y-5">
                <div className="flex items-center gap-3 border-b border-neutral-200 pb-4">
                  <Code className="h-5 w-5 text-web3-500" />
                  <h2 className="text-lg font-semibold text-neutral-800">
                    Freelancer Details
                  </h2>
                </div>
                <Input
                  label="Hourly Rate (USD)"
                  type="number"
                  placeholder="50"
                  value={form.hourly_rate}
                  onChange={(e) => updateField("hourly_rate", e.target.value)}
                  error={errors.hourly_rate}
                />
                <Input
                  label="Portfolio URL"
                  placeholder="https://yourportfolio.com"
                  value={form.portfolio_url}
                  onChange={(e) => updateField("portfolio_url", e.target.value)}
                />
                <Input
                  label="GitHub Username"
                  placeholder="yourgithub"
                  value={form.github_username}
                  onChange={(e) =>
                    updateField("github_username", e.target.value)
                  }
                />
              </Card>
            )}

            {submitError && (
              <p className="text-center text-sm text-error-500">
                {submitError}
              </p>
            )}

            <div className="flex justify-between">
              <Button
                variant="ghost"
                size="lg"
                onClick={() => setCurrentStep(0)}
              >
                <ArrowLeft className="h-5 w-5" />
                Back
              </Button>
              <Button
                variant="primary"
                size="lg"
                loading={isSubmitting}
                onClick={handleSubmit}
              >
                Complete Setup
                <ArrowRight className="h-5 w-5" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Complete */}
        {currentStep === 2 && (
          <div className="flex flex-col items-center space-y-6 py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success-50">
              <CheckCircle className="h-8 w-8 text-success-500" />
            </div>
            <div className="text-center">
              <h1 className="text-2xl font-bold text-neutral-800">
                You&apos;re all set!
              </h1>
              <p className="mt-2 text-sm text-neutral-500">
                Your profile is ready.{" "}
                {role === "CLIENT"
                  ? "Start posting gigs and finding talent."
                  : "Browse available gigs and start earning."}
              </p>
            </div>
            <Button
              variant="primary"
              size="lg"
              onClick={() => router.push("/dashboard")}
            >
              Go to Dashboard
              <ArrowRight className="h-5 w-5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <AuthGuard>
      <OnboardingContent />
    </AuthGuard>
  );
}
