"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { X, Plus } from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import {
  Button,
  Card,
  Input,
  Textarea,
  Select,
  Spinner,
} from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { useAuthStore } from "@/lib/stores/auth";
import { fetchGig, updateGig } from "@/lib/api/gigs";
import type { Gig } from "@/types/gig";

const CATEGORIES = [
  { value: "", label: "Select a category" },
  { value: "web-development", label: "Web Development" },
  { value: "mobile-development", label: "Mobile Development" },
  { value: "smart-contracts", label: "Smart Contracts" },
  { value: "design", label: "Design" },
  { value: "data-science", label: "Data Science" },
  { value: "devops", label: "DevOps" },
  { value: "security-audit", label: "Security Audit" },
  { value: "other", label: "Other" },
];

function EditGigContent() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);

  const [gig, setGig] = useState<Gig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [deadline, setDeadline] = useState("");
  const [editMilestones, setEditMilestones] = useState<
    {
      title: string;
      description: string;
      acceptance_criteria: string;
      amount: string;
      currency: string;
    }[]
  >([]);

  useEffect(() => {
    if (!id) return;
    fetchGig(id)
      .then((g) => {
        setGig(g);
        setTitle(g.title);
        setDescription(g.description);
        setCategory(
          (g as unknown as { tags?: string[] }).tags?.[0] ?? g.category ?? "",
        );
        setSkills(g.skills ?? g.required_skills ?? []);
        setDeadline(g.deadline?.split("T")[0] ?? "");
        setEditMilestones(
          (g.milestones ?? []).map((m) => ({
            title: m.title,
            description: m.description || "",
            acceptance_criteria: "",
            amount: m.amount,
            currency: m.currency || g.currency || "USDC",
          })),
        );
      })
      .catch(() => toast.error("Failed to load gig"))
      .finally(() => setLoading(false));
  }, [id, toast]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!gig) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-neutral-500">Gig not found.</p>
      </div>
    );
  }

  if (gig.client_id !== user?.id) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-neutral-500">You can only edit your own gigs.</p>
      </div>
    );
  }

  if (gig.status !== "DRAFT") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-neutral-500">
          Only draft gigs can be edited. This gig is {gig.status.toLowerCase()}.
        </p>
      </div>
    );
  }

  const addSkill = () => {
    const s = skillInput.trim();
    if (s && !skills.includes(s)) {
      setSkills([...skills, s]);
      setSkillInput("");
    }
  };

  const handleSave = async () => {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    setSaving(true);
    try {
      await updateGig(gig.id, {
        title: title.trim(),
        description: description.trim(),
        category,
        skills,
        deadline: deadline || null,
        milestones: editMilestones,
      });
      toast.success("Gig updated");
      router.push(`/gigs/${gig.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update gig");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-neutral-800">Edit Gig</h1>
      <p className="mt-1 text-sm text-neutral-500">
        Update your gig details before publishing.
      </p>

      <Card className="mt-6 space-y-5">
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Textarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={6}
          required
        />
        <Select
          label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          options={CATEGORIES}
        />
        <div>
          <label className="mb-1.5 block text-sm font-medium text-neutral-700">
            Required Skills
          </label>
          <div className="flex gap-2">
            <Input
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              placeholder="Add a skill"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addSkill();
                }
              }}
            />
            <Button type="button" variant="outline" onClick={addSkill}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          {skills.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {skills.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700"
                >
                  {s}
                  <button
                    onClick={() => setSkills(skills.filter((x) => x !== s))}
                    className="text-primary-400 hover:text-primary-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
        <Input
          label="Deadline"
          type="date"
          value={deadline}
          onChange={(e) => setDeadline(e.target.value)}
        />
      </Card>

      {/* Milestones */}
      <Card className="mt-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-800">Milestones</h2>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              setEditMilestones([
                ...editMilestones,
                {
                  title: "",
                  description: "",
                  acceptance_criteria: "",
                  amount: "",
                  currency: gig.currency || "USDC",
                },
              ])
            }
          >
            <Plus className="mr-1 h-4 w-4" />
            Add
          </Button>
        </div>
        {editMilestones.map((m, i) => (
          <div
            key={i}
            className="space-y-3 rounded-lg border border-neutral-200 p-4"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-neutral-500">
                Milestone {i + 1}
              </span>
              {editMilestones.length > 1 && (
                <button
                  onClick={() =>
                    setEditMilestones(editMilestones.filter((_, j) => j !== i))
                  }
                  className="text-xs text-error-500 hover:underline"
                >
                  Remove
                </button>
              )}
            </div>
            <Input
              label="Title"
              value={m.title}
              onChange={(e) => {
                const updated = [...editMilestones];
                updated[i] = { ...updated[i], title: e.target.value };
                setEditMilestones(updated);
              }}
              required
            />
            <Textarea
              label="Description"
              value={m.description}
              onChange={(e) => {
                const updated = [...editMilestones];
                updated[i] = { ...updated[i], description: e.target.value };
                setEditMilestones(updated);
              }}
              rows={2}
            />
            <Textarea
              label="Acceptance Criteria"
              value={m.acceptance_criteria}
              onChange={(e) => {
                const updated = [...editMilestones];
                updated[i] = {
                  ...updated[i],
                  acceptance_criteria: e.target.value,
                };
                setEditMilestones(updated);
              }}
              rows={2}
              placeholder="What must be true for this milestone to be approved?"
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                label={`Amount (${m.currency})`}
                type="number"
                step="0.01"
                value={m.amount}
                onChange={(e) => {
                  const updated = [...editMilestones];
                  updated[i] = { ...updated[i], amount: e.target.value };
                  setEditMilestones(updated);
                }}
                required
              />
              <Select
                label="Currency"
                value={m.currency}
                onChange={(e) => {
                  const updated = [...editMilestones];
                  updated[i] = { ...updated[i], currency: e.target.value };
                  setEditMilestones(updated);
                }}
                options={[
                  { value: "USDC", label: "USDC" },
                  { value: "SOL", label: "SOL" },
                ]}
              />
            </div>
          </div>
        ))}
      </Card>

      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button variant="primary" loading={saving} onClick={handleSave}>
          Save Changes
        </Button>
      </div>
    </div>
  );
}

export default function EditGigPage() {
  return (
    <AuthGuard>
      <EditGigContent />
    </AuthGuard>
  );
}
