import { useCallback, useEffect, useMemo, useState } from "react";

import {
  deleteSession,
  listSessions,
  loadSession,
  renameSession,
  type SessionBlockedResponse,
  type SessionLoadApiResponse,
  type SessionLoadResponse,
  type SessionMutationResult,
  type SessionSummary,
} from "./sessionApi";
import {
  hydrateSessionArtifacts,
  type ArtifactFallbackNotice,
  type HydratedArtifact,
} from "./sessionArtifactHydration";
import {
  loadSessionCache,
  saveSessionCache,
  type SessionCacheSnapshot,
} from "./sessionCache";

export interface SessionHistoryState {
  sessions: SessionSummary[];
  isLoading: boolean;
  isRestoringSession: boolean;
  error: string | null;
  selectedSessionId: string | null;
  restorationStatus: "full" | "partial" | "none";
  restoredArtifacts: HydratedArtifact[];
  artifactFallbackNotices: ArtifactFallbackNotice[];
  loadedSession: SessionLoadResponse | null;
  mutationStatusBySession: Record<string, "pending" | "synced" | "failed">;
  refresh: (options?: { silent?: boolean }) => Promise<void>;
  selectSession: (
    sessionId: string,
    options?: { blockReason?: string | null },
  ) => Promise<SessionLoadResponse | null>;
  rename: (sessionId: string, title: string) => Promise<void>;
  remove: (sessionId: string) => Promise<void>;
}

function isBlockedSessionResponse(
  payload: SessionLoadApiResponse,
): payload is SessionBlockedResponse {
  return "blocked" in payload && payload.blocked === true;
}

