import type { SessionArtifact, SessionLoadResponse } from "./sessionApi";

export interface HydratedArtifact {
  artifactId: string;
  messageId: string;
  transcriptIndex: number;
  title: string;
  description: string;
}

export interface ArtifactFallbackNotice {
  artifactId: string;
  messageId: string;
  transcriptIndex: number;
  message: string;
}

export interface HydratedArtifactState {
  restorationStatus: SessionLoadResponse["restoration_status"];
  restored: HydratedArtifact[];
  fallbackNotices: ArtifactFallbackNotice[];
}

function buildTitle(artifact: SessionArtifact): string {
  if (artifact.artifact_type === "tool_result_text") {
    return "Tool Result";
  }
  if (artifact.artifact_type === "assistant_tool_call_summary") {
    return "Tool Call Summary";
  }
  return "Unsupported Artifact";
}

function buildDescription(artifact: SessionArtifact): string {
  const descriptor = artifact.restoration_descriptor ?? {};

  if (artifact.artifact_type === "tool_result_text") {
    const text = typeof descriptor.text === "string" ? descriptor.text : "";
    const clipped = text.trim().slice(0, 160);
    return clipped || "Prior tool output restored.";
  }

  if (artifact.artifact_type === "assistant_tool_call_summary") {
    const names = Array.isArray(descriptor.tool_names)
      ? descriptor.tool_names.filter((value): value is string => typeof value === "string")
      : [];
    return names.length > 0 ? `Tools: ${names.join(", ")}` : "Tool call details restored.";
  }

  return "Artifact restored.";
}

export function hydrateSessionArtifacts(payload: SessionLoadResponse): HydratedArtifactState {
  const restored: HydratedArtifact[] = [];
  const fallbackNotices: ArtifactFallbackNotice[] = [];

  for (const artifact of payload.restoration_manifest) {
    if (artifact.restoration_status === "restored") {
      restored.push({
        artifactId: artifact.artifact_id,
        messageId: artifact.message_id,
        transcriptIndex: artifact.transcript_index,
        title: buildTitle(artifact),
        description: buildDescription(artifact),
      });
      continue;
    }

    fallbackNotices.push({
      artifactId: artifact.artifact_id,
      messageId: artifact.message_id,
      transcriptIndex: artifact.transcript_index,
      message:
        artifact.fallback_text?.trim() ||
        "This prior artifact could not be rehydrated. Transcript continuity is preserved.",
    });
  }

  restored.sort((a, b) => a.transcriptIndex - b.transcriptIndex);
  fallbackNotices.sort((a, b) => a.transcriptIndex - b.transcriptIndex);

  // Hydration is read-only and never executes tools or side effects.
  return {
    restorationStatus: payload.restoration_status,
    restored,
    fallbackNotices,
  };
}
