"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  GitPullRequest,
  Upload,
  X,
  FileText,
  CheckCircle,
  Info,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Button, Card, Input, Textarea, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { createSubmission, getUploadUrl } from "@/lib/api/submissions";

const PR_URL_REGEX = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/pull\/\d+\/?$/;

interface UploadedFile {
  name: string;
  key: string;
  size: number;
}

function SubmitContent() {
  const params = useParams<{ id: string; milestoneId: string }>();
  const router = useRouter();
  const toast = useToast();

  const [activeTab, setActiveTab] = useState("pr");
  const [repoUrl, setRepoUrl] = useState("");
  const [repoUrlError, setRepoUrlError] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [isPrSubmission, setIsPrSubmission] = useState(false);

  // File upload state
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  function validatePrUrl(url: string): boolean {
    if (!url.trim()) {
      setRepoUrlError("PR URL is required");
      return false;
    }
    if (!PR_URL_REGEX.test(url.trim())) {
      setRepoUrlError(
        "Must be a valid GitHub PR URL (https://github.com/owner/repo/pull/N)",
      );
      return false;
    }
    setRepoUrlError(null);
    return true;
  }

  const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      const oversized = fileArray.filter((f) => f.size > MAX_FILE_SIZE);
      if (oversized.length > 0) {
        toast.error(
          `Files must be under 20 MB. Remove: ${oversized.map((f) => f.name).join(", ")}`,
        );
        return;
      }

      setUploading(true);
      try {
        const results: UploadedFile[] = [];

        for (const file of fileArray) {
          const { upload_url, file_key } = await getUploadUrl(file.name);
          await fetch(upload_url, {
            method: "PUT",
            body: file,
            headers: {
              "Content-Type": file.type || "application/octet-stream",
            },
          });
          results.push({ name: file.name, key: file_key, size: file.size });
        }

        setUploadedFiles((prev) => [...prev, ...results]);
        toast.success(
          `${results.length} file${results.length !== 1 ? "s" : ""} uploaded`,
        );
      } catch {
        toast.error("Failed to upload files");
      } finally {
        setUploading(false);
      }
    },
    [toast],
  );

  function removeFile(key: string) {
    setUploadedFiles((prev) => prev.filter((f) => f.key !== key));
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  }

  async function handleSubmit() {
    if (activeTab === "pr") {
      if (!validatePrUrl(repoUrl)) return;
    } else {
      if (uploadedFiles.length === 0) {
        toast.error("Please upload at least one file");
        return;
      }
    }

    setSubmitting(true);
    try {
      await createSubmission({
        milestone_id: params.milestoneId,
        repo_url: activeTab === "pr" ? repoUrl.trim() : undefined,
        file_keys:
          activeTab === "files" ? uploadedFiles.map((f) => f.key) : undefined,
        notes: (activeTab === "pr" ? description : notes) || undefined,
      });
      setIsPrSubmission(activeTab === "pr");
      setSubmitted(true);
      toast.success("Submission received");
    } catch {
      toast.error("Failed to create submission");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <CheckCircle className="mx-auto h-12 w-12 text-success-500" />
        <h2 className="mt-4 text-2xl font-bold text-neutral-800">
          Submission Received
        </h2>
        {isPrSubmission && (
          <div className="mx-auto mt-4 flex max-w-md items-start gap-3 rounded-lg bg-primary-50 p-4 text-left">
            <Info className="mt-0.5 h-5 w-5 shrink-0 text-primary-500" />
            <p className="text-sm text-primary-700">
              AI review has been triggered — you&apos;ll be notified when
              results are ready.
            </p>
          </div>
        )}
        <Button
          variant="primary"
          className="mt-6"
          onClick={() =>
            router.push(`/gigs/${params.id}/milestones/${params.milestoneId}`)
          }
        >
          View Milestone
        </Button>
      </div>
    );
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const prTab = (
    <div className="space-y-4">
      <div>
        <Input
          label="GitHub PR URL"
          placeholder="https://github.com/owner/repo/pull/123"
          value={repoUrl}
          error={repoUrlError ?? undefined}
          onChange={(e) => {
            setRepoUrl(e.target.value);
            if (repoUrlError) validatePrUrl(e.target.value);
          }}
          onBlur={() => {
            if (repoUrl) validatePrUrl(repoUrl);
          }}
        />
      </div>

      <div className="flex items-start gap-3 rounded-lg bg-primary-50 p-3">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary-500" />
        <p className="text-sm text-primary-700">
          Submitting a PR URL will trigger an AI code review via OpenReview
        </p>
      </div>

      <Textarea
        label="Description (optional)"
        placeholder="Add context for the reviewer..."
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        helperText="Provide any additional context about your submission"
      />
    </div>
  );

  const filesTab = (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
          dragActive
            ? "border-primary-400 bg-primary-50"
            : "border-neutral-300 bg-neutral-50 hover:border-neutral-400"
        }`}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.multiple = true;
          input.onchange = (e) => {
            const files = (e.target as HTMLInputElement).files;
            if (files) uploadFiles(files);
          };
          input.click();
        }}
      >
        {uploading ? (
          <Spinner size="md" />
        ) : (
          <>
            <Upload className="h-8 w-8 text-neutral-400" />
            <p className="mt-2 text-sm font-medium text-neutral-600">
              Drag and drop files here, or click to browse
            </p>
            <p className="mt-1 text-xs text-neutral-400">
              Multiple files supported
            </p>
          </>
        )}
      </div>

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          {uploadedFiles.map((file) => (
            <div
              key={file.key}
              className="flex items-center justify-between rounded-md border border-neutral-200 bg-white px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-neutral-400" />
                <span className="text-sm text-neutral-700">{file.name}</span>
                <span className="text-xs text-neutral-400">
                  {formatSize(file.size)}
                </span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(file.key);
                }}
                className="rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <Textarea
        label="Notes"
        placeholder="General notes for the client..."
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
    </div>
  );

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-neutral-800">Submit Work</h1>
      <p className="mt-1 text-sm text-neutral-500">
        Submit your deliverables for this milestone
      </p>

      <Card variant="bordered" className="mt-6">
        <Tabs
          tabs={[
            {
              value: "pr",
              label: "GitHub PR URL",
              content: prTab,
            },
            {
              value: "files",
              label: "File Upload",
              content: filesTab,
            },
          ]}
          value={activeTab}
          onChange={setActiveTab}
        />

        <div className="mt-6 flex justify-end gap-3">
          <Button
            variant="ghost"
            onClick={() =>
              router.push(`/gigs/${params.id}/milestones/${params.milestoneId}`)
            }
          >
            Cancel
          </Button>
          <Button variant="primary" loading={submitting} onClick={handleSubmit}>
            Submit
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default function SubmitWorkPage() {
  return (
    <AuthGuard>
      <SubmitContent />
    </AuthGuard>
  );
}
