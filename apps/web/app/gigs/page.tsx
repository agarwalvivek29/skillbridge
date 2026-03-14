"use client";

import { useCallback, useEffect, useState } from "react";
import { Search, SlidersHorizontal, X, Briefcase } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState } from "@/components/ui/EmptyState";
import { GigCard } from "@/components/gigs/GigCard";
import { GigCardSkeleton } from "@/components/gigs/GigCardSkeleton";
import { Footer } from "@/components/layout/Footer";
import { fetchGigs, type GigQueryParams } from "@/lib/api/gigs";
import type { Gig } from "@/types/gig";

const categories = [
  "All Categories",
  "Web Development",
  "Mobile Development",
  "Smart Contracts",
  "Design",
  "Data Science",
  "DevOps",
  "Security Audit",
  "Other",
];

const sortOptions = [
  { label: "Newest First", value: "created_at" },
  { label: "Budget: High to Low", value: "budget_desc" },
  { label: "Deadline: Soonest", value: "deadline" },
];

const PAGE_SIZE = 12;

export default function GigDiscoveryPage() {
  const [gigs, setGigs] = useState<Gig[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("created_at");
  const [minBudget, setMinBudget] = useState("");
  const [maxBudget, setMaxBudget] = useState("");
  const [skillsInput, setSkillsInput] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);

  const loadGigs = useCallback(async () => {
    setLoading(true);
    try {
      const params: GigQueryParams = {
        page,
        page_size: PAGE_SIZE,
        sort,
        status: "OPEN",
      };
      if (search) params.search = search;
      if (category && category !== "All Categories") params.category = category;
      if (minBudget) params.min_budget = minBudget;
      if (maxBudget) params.max_budget = maxBudget;
      if (skillsInput) {
        params.skills = skillsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      }

      const res = await fetchGigs(params);
      setGigs(res.gigs);
      setTotalPages(res.total_pages);
      setTotal(res.total);
    } catch {
      setGigs([]);
      setTotalPages(1);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, sort, search, category, minBudget, maxBudget, skillsInput]);

  useEffect(() => {
    loadGigs();
  }, [loadGigs]);

  useEffect(() => {
    setPage(1);
  }, [search, category, sort, minBudget, maxBudget, skillsInput]);

  const resetFilters = () => {
    setSearch("");
    setCategory("");
    setSort("created_at");
    setMinBudget("");
    setMaxBudget("");
    setSkillsInput("");
    setPage(1);
  };

  const hasActiveFilters =
    search ||
    (category && category !== "All Categories") ||
    minBudget ||
    maxBudget ||
    skillsInput;

  return (
    <>
      <div className="mx-auto max-w-[1280px] px-4 py-8 md:px-6 md:py-12">
        {/* Header */}
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-neutral-800 md:text-3xl">
            Browse Gigs
          </h1>
          <p className="text-neutral-500">
            Find funded projects ready for talented freelancers.
          </p>
        </div>

        {/* Search + Sort + Filter toggle */}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              placeholder="Search gigs by title or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-lg border border-neutral-300 bg-white pl-9 pr-3 text-sm placeholder:text-neutral-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
            />
          </div>

          <div className="flex gap-2">
            <Select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              options={sortOptions}
              className="w-44"
            />
            <Button
              variant={filtersOpen ? "primary" : "outline"}
              size="md"
              onClick={() => setFiltersOpen(!filtersOpen)}
            >
              <SlidersHorizontal className="h-4 w-4" />
              <span className="hidden sm:inline">Filters</span>
            </Button>
          </div>
        </div>

        {/* Collapsible Filters — horizontal bar instead of sidebar */}
        {filtersOpen && (
          <div className="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-neutral-600">
                  Category
                </label>
                <Select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  options={categories.map((cat) => ({
                    value: cat,
                    label: cat,
                  }))}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-neutral-600">
                  Budget Range
                </label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    placeholder="Min"
                    value={minBudget}
                    onChange={(e) => setMinBudget(e.target.value)}
                  />
                  <span className="text-neutral-400">—</span>
                  <Input
                    type="number"
                    placeholder="Max"
                    value={maxBudget}
                    onChange={(e) => setMaxBudget(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-neutral-600">
                  Skills
                </label>
                <Input
                  placeholder="e.g. React, Solidity"
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                />
              </div>
              <div className="flex items-end">
                {hasActiveFilters && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    className="w-full"
                  >
                    <X className="h-4 w-4" />
                    Reset
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Results count */}
        {!loading && (
          <p className="mt-6 text-sm text-neutral-500">
            {total} {total === 1 ? "gig" : "gigs"} found
          </p>
        )}

        {/* Gig Grid — full width, no sidebar stealing space */}
        <div className="mt-4">
          {loading ? (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <GigCardSkeleton key={i} />
              ))}
            </div>
          ) : gigs.length > 0 ? (
            <>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {gigs.map((gig) => (
                  <GigCard key={gig.id} gig={gig} />
                ))}
              </div>
              {totalPages > 1 && (
                <div className="mt-8 flex justify-center">
                  <Pagination
                    currentPage={page}
                    totalPages={totalPages}
                    onPageChange={setPage}
                  />
                </div>
              )}
            </>
          ) : (
            <EmptyState
              icon={Briefcase}
              title="No gigs found"
              description={
                hasActiveFilters
                  ? "Try adjusting your filters or search terms."
                  : "There are no open gigs at the moment."
              }
              actionLabel={hasActiveFilters ? "Reset Filters" : undefined}
              onAction={hasActiveFilters ? resetFilters : undefined}
            />
          )}
        </div>
      </div>

      <Footer />
    </>
  );
}
