export interface TraceIdentity {
  conversationId: string;
  turnId?: string;
  runId?: string;
  toolCallId?: string;
  a2aInteractionId?: string;
}

export interface CopilotRuntimeRequestShape {
  threadId?: string;
  runId?: string;
  run?: {
    id?: string;
  };
}

export function extractTraceIdentityFromBody(rawBody: unknown): TraceIdentity | null {
  if (!rawBody || typeof rawBody !== "object") {
    return null;
  }

  const body = rawBody as CopilotRuntimeRequestShape;
  const conversationId = typeof body.threadId === "string" ? body.threadId.trim() : "";
  if (!conversationId) {
    return null;
  }

  const runIdCandidate =
    typeof body.runId === "string"
      ? body.runId
      : typeof body.run?.id === "string"
        ? body.run.id
        : undefined;

  return {
    conversationId,
    runId: runIdCandidate?.trim() || undefined,
  };
}
