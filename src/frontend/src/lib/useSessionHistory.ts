import { useCallback, useEffect, useMemo, useState } from "react";

import {
  deleteSession,
  listSessions,
  loadSession,
  renameSession,
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
  error: string | null;
  selectedSessionId: string | null;
  restorationStatus: "full" | "partial" | "none";
  restoredArtifacts: HydratedArtifact[];
  artifactFallbackNotices: ArtifactFallbackNotice[];
  loadedSession: SessionLoadResponse | null;
  mutationStatusBySession: Record<string, "pending" | "synced" | "failed">;
  refresh: () => Promise<void>;
  selectSession: (
    sessionId: string,
    options?: { blockReason?: string | null },
  ) => Promise<SessionLoadResponse | null>;
  rename: (sessionId: string, title: string) => Promise<void>;
  remove: (sessionId: string) => Promise<void>;
}

export function useSessionHistory(
  userCacheKey: string,
  accessToken?: string | null,
): SessionHistoryState {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restorationStatus, setRestorationStatus] = useState<"full" | "partial" | "none">("none");
  const [restoredArtifacts, setRestoredArtifacts] = useState<HydratedArtifact[]>([]);
  const [artifactFallbackNotices, setArtifactFallbackNotices] = useState<ArtifactFallbackNotice[]>([]);
  const [loadedSession, setLoadedSession] = useState<SessionLoadResponse | null>(null);
  const [mutationStatusBySession, setMutationStatusBySession] = useState<
    Record<string, "pending" | "synced" | "failed">
  >({});

  const hydrateFromCache = useCallback(() => {
    const cached = loadSessionCache(userCacheKey);
    if (cached) {
      setSessions(cached.sessions);
    }
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

  const refresh = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    setIsLoading(true);
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
      setIsLoading(false);
    }
  }, [persist, accessToken]);

  const selectSession = useCallback(
    async (sessionId: string, options?: { blockReason?: string | null }) => {
      if (options?.blockReason) {
        setError(options.blockReason);
        return null;
      }

      setError(null);
      setIsLoading(true);
      try {
        if (!accessToken) {
          throw new Error("Authentication token unavailable");
        }
        setSelectedSessionId(sessionId);
        const payload = await loadSession(sessionId, undefined, accessToken);
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
        await refresh();
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
        await refresh();
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
    hydrateFromCache();
    if (accessToken) {
      void refresh();
    }
  }, [hydrateFromCache, refresh, accessToken]);

  return useMemo(
    () => ({
      sessions,
      isLoading,
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
