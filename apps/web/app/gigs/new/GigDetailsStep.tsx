"use client";

import { X } from "lucide-react";
import { useState } from "react";
import { Input, Textarea, Select } from "@/components/ui";
import type { GigFormData } from "./page";

const CATEGORIES = [
  { value: "", label: "Select a category" },
  { value: "web-development", label: "Web Development" },
  { value: "mobile-development", label: "Mobile Development" },
  { value: "smart-contracts", label: "Smart Contracts" },
  { value: "design", label: "Design" },
  { value: "data-science", label: "Data Science" },
  { value: "devops", label: "DevOps" },
  { value: "security", label: "Security Audit" },
  { value: "other", label: "Other" },
];

interface Props {
  data: GigFormData;
  errors: Record<string, string>;
  onChange: (data: GigFormData) => void;
}

export function GigDetailsStep({ data, errors, onChange }: Props) {
  const [skillInput, setSkillInput] = useState("");

  function addSkill() {
    const skill = skillInput.trim();
    if (skill && !data.skills.includes(skill)) {
      onChange({ ...data, skills: [...data.skills, skill] });
    }
    setSkillInput("");
  }

  function removeSkill(skill: string) {
    onChange({ ...data, skills: data.skills.filter((s) => s !== skill) });
  }

  return (
    <div className="space-y-5">
      <Input
        label="Gig Title"
        placeholder="e.g. Build a DeFi Dashboard"
        value={data.title}
        error={errors.title}
        onChange={(e) => onChange({ ...data, title: e.target.value })}
      />

      <Textarea
        label="Description"
        placeholder="Describe the work needed, context, and expectations..."
        value={data.description}
        error={errors.description}
        onChange={(e) => onChange({ ...data, description: e.target.value })}
      />

      <Select
        label="Category"
        options={CATEGORIES}
        value={data.category}
        error={errors.category}
        onChange={(e) => onChange({ ...data, category: e.target.value })}
      />

      <div>
        <label className="mb-1.5 block text-sm font-medium text-neutral-700">
          Required Skills
        </label>
        <div className="flex gap-2">
          <input
            className="h-10 flex-1 rounded-md border border-neutral-300 px-3 text-base placeholder:text-neutral-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            placeholder="Type a skill and press Enter"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addSkill();
              }
            }}
          />
        </div>
        {data.skills.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {data.skills.map((skill) => (
              <span
                key={skill}
                className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700"
              >
                {skill}
                <button
                  onClick={() => removeSkill(skill)}
                  className="ml-0.5 rounded-full p-0.5 hover:bg-primary-100"
                  aria-label={`Remove ${skill}`}
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
        value={data.deadline}
        onChange={(e) => onChange({ ...data, deadline: e.target.value })}
        helperText="Optional — when should the work be completed?"
      />
    </div>
  );
}
