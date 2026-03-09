"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { Button, Modal, Textarea } from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { createRating } from "@/lib/api/ratings";
import type { RatingTag } from "@/types/rating";

const RATING_TAGS: RatingTag[] = [
  "Great communication",
  "High quality work",
  "Delivered on time",
  "Would hire again",
];

interface RatingModalProps {
  open: boolean;
  onClose: () => void;
  gigId: string;
  rateeId: string;
  rateeName: string;
  onSubmitted?: () => void;
}

function StarRating({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          onClick={() => onChange(star)}
          className="rounded-sm p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-1"
          aria-label={`Rate ${star} star${star !== 1 ? "s" : ""}`}
        >
          <Star
            className={`h-8 w-8 transition-colors ${
              star <= (hovered || value)
                ? "fill-secondary-400 text-secondary-400"
                : "fill-transparent text-neutral-300"
            }`}
          />
        </button>
      ))}
    </div>
  );
}

export function RatingModal({
  open,
  onClose,
  gigId,
  rateeId,
  rateeName,
  onSubmitted,
}: RatingModalProps) {
  const toast = useToast();

  const [score, setScore] = useState(0);
  const [review, setReview] = useState("");
  const [tags, setTags] = useState<RatingTag[]>([]);
  const [submitting, setSubmitting] = useState(false);

  function toggleTag(tag: RatingTag) {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  }

  async function handleSubmit() {
    if (score === 0) {
      toast.error("Please select a rating");
      return;
    }

    setSubmitting(true);
    try {
      await createRating({
        gig_id: gigId,
        ratee_id: rateeId,
        score,
        review: review.trim() || undefined,
        tags,
      });
      toast.success("Rating submitted!");
      onSubmitted?.();
      onClose();
    } catch {
      toast.error("Failed to submit rating");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Rate ${rateeName}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Skip for Now
          </Button>
          <Button
            variant="primary"
            loading={submitting}
            onClick={handleSubmit}
            disabled={score === 0}
          >
            Submit Rating
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {/* Star rating */}
        <div>
          <label className="mb-2 block text-sm font-medium text-neutral-700">
            Overall rating
          </label>
          <StarRating value={score} onChange={setScore} />
          {score > 0 && (
            <p className="mt-1 text-sm text-neutral-500">
              {score === 1
                ? "Poor"
                : score === 2
                  ? "Fair"
                  : score === 3
                    ? "Good"
                    : score === 4
                      ? "Very Good"
                      : "Excellent"}
            </p>
          )}
        </div>

        {/* Tags */}
        <div>
          <label className="mb-2 block text-sm font-medium text-neutral-700">
            What stood out?
          </label>
          <div className="flex flex-wrap gap-2">
            {RATING_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                  tags.includes(tag)
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-neutral-200 bg-white text-neutral-600 hover:border-neutral-300"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Written review */}
        <Textarea
          label="Written review (optional)"
          placeholder="Share your experience working with this person..."
          value={review}
          onChange={(e) => setReview(e.target.value)}
        />
      </div>
    </Modal>
  );
}
