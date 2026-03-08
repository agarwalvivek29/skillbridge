"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Tab {
  value: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  value?: string;
  onChange?: (value: string) => void;
  className?: string;
}

export function Tabs({ tabs, value, onChange, className }: TabsProps) {
  const [internalValue, setInternalValue] = useState(tabs[0]?.value ?? "");
  const activeValue = value ?? internalValue;

  const handleChange = (v: string) => {
    if (onChange) {
      onChange(v);
    } else {
      setInternalValue(v);
    }
  };

  const activeTab = tabs.find((t) => t.value === activeValue);

  return (
    <div className={className}>
      <div className="flex border-b border-neutral-200" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            role="tab"
            aria-selected={tab.value === activeValue}
            onClick={() => handleChange(tab.value)}
            className={cn(
              "px-4 py-2.5 text-sm font-medium transition-colors",
              tab.value === activeValue
                ? "border-b-2 border-primary-600 text-primary-600"
                : "text-neutral-500 hover:text-neutral-700",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="pt-4">
        {activeTab?.content}
      </div>
    </div>
  );
}
