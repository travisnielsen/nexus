export type SessionAvailability = "available" | "unavailable";

export interface SessionSummary {
  session_id: string;
  title: string;
  title_source: "first_message" | "timestamp_fallback" | "user_edited";
  display_datetime: string;
  last_activity_at: string;
  availability: SessionAvailability;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
  limit: number;
}

export interface SessionLoadResponse {
  session: SessionSummary;
  linkage: {
    session_id: string;
    copilot_thread_id: string;
    maf_service_session_id: string;
    foundry_conversation_id: string;
    last_verified_at: string;
  };
  transcript: Array<Record<string, unknown>>;
  restoration_status: "full" | "partial" | "none";
  restoration_manifest: SessionArtifact[];
}

export type ArtifactRestorationStatus = "restored" | "unsupported" | "missing_data" | "failed";

export interface SessionArtifact {
  artifact_id: string;
  session_id: string;
  message_id: string;
  transcript_index: number;
  artifact_type: string;
  restoration_status: ArtifactRestorationStatus;
  restoration_descriptor?: Record<string, unknown> | null;
  fallback_text?: string | null;
}

export interface SessionMutationResult {
  session_id: string;
  mutation_type: "rename" | "delete";
  status: "applied" | "rejected";
  title?: string | null;
  conflict_reason?: string | null;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

function buildAuthHeaders(accessToken?: string | null): HeadersInit | undefined {
  if (!accessToken) {
    return undefined;
  }
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

export async function listSessions(
  signal?: AbortSignal,
  accessToken?: string | null,
): Promise<SessionListResponse> {
  const response = await fetch("/api/sessions", {
    method: "GET",
    headers: buildAuthHeaders(accessToken),
    signal,
    cache: "no-store",
  });
  return parseJson<SessionListResponse>(response);
}

export async function loadSession(
  sessionId: string,
  signal?: AbortSignal,
  accessToken?: string | null,
): Promise<SessionLoadResponse> {
  const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: "GET",
    headers: buildAuthHeaders(accessToken),
    signal,
    cache: "no-store",
  });
  return parseJson<SessionLoadResponse>(response);
}

export async function renameSession(
  sessionId: string,
  title: string,
  accessToken?: string | null,
): Promise<SessionMutationResult> {
  const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(buildAuthHeaders(accessToken) ?? {}),
    },
    body: JSON.stringify({ title }),
  });
  return parseJson<SessionMutationResult>(response);
}

export async function deleteSession(
  sessionId: string,
  accessToken?: string | null,
): Promise<SessionMutationResult> {
  const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
    headers: buildAuthHeaders(accessToken),
  });
  return parseJson<SessionMutationResult>(response);
}