export function useSessionHistory(
  userCacheKey: string,
  accessToken?: string | null,
): SessionHistoryState {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoringSession, setIsRestoringSession] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restorationStatus, setRestorationStatus] = useState<"full" | "partial" | "none">("none");
  const [restoredArtifacts, setRestoredArtifacts] = useState<HydratedArtifact[]>([]);
  const [artifactFallbackNotices, setArtifactFallbackNotices] = useState<ArtifactFallbackNotice[]>([]);
  const [loadedSession, setLoadedSession] = useState<SessionLoadResponse | null>(null);
  const [mutationStatusBySession, setMutationStatusBySession] = useState<
    Record<string, "pending" | "synced" | "failed">
  >({});

  const hydrateFromCache = useCallback((): boolean => {
    const cached = loadSessionCache(userCacheKey);
    if (cached && cached.sessions.length > 0) {
      setSessions(cached.sessions);
      return true;
    }
    return false;
  }, [userCacheKey]);

  const persist = useCallback(
    (nextSessions: SessionSummary[]) => {
      const snapshot: SessionCacheSnapshot = {
        cacheVersion: "1",
        userCacheKey,
        sessions: nextSessions,
        lastSyncedAt: new Date().toISOString(),
      };
      saveSessionCache(snapshot);
    },
    [userCacheKey],
  );

  const refresh = useCallback(async (options?: { silent?: boolean }) => {
    if (!accessToken) {
      return;
    }
    const silent = options?.silent ?? false;
    if (!silent) setIsLoading(true);
    setError(null);
    try {
      const data = await listSessions(undefined, accessToken);
      setSessions((previous) => {
        // Preserve local-first history if backend temporarily returns empty
        // (for example during local backend restarts while metadata is in-memory).
        if (data.sessions.length === 0 && previous.length > 0) {
          return previous;
        }
        persist(data.sessions);
        return data.sessions;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      if (!silent) setIsLoading(false);
    }
  }, [persist, accessToken]);

  const selectSession = useCallback(
    async (sessionId: string, options?: { blockReason?: string | null }) => {
      if (options?.blockReason) {
        setError(options.blockReason);
        return null;
      }

      setError(null);
      setIsRestoringSession(true);
      setIsLoading(true);
      try {
        if (!accessToken) {
          throw new Error("Authentication token unavailable");
        }
        setSelectedSessionId(sessionId);
        const payload: SessionLoadApiResponse = await loadSession(
          sessionId,
          undefined,
          accessToken,
        );
        if (isBlockedSessionResponse(payload)) {
          setError(payload.reason || "Session is unavailable and cannot be resumed");
          setLoadedSession(null);
          setRestorationStatus("none");
          setRestoredArtifacts([]);
          setArtifactFallbackNotices([]);
          return null;
        }

        const hydrated = hydrateSessionArtifacts(payload);
        setLoadedSession(payload);
        setRestorationStatus(hydrated.restorationStatus);
        setRestoredArtifacts(hydrated.restored);
        setArtifactFallbackNotices(hydrated.fallbackNotices);
        return payload;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load session");
        return null;
      } finally {
        setIsRestoringSession(false);
        setIsLoading(false);
      }
    },
    [accessToken],
  );

  const rename = useCallback(
    async (sessionId: string, title: string) => {
      const previous = sessions;
      const optimistic = sessions.map((session) =>
        session.session_id === sessionId ? { ...session, title } : session,
      );
      setSessions(optimistic);
      setMutationStatusBySession((prev) => ({ ...prev, [sessionId]: "pending" }));
      persist(optimistic);
      try {
        const result: SessionMutationResult = await renameSession(sessionId, title, accessToken);
        if (result.status !== "applied") {
          throw new Error(result.conflict_reason || "Rename rejected");
        }
        setMutationStatusBySession((prev) => ({ ...prev, [sessionId]: "synced" }));
        await refresh({ silent: true });
      } catch (err) {
        setSessions(previous);
        persist(previous);
        setError(err instanceof Error ? err.message : "Failed to rename session");
        setMutationStatusBySession((prev) => ({ ...prev, [sessionId]: "failed" }));
      }
    },
    [sessions, persist, refresh, accessToken],
  );

  const remove = useCallback(
    async (sessionId: string) => {
      const previous = sessions;
      const optimistic = sessions.filter((session) => session.session_id !== sessionId);
      setSessions(optimistic);
      setMutationStatusBySession((prev) => ({ ...prev, [sessionId]: "pending" }));
      persist(optimistic);
      try {
        const result: SessionMutationResult = await deleteSession(sessionId, accessToken);
        if (result.status !== "applied") {
          throw new Error(result.conflict_reason || "Delete rejected");
        }
        setMutationStatusBySession((prev) => ({ ...prev, [sessionId]: "synced" }));
        await refresh({ silent: true });
      } catch (err) {
        setSessions(previous);
        persist(previous);
        setError(err instanceof Error ? err.message : "Failed to delete session");
        setMutationStatusBySession((prev) => ({ ...prev, [sessionId]: "failed" }));
      }
    },
    [sessions, persist, refresh, accessToken],
  );

  useEffect(() => {
    const hasCachedData = hydrateFromCache();
    if (accessToken) {
      // If cache data was rendered immediately, sync in background without blocking the UI.
      // If no cache exists, show the loading state so the flyout isn't empty indefinitely.
      void refresh({ silent: hasCachedData });
    }
  }, [hydrateFromCache, refresh, accessToken]);

  return useMemo(
    () => ({
      sessions,
      isLoading,
      isRestoringSession,
      error,
      selectedSessionId,
      restorationStatus,
      restoredArtifacts,
      artifactFallbackNotices,
      loadedSession,
      mutationStatusBySession,
      refresh,
      selectSession,
      rename,
      remove,
    }),
    [
      sessions,
      isLoading,
      isRestoringSession,
      error,
      selectedSessionId,
      restorationStatus,
      restoredArtifacts,
      artifactFallbackNotices,
      loadedSession,
      mutationStatusBySession,
      refresh,
      selectSession,
      rename,
      remove,
    ],
  );
}
