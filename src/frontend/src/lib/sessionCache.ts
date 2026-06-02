import type { SessionSummary } from "./sessionApi";

export interface SessionCacheSnapshot {
  cacheVersion: string;
  userCacheKey: string;
  sessions: SessionSummary[];
  lastSyncedAt: string | null;
}

const CACHE_VERSION = "1";
const PREFIX = "session-history";

export function buildSessionCacheKey(userKey: string): string {
  return `${PREFIX}:v${CACHE_VERSION}:${userKey}`;
}

export function loadSessionCache(userKey: string): SessionCacheSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(buildSessionCacheKey(userKey));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as SessionCacheSnapshot;
    if (parsed.cacheVersion !== CACHE_VERSION) {
      return migrateSessionCache(userKey, parsed);
    }
    return parsed;
  } catch {
    return null;
  }
}

export function migrateSessionCache(
  userKey: string,
  snapshot: Partial<SessionCacheSnapshot>,
): SessionCacheSnapshot | null {
  if (!snapshot.sessions || !Array.isArray(snapshot.sessions)) {
    clearSessionCache(userKey);
    return null;
  }
  const migrated: SessionCacheSnapshot = {
    cacheVersion: CACHE_VERSION,
    userCacheKey: userKey,
    sessions: snapshot.sessions,
    lastSyncedAt: snapshot.lastSyncedAt ?? null,
  };
  saveSessionCache(migrated);
  return migrated;
}

export function saveSessionCache(snapshot: SessionCacheSnapshot): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(buildSessionCacheKey(snapshot.userCacheKey), JSON.stringify(snapshot));
}

export function clearSessionCache(userKey: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(buildSessionCacheKey(userKey));
}
