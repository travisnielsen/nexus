"use client";

import { useState, useEffect, useCallback } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { useAccessToken } from "@/lib/useAccessToken";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { loginRequest } from "@/lib/msalConfig";
import { ThreadIdContext, NewChatContext } from "./NoAuthCopilotKit";

/**
 * Create a new Azure Foundry conversation via the backend API.
 * Returns a conv_* ID that Azure manages server-side for history and continuity.
 */
async function createConversation(accessToken: string): Promise<string> {
  const response = await fetch("/api/conversations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to create conversation: ${response.statusText}`);
  }
  const data = await response.json();
  return data.conversationId;
}

interface AuthenticatedCopilotKitProps {
  children: React.ReactNode;
}

/**
 * CopilotKit wrapper for the logistics agent with Azure AD authentication.
 * This component must be rendered inside MsalProvider context.
 * Uses Next.js API route as a proxy to forward requests with auth headers.
 * 
 * Creates an Azure Foundry conversation (conv_*) on mount and uses it as
 * the CopilotKit threadId. This enables AgentSession to manage server-side
 * conversation history natively via use_service_session=True.
 */
export function AuthenticatedCopilotKit({ children }: AuthenticatedCopilotKitProps) {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [convError, setConvError] = useState<string | null>(null);
  const { accessToken, isLoading } = useAccessToken();
  const isAuthenticated = useIsAuthenticated();
  const { instance } = useMsal();

  const initConversation = useCallback(async (token: string) => {
    try {
      setConvError(null);
      const convId = await createConversation(token);
      console.log('[AuthenticatedCopilotKit] Created Azure conversation:', convId);
      setThreadId(convId);
    } catch (err) {
      console.error('[AuthenticatedCopilotKit] Failed to create conversation:', err);
      setConvError(err instanceof Error ? err.message : 'Failed to create conversation');
    }
  }, []);

  // Create conversation once we have an access token
  useEffect(() => {
    let cancelled = false;

    if (accessToken && !threadId && !convError) {
      const timer = setTimeout(() => {
        if (!cancelled) {
          void initConversation(accessToken);
        }
      }, 0);

      return () => {
        cancelled = true;
        clearTimeout(timer);
      };
    }

    return () => {
      cancelled = true;
    };
  }, [accessToken, threadId, convError, initConversation]);

  // New Chat handler: create a fresh conversation
  const handleNewChat = useCallback(() => {
    if (accessToken) {
      setThreadId(null);
      initConversation(accessToken);
    }
  }, [accessToken, initConversation]);

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

  // Show error creating conversation
  if (convError) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
        <span>Failed to initialize conversation</span>
        <span className="text-sm text-red-400">{convError}</span>
        <button
          onClick={() => initConversation(accessToken)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Show loading state while creating conversation
  if (!threadId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <span>Initializing conversation...</span>
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
      <NewChatContext.Provider value={handleNewChat}>
        <ThreadIdContext.Provider value={threadId}>
          {children}
        </ThreadIdContext.Provider>
      </NewChatContext.Provider>
    </CopilotKit>
  );
}
