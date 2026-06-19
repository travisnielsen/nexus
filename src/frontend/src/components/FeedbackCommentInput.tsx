"use client";

import React, { useState } from "react";

export interface FeedbackCommentInputProps {
  messageId: string;
  onSubmit: (messageId: string, comment: string) => Promise<void>;
  onDismiss: (messageId: string) => Promise<void> | void;
  isSubmitting?: boolean;
}

export function FeedbackCommentInput({
  messageId,
  onSubmit,
  onDismiss,
  isSubmitting = false,
}: FeedbackCommentInputProps) {
  const [comment, setComment] = useState("");

  const handleSubmit = async () => {
    await onSubmit(messageId, comment);
  };

  const handleDismiss = async () => {
    await onDismiss(messageId);
  };

  return (
    <div className="mt-4 max-w-md rounded-lg border border-red-500/30 bg-red-500/10 p-3 space-y-2.5">
      <label className="block text-sm font-medium text-red-300">
        What went wrong? (optional)
      </label>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Tell us more about this response..."
        className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500/50"
        rows={2}
        disabled={isSubmitting}
      />
      <div className="flex gap-2 pt-1">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : "Save feedback"}
        </button>
        <button
          onClick={handleDismiss}
          disabled={isSubmitting}
          className="rounded bg-gray-700 px-3 py-1.5 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
