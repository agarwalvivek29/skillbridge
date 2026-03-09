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
    } catch {
      setGigs([]);
      setTotalPages(1);
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
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-neutral-800 md:text-3xl">
            Browse Gigs
          </h1>
          <p className="text-neutral-500">
            Find funded projects ready for talented freelancers.
          </p>
        </div>

        {/* Search + Sort bar */}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              placeholder="Search gigs by title or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-md border border-neutral-300 pl-9 pr-3 text-base placeholder:text-neutral-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          <Select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            options={sortOptions}
            className="w-full sm:w-48"
          />

          <Button
            variant="outline"
            size="md"
            onClick={() => setFiltersOpen(!filtersOpen)}
            className="sm:hidden"
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </Button>
        </div>

        <div className="mt-6 flex gap-6">
          {/* Filters Sidebar — desktop visible, mobile drawer */}
          <aside
            className={`${
              filtersOpen
                ? "fixed inset-0 z-40 block bg-black/50 sm:static sm:z-auto sm:bg-transparent"
                : "hidden"
            } sm:block sm:w-64 sm:shrink-0`}
          >
            <div
              className={`${
                filtersOpen
                  ? "fixed bottom-0 left-0 right-0 z-50 max-h-[80vh] overflow-y-auto rounded-t-xl bg-white p-4 shadow-xl sm:static sm:max-h-none sm:rounded-t-none sm:p-0 sm:shadow-none"
                  : ""
              }`}
            >
              <div className="flex items-center justify-between sm:hidden">
                <h3 className="text-lg font-semibold text-neutral-800">
                  Filters
                </h3>
                <button
                  onClick={() => setFiltersOpen(false)}
                  className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-neutral-100"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="mt-4 space-y-5 sm:mt-0">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-neutral-700">
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
                  <label className="mb-1.5 block text-sm font-medium text-neutral-700">
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
                  <label className="mb-1.5 block text-sm font-medium text-neutral-700">
                    Skills
                  </label>
                  <Input
                    placeholder="e.g. React, Solidity"
                    value={skillsInput}
                    onChange={(e) => setSkillsInput(e.target.value)}
                  />
                  <p className="mt-1 text-xs text-neutral-400">
                    Comma-separated list
                  </p>
                </div>

                {hasActiveFilters && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    className="w-full"
                  >
                    <X className="h-4 w-4" />
                    Reset Filters
                  </Button>
                )}
              </div>
            </div>
          </aside>

          {/* Gig Grid */}
          <div className="flex-1">
            {loading ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: PAGE_SIZE }).map((_, i) => (
                  <GigCardSkeleton key={i} />
                ))}
              </div>
            ) : gigs.length > 0 ? (
              <>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {gigs.map((gig) => (
                    <GigCard key={gig.id} gig={gig} />
                  ))}
                </div>
                <div className="mt-8 flex justify-center">
                  <Pagination
                    currentPage={page}
                    totalPages={totalPages}
                    onPageChange={setPage}
                  />
                </div>
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
      </div>

      <Footer />
    </>
  );
}
