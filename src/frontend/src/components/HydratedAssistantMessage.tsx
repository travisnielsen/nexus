"use client";

import React from "react";
import { AssistantMessage as DefaultAssistantMessage, AssistantMessageProps } from "@copilotkit/react-ui";
import { parseHydratedToolMarker } from "@/lib/sessionTranscriptHydration";
import { RecommendationsCard } from "@/components/RecommendationsCard";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function FilterFlightsBar({ args }: { args: unknown }) {
  const filter = asRecord(args);
  const parts: string[] = [];
  if (typeof filter.route_from === "string") parts.push(filter.route_from);
  if (typeof filter.route_to === "string") parts.push(`→ ${filter.route_to}`);
  if (typeof filter.utilization === "string") parts.push(`(${filter.utilization})`);
  if (typeof filter.risk_level === "string") parts.push(`[${filter.risk_level} risk]`);
  const filterDesc = parts.length > 0 ? parts.join(" ") : "current filters";
  return (
    <div className="flex items-center gap-2 text-sm p-2 my-1 rounded-lg bg-blue-500/10 border border-blue-500/20">
      <span className="text-blue-400">🔍</span>
      <span className="text-blue-300">Loaded {filterDesc}</span>
    </div>
  );
}

function ResetFiltersBar() {
  return (
    <div className="flex items-center gap-2 text-sm p-2 my-1 rounded-lg bg-orange-500/10 border border-orange-500/20">
      <span className="text-orange-400">🔄</span>
      <span className="text-orange-300">Filters cleared</span>
    </div>
  );
}

function AnalyzeFlightsBar({ result }: { result: unknown }) {
  const analysis = asRecord(result);
  return (
    <div className="flex flex-col gap-2 text-sm p-2 my-1 rounded-lg bg-purple-500/10 border border-purple-500/20">
      <div className="flex items-start gap-2">
        <span className="text-purple-400">📊</span>
        <span className="text-purple-300 font-medium">
          {analysis.flight_count !== undefined
            ? `${String(analysis.flight_count)} flights analyzed`
            : "Analysis complete"}
          {analysis.filter_applied && analysis.filter_applied !== "none (all flights)"
            ? ` (${String(analysis.filter_applied)})`
            : ""}
        </span>
      </div>
      {analysis.average_utilization !== undefined && (
        <div className="text-purple-200 text-xs ml-6">
          Average utilization: {String(analysis.average_utilization)}%
        </div>
      )}
    </div>
  );
}

function HistoricalPayloadBar({ args }: { args: unknown }) {
  const params = asRecord(args);
  const route = typeof params.route === "string" ? params.route : "";
  return (
    <div className="flex items-center gap-2 text-sm p-2 my-1 rounded-lg bg-green-500/10 border border-green-500/20">
      <span className="text-green-400">📈</span>
      <span className="text-green-300">Historical data loaded{route ? ` for ${route}` : ""}</span>
    </div>
  );
}

function PredictedPayloadBar({ args }: { args: unknown }) {
  const params = asRecord(args);
  const route = typeof params.route === "string" ? params.route : "";
  return (
    <div className="flex items-center gap-2 text-sm p-2 my-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
      <span className="text-cyan-400">🔮</span>
      <span className="text-cyan-300">Predictions ready{route ? ` for ${route}` : ""}</span>
    </div>
  );
}

/**
 * AssistantMessage renderer that detects historical tool-call messages
 * (emitted by session transcript hydration) and renders the matching React
 * card directly. Non-marker messages fall through to the default renderer.
 */
export function HydratedAssistantMessage(props: AssistantMessageProps) {
  const content = props.message?.content;
  const text = typeof content === "string" ? content : "";

  const hydrated = text ? parseHydratedToolMarker(text) : null;
  if (hydrated) {
    switch (hydrated.toolName) {
      case "filter_flights":
        return <FilterFlightsBar args={hydrated.args} />;
      case "reset_filters":
        return <ResetFiltersBar />;
      case "analyze_flights":
        return <AnalyzeFlightsBar result={hydrated.result} />;
      case "get_historical_payload":
        return <HistoricalPayloadBar args={hydrated.args} />;
      case "get_predicted_payload":
        return <PredictedPayloadBar args={hydrated.args} />;
      case "get_recommendations":
        return <RecommendationsCard status="complete" result={hydrated.result} />;
      default:
        return null;
    }
  }

  return <DefaultAssistantMessage {...props} />;
}
