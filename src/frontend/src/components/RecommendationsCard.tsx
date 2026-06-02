"use client";

import React, { useState } from "react";
import { RecommendationsResult, FeedbackPayload } from "@/lib/logisticsTypes";

export type RecommendationsCardProps = {
  status: string;
  result: unknown;
};

export function RecommendationsCard({ status, result }: RecommendationsCardProps) {
  const [vote, setVote] = useState<'up' | 'down' | null>(null);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (status !== 'complete') {
    return (
      <div className="p-4 my-2 rounded-xl bg-amber-500/10 border border-amber-500/20">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-amber-300">Generating recommendations...</span>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="p-4 my-2 rounded-xl bg-red-500/10 border border-red-500/20">
        <span className="text-red-300">Unable to generate recommendations</span>
      </div>
    );
  }

  const data = result as RecommendationsResult;

  if ('error' in data && data.error) {
    return (
      <div className="p-4 my-2 rounded-xl bg-amber-500/10 border border-amber-500/20">
        <span className="text-amber-300">{String(data.error)}</span>
      </div>
    );
  }

  if (!data.recommendations || data.recommendations.length === 0) {
    return (
      <div className="p-4 my-2 rounded-xl bg-green-500/10 border border-green-500/20">
        <div className="flex items-center gap-2">
          <span className="text-xl">✅</span>
          <div>
            <p className="text-green-300 font-medium">{data.flightNumber} - Optimal</p>
            <p className="text-green-400/80 text-sm">{data.message || `Flight is at ${data.utilizationPercent?.toFixed(1)}% utilization. No action needed.`}</p>
          </div>
        </div>
      </div>
    );
  }

  const handleVote = (newVote: 'up' | 'down') => {
    setVote(prev => prev === newVote ? null : newVote);
  };

  const handleSubmit = async () => {
    if (!vote && !comment.trim()) {
      return;
    }

    setSubmitting(true);

    const payload: FeedbackPayload = {
      flightId: data.flightId,
      flightNumber: data.flightNumber,
      votes: vote ? { overall: vote } : {},
      comment: comment.trim() || undefined,
      timestamp: new Date().toISOString(),
    };

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/logistics/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setSubmitted(true);
      } else {
        console.error('Failed to submit feedback:', await response.text());
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const isHighRisk = data.riskLevel === 'high' || data.riskLevel === 'critical';
  const cardBg = isHighRisk ? 'bg-red-500/10' : 'bg-blue-500/10';
  const cardBorder = isHighRisk ? 'border-red-500/30' : 'border-blue-500/30';
  const titleIcon = isHighRisk ? '⚠️' : '💡';
  const titleText = isHighRisk ? 'Risk Mitigation Recommendations' : 'Optimization Suggestions';

  return (
    <div className={`p-4 my-2 rounded-xl ${cardBg} border ${cardBorder} space-y-3`}>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xl">{titleIcon}</span>
          <h4 className="font-semibold text-white">{titleText}</h4>
        </div>
        <div className="flex items-center gap-2 pl-7">
          <span className="text-sm text-gray-300">{data.flightNumber}</span>
          <span className="text-sm text-gray-400">({data.route})</span>
        </div>
      </div>

      <div className="space-y-2">
        {data.recommendations.map((rec) => (
          <div
            key={rec.id}
            className="p-3 bg-white/5 rounded-lg"
          >
            <span className="text-gray-200 text-sm">{rec.text}</span>
          </div>
        ))}
      </div>

      {!submitted ? (
        <div className="space-y-3 pt-3 border-t border-white/10">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Were these recommendations helpful?</span>
            <div className="flex gap-2">
              <button
                onClick={() => handleVote('up')}
                disabled={submitted}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                  vote === 'up'
                    ? 'bg-green-500/30 text-green-300 border border-green-500/50'
                    : 'bg-white/5 hover:bg-white/10 text-gray-400 hover:text-green-300 border border-white/10'
                }`}
              >
                <span>👍</span>
                <span className="text-sm">Yes</span>
              </button>
              <button
                onClick={() => handleVote('down')}
                disabled={submitted}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                  vote === 'down'
                    ? 'bg-red-500/30 text-red-300 border border-red-500/50'
                    : 'bg-white/5 hover:bg-white/10 text-gray-400 hover:text-red-300 border border-white/10'
                }`}
              >
                <span>👎</span>
                <span className="text-sm">No</span>
              </button>
            </div>
          </div>

          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Additional feedback or suggestions... (optional)"
            className="w-full p-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 text-sm resize-none focus:outline-none focus:border-white/30"
            rows={2}
          />

          <div className="flex justify-end">
            <button
              onClick={handleSubmit}
              disabled={submitting || (!vote && !comment.trim())}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                submitting || (!vote && !comment.trim())
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {submitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </div>
        </div>
      ) : (
        <div className="pt-3 border-t border-white/10">
          <div className="flex items-center gap-2 text-green-400">
            <span>✓</span>
            <span className="text-sm">Thank you for your feedback!</span>
          </div>
        </div>
      )}
    </div>
  );
}
