"use client";

import { useMemo } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { useAccessToken } from "@/lib/useAccessToken";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { loginRequest } from "@/lib/msalConfig";
import { ThreadIdContext } from "./NoAuthCopilotKit";

/**
 * Generate a stable thread ID for this session.
 * Uses crypto.randomUUID() which is available in modern browsers.
 * The ID is stable for the component lifecycle (session).
 */
function useStableThreadId(): string {
  return useMemo(() => {
    // Generate a new thread ID for this session
    // This will be stable across re-renders but new for each page load
    return crypto.randomUUID();
  }, []);
}

interface AuthenticatedCopilotKitProps {
  children: React.ReactNode;
}

/**
 * CopilotKit wrapper for the logistics agent with Azure AD authentication.
 * This component must be rendered inside MsalProvider context.
 * Uses Next.js API route as a proxy to forward requests with auth headers.
 * 
 * Provides a stable threadId for conversation continuity across messages.
 * This enables the backend to chain Azure response_ids for multi-turn conversations.
 */
export function AuthenticatedCopilotKit({ children }: AuthenticatedCopilotKitProps) {
  const threadId = useStableThreadId();
  const { accessToken, isLoading } = useAccessToken();
  const isAuthenticated = useIsAuthenticated();
  const { instance } = useMsal();

  // Force sign-in if not authenticated
  const handleSignIn = async () => {
    try {
      await instance.loginRedirect(loginRequest);
    } catch (e) {
      console.error("Login failed:", e);
    }
  };

  // Show sign-in prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
        <span>Please sign in to use the logistics agent</span>
        <button
          onClick={handleSignIn}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Sign In
        </button>
      </div>
    );
  }

  // Show loading state while acquiring token
  if (isLoading && !accessToken) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <span>Authenticating...</span>
      </div>
    );
  }

  // If authenticated but no token (error state), show retry option
  if (!accessToken) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
        <span>Unable to acquire access token</span>
        <button
          onClick={handleSignIn}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Sign In Again
        </button>
      </div>
    );
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${accessToken}`,
  };

  // Use Next.js API route as a proxy to the backend
  // The proxy forwards requests to /logistics on the backend
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="logistics_agent"
      headers={headers}
      threadId={threadId}
    >
      <ThreadIdContext.Provider value={threadId}>
        {children}
      </ThreadIdContext.Provider>
    </CopilotKit>
  );
}
