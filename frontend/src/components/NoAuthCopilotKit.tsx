"use client";

import { useState, useEffect, useCallback, createContext, useContext } from "react";
import { CopilotKit } from "@copilotkit/react-core";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Context to expose threadId to child components
export const ThreadIdContext = createContext<string | null>(null);

// Hook to access the threadId from child components
export function useThreadId(): string | null {
  return useContext(ThreadIdContext);
}

// Hook to access the newChat callback from child components
export const NewChatContext = createContext<(() => void) | null>(null);
export function useNewChat(): (() => void) | null {
  return useContext(NewChatContext);
}

interface NoAuthCopilotKitProps {
  children: React.ReactNode;
}

/**
 * Create a new Azure Foundry conversation via the backend API.
 * Returns a conv_* ID that Azure manages server-side for history and continuity.
 */
async function createConversation(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to create conversation: ${response.statusText}`);
  }
  const data = await response.json();
  return data.conversationId;
}

/**
 * CopilotKit wrapper without authentication.
 * Use this when AUTH_ENABLED=false to bypass Azure AD authentication.
 * Uses Next.js API route as a proxy to forward requests to the backend.
 * 
 * Creates an Azure Foundry conversation (conv_*) on mount and uses it as
 * the CopilotKit threadId. This enables AgentSession to manage server-side
 * conversation history natively via use_service_session=True.
 */
export function NoAuthCopilotKit({ children }: NoAuthCopilotKitProps) {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const initConversation = useCallback(async () => {
    try {
      setError(null);
      const convId = await createConversation();
      console.log('[NoAuthCopilotKit] Created Azure conversation:', convId);
      setThreadId(convId);
    } catch (err) {
      console.error('[NoAuthCopilotKit] Failed to create conversation:', err);
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
    }
  }, []);

  // Create conversation on mount
  useEffect(() => {
    initConversation();
  }, [initConversation]);

  // New Chat handler: create a fresh conversation
  const handleNewChat = useCallback(() => {
    setThreadId(null);
    initConversation();
  }, [initConversation]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
        <span>Failed to initialize conversation</span>
        <span className="text-sm text-red-400">{error}</span>
        <button
          onClick={initConversation}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!threadId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <span>Initializing conversation...</span>
      </div>
    );
  }

  // Use Next.js API route as a proxy to the backend
  // The proxy forwards requests to /logistics on the backend
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="logistics_agent"
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
