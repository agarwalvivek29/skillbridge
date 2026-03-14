"use client";

import { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import {
  Plus,
  Pencil,
  Trash2,
  FolderOpen,
  BadgeCheck,
  ExternalLink,
  Github,
  X,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  getMyPortfolio,
  createPortfolioItem,
  updatePortfolioItem,
  deletePortfolioItem,
  getUploadUrl,
  type PortfolioPayload,
} from "@/lib/api/portfolio";
import type { PortfolioItem } from "@/types/portfolio";

function PortfolioForm({
  initial,
  onSubmit,
  onCancel,
  saving,
}: {
  initial?: PortfolioItem;
  onSubmit: (payload: PortfolioPayload) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [projectUrl, setProjectUrl] = useState(initial?.project_url ?? "");
  const [githubUrl, setGithubUrl] = useState(initial?.github_url ?? "");
  const [tags, setTags] = useState(initial?.tags.join(", ") ?? "");
  const [coverUrl, setCoverUrl] = useState(initial?.cover_image_url ?? "");
  const [uploading, setUploading] = useState(false);

  const handleImageUpload = async (file: File) => {
    setUploading(true);
    try {
      const { upload_url, file_key } = await getUploadUrl(file.name);
      await fetch(upload_url, { method: "PUT", body: file });
      setCoverUrl(file_key);
    } catch {
      // Upload failed silently
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      title,
      description,
      project_url: projectUrl || undefined,
      github_url: githubUrl || undefined,
      cover_image_url: coverUrl || undefined,
      tags: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
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
        required
      />
      <Input
        label="Project URL"
        type="url"
        value={projectUrl}
        onChange={(e) => setProjectUrl(e.target.value)}
        placeholder="https://example.com"
      />
      <Input
        label="GitHub URL"
        type="url"
        value={githubUrl}
        onChange={(e) => setGithubUrl(e.target.value)}
        placeholder="https://github.com/..."
      />
      <Input
        label="Skills/Tags (comma separated)"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        placeholder="React, TypeScript, Solidity"
      />
      <div>
        <label className="mb-1.5 block text-sm font-medium text-neutral-700">
          Cover Image
        </label>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleImageUpload(file);
          }}
          className="text-sm text-neutral-600"
          disabled={uploading}
        />
        {uploading && <Spinner size="sm" className="mt-2" />}
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={saving}>
          {initial ? "Update" : "Add Item"}
        </Button>
      </div>
    </form>
  );
}

function PortfolioContent() {
  const user = useAuthStore((s) => s.user);
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<PortfolioItem | undefined>();
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    if (!user?.id) return;
    setLoading(true);
    getMyPortfolio(user.id)
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user?.id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (payload: PortfolioPayload) => {
    setSaving(true);
    try {
      if (editItem) {
        await updatePortfolioItem(editItem.id, payload);
      } else {
        await createPortfolioItem(payload);
      }
      setModalOpen(false);
      setEditItem(undefined);
      load();
    } catch {
      // Error handled silently
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePortfolioItem(id);
      setDeleteConfirm(null);
      load();
    } catch {
      // Error handled silently
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-neutral-800">Portfolio</h1>
        <Button
          variant="primary"
          onClick={() => {
            setEditItem(undefined);
            setModalOpen(true);
          }}
        >
          <Plus className="mr-1.5 h-4 w-4" />
          Add Item
        </Button>
      </div>

      {items.length === 0 ? (
        <EmptyState
          icon={FolderOpen}
          title="No portfolio items"
          description="Add your first project to showcase your work."
          actionLabel="Add Item"
          onAction={() => setModalOpen(true)}
        />
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <Card
              key={item.id}
              className="group relative flex flex-col overflow-hidden border border-neutral-200 p-0 transition-shadow hover:shadow-md"
            >
              {/* Cover image / URL preview / placeholder */}
              <div className="relative h-44 bg-gradient-to-br from-primary-50 to-web3-50">
                {item.cover_image_url ? (
                  <Image
                    src={item.cover_image_url}
                    alt={item.title}
                    fill
                    className="object-cover"
                  />
                ) : item.project_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={`https://api.microlink.io/?url=${encodeURIComponent(item.project_url)}&screenshot=true&meta=false&embed=screenshot.url`}
                    alt={`Preview of ${item.title}`}
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      const target = e.currentTarget;
                      target.style.display = "none";
                      target.parentElement?.classList.add(
                        "items-center",
                        "justify-center",
                      );
                      const fallback = document.createElement("div");
                      fallback.className =
                        "flex h-full w-full items-center justify-center";
                      fallback.innerHTML =
                        '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-primary-200"><path d="M5 17H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-1"/><polygon points="12 15 17 21 7 21 12 15"/></svg>';
                      target.parentElement?.appendChild(fallback);
                    }}
                  />
                ) : item.github_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={`https://opengraph.githubassets.com/1/${item.github_url.replace("https://github.com/", "")}`}
                    alt={`GitHub preview of ${item.title}`}
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <FolderOpen className="h-12 w-12 text-primary-200" />
                  </div>
                )}
                {item.verified_delivery && (
                  <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-green-500 px-2.5 py-1 text-xs font-medium text-white shadow-sm">
                    <BadgeCheck className="h-3.5 w-3.5" />
                    Verified
                  </span>
                )}
                {/* Edit/delete overlay */}
                <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    onClick={() => {
                      setEditItem(item);
                      setModalOpen(true);
                    }}
                    className="rounded-md bg-white/90 p-1.5 text-neutral-600 shadow-sm backdrop-blur hover:bg-white hover:text-primary-600"
                    aria-label="Edit"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(item.id)}
                    className="rounded-md bg-white/90 p-1.5 text-neutral-600 shadow-sm backdrop-blur hover:bg-white hover:text-error-500"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="flex flex-1 flex-col p-4">
                <h3 className="text-base font-semibold text-neutral-800">
                  {item.title}
                </h3>
                <p className="mt-1.5 line-clamp-3 flex-1 text-sm leading-relaxed text-neutral-500">
                  {item.description}
                </p>

                {/* Tags */}
                {item.tags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {item.tags.map((tag) => (
                      <Badge key={tag} variant="default">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Links */}
                {(item.project_url || item.github_url) && (
                  <div className="mt-4 flex items-center gap-3 border-t border-neutral-100 pt-3">
                    {item.project_url && (
                      <a
                        href={item.project_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 transition-colors hover:text-primary-700"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Live Demo
                      </a>
                    )}
                    {item.github_url && (
                      <a
                        href={item.github_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-800"
                      >
                        <Github className="h-4 w-4" />
                        Source
                      </a>
                    )}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditItem(undefined);
        }}
        title={editItem ? "Edit Portfolio Item" : "Add Portfolio Item"}
      >
        <PortfolioForm
          initial={editItem}
          onSubmit={handleSubmit}
          onCancel={() => {
            setModalOpen(false);
            setEditItem(undefined);
          }}
          saving={saving}
        />
      </Modal>

      {/* Delete Confirmation */}
      <Modal
        open={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        title="Delete Portfolio Item"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-neutral-600">
          Are you sure you want to delete this portfolio item? This action
          cannot be undone.
        </p>
      </Modal>
    </div>
  );
}

export default function PortfolioPage() {
  return (
    <AuthGuard>
      <DashboardLayout>
        <PortfolioContent />
      </DashboardLayout>
    </AuthGuard>
  );
}
