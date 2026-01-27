"use client";

import { useAccessToken } from "./useAccessToken";

// Check if auth is enabled at module level
const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

/**
 * Safe wrapper for useAccessToken that returns null when auth is disabled.
 * This allows components to work both with and without authentication.
 */
export function useSafeAccessToken(): string | null {
  // When auth is disabled, we can't use MSAL hooks (no provider context)
  // So we return null directly
  if (!isAuthEnabled) {
    return null;
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const { accessToken } = useAccessToken();
  return accessToken;
}
