"use client";

import React, { useEffect, useState } from "react";
import {
  FeedbackSubmissionOutcome,
  FeedbackSubmissionRequest,
  FeedbackRating,
} from "@/lib/logisticsTypes";
import { useThreadId } from "@/components/NoAuthCopilotKit";
import { useSafeAccessToken } from "@/lib/useSafeAccessToken";

interface OverallFeedbackCardProps {
  prompt?: string;
  cardTurnId?: string;
  onSubmitted?: () => void;
  collapseOnSubmit?: boolean;
}

// Keeps submitted-card collapse stable if the component remounts for the same card turn.
const submittedCardTurnIds = new Set<string>();
// Keeps cancelled-card collapse stable if the component remounts for the same card turn.
const cancelledCardTurnIds = new Set<string>();

function getCollapsedState(cardTurnId?: string) {
  if (cardTurnId && cancelledCardTurnIds.has(cardTurnId)) {
    return { isCollapsed: true, collapsedMessage: "Feedback cancelled" };
  }
  if (cardTurnId && submittedCardTurnIds.has(cardTurnId)) {
    return { isCollapsed: true, collapsedMessage: "Feedback submitted" };
  }
  return { isCollapsed: false, collapsedMessage: "Feedback submitted" };
}

export function OverallFeedbackCard({
  prompt,
  cardTurnId,
  onSubmitted,
  collapseOnSubmit = false,
}: OverallFeedbackCardProps) {
  const initialCollapsedState = getCollapsedState(cardTurnId);
  const [rating, setRating] = useState<FeedbackRating | null>(null);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsedState.isCollapsed);
  const [collapsedMessage, setCollapsedMessage] = useState(initialCollapsedState.collapsedMessage);

  const conversationId = useThreadId();
  const accessToken = useSafeAccessToken();
  const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (!cardTurnId) {
      return;
    }

    if (cancelledCardTurnIds.has(cardTurnId)) {
      setCollapsedMessage("Feedback cancelled");
      setIsCollapsed(true);
      return;
    }

    if (submittedCardTurnIds.has(cardTurnId)) {
      setCollapsedMessage("Feedback submitted");
      setIsCollapsed(true);
    }
  }, [cardTurnId]);

  if (!isAuthEnabled) {
    return null;
  }

  if (isCollapsed) {
    const cancelledStyle = collapsedMessage === "Feedback cancelled";
    return (
      <div
        className={`my-2 rounded-lg border px-3 py-2 text-sm ${
          cancelledStyle
            ? "border-white/15 bg-white/5 text-gray-200"
            : "border-green-400/40 bg-green-500/10 text-green-200"
        }`}
      >
        {collapsedMessage}
      </div>
    );
  }

  const submit = async () => {
    if (!conversationId) {
      return;
    }
    if (!rating) {
      setStatusMessage("Please select Good or Needs work before submitting.");
      return;
    }
    if (!accessToken) {
      setStatusMessage("Authentication token unavailable. Please sign in again and retry.");
      return;
    }

    const payload: FeedbackSubmissionRequest = {
      feedback_kind: "overall_experience",
      conversation_id: conversationId,
      rating,
      comment: comment.trim() || undefined,
      card_turn_id: cardTurnId,
      source_surface: "overall_feedback_card",
    };

    setIsSubmitting(true);
    setStatusMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/logistics/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(payload),
      });
      const outcome = (await response.json()) as FeedbackSubmissionOutcome | { detail?: string };

      if (!response.ok || !(outcome as FeedbackSubmissionOutcome).accepted) {
        setStatusMessage("We couldn't save your feedback right now. Please try again.");
        return;
      }

      if (onSubmitted) {
        onSubmitted();
        return;
      }

      if (collapseOnSubmit) {
        if (cardTurnId) {
          submittedCardTurnIds.add(cardTurnId);
          cancelledCardTurnIds.delete(cardTurnId);
        }
        setCollapsedMessage("Feedback submitted");
        setIsCollapsed(true);
        return;
      }

      setStatusMessage("Feedback saved. Thank you.");
      setComment("");
    } catch {
      setStatusMessage("We couldn't save your feedback right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="my-2 rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-3">
      <div className="mb-1.5 flex items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-indigo-100 leading-tight">Feeback</h4>
          <p className="text-xs text-indigo-200/80">
            {prompt || "How was your overall experience with this application?"}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setRating("positive")}
          className={`rounded px-2.5 py-1 text-sm ${
            rating === "positive"
              ? "border border-green-400/50 bg-green-500/30 text-green-100"
              : "bg-white/10 text-gray-100 hover:bg-white/15"
          }`}
        >
          👍 Good
        </button>
        <button
          type="button"
          onClick={() => setRating("negative")}
          className={`rounded px-2.5 py-1 text-sm ${
            rating === "negative"
              ? "border border-red-400/50 bg-red-500/30 text-red-100"
              : "bg-white/10 text-gray-100 hover:bg-white/15"
          }`}
        >
          👎 Needs work
        </button>
      </div>

      <textarea
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        rows={2}
        className="mt-1 w-full rounded border border-white/10 bg-white/5 px-3 py-2 text-sm leading-5 text-white placeholder:text-gray-500"
        placeholder="Optional: share more details"
      />

      <div className="mt-1.5 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => {
            setCollapsedMessage("Feedback cancelled");
            if (cardTurnId) {
              cancelledCardTurnIds.add(cardTurnId);
              submittedCardTurnIds.delete(cardTurnId);
            }
            setIsCollapsed(true);
          }}
          className="rounded bg-white/10 px-2.5 py-1 text-xs text-gray-200 hover:bg-white/15"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => void submit()}
          disabled={isSubmitting || !conversationId}
          className="rounded bg-indigo-600 px-2.5 py-1 text-xs text-white disabled:opacity-50"
        >
          {isSubmitting ? "Submitting..." : "Submit"}
        </button>
      </div>

      <div aria-live="polite" className="mt-0.5 text-xs text-gray-200">
        {statusMessage}
      </div>
    </div>
  );
}
