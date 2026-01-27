"use client";

import { useMemo, createContext, useContext } from "react";
import { CopilotKit } from "@copilotkit/react-core";

// Context to expose threadId to child components
export const ThreadIdContext = createContext<string | null>(null);

// Hook to access the threadId from child components
export function useThreadId(): string | null {
  return useContext(ThreadIdContext);
}

interface NoAuthCopilotKitProps {
  children: React.ReactNode;
}

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

/**
 * CopilotKit wrapper without authentication.
 * Use this when AUTH_ENABLED=false to bypass Azure AD authentication.
 * Uses Next.js API route as a proxy to forward requests to the backend.
 * 
 * Provides a stable threadId for conversation continuity across messages.
 * This enables the backend to chain Azure response_ids for multi-turn conversations.
 */
export function NoAuthCopilotKit({ children }: NoAuthCopilotKitProps) {
  const threadId = useStableThreadId();
  
  // Use Next.js API route as a proxy to the backend
  // The proxy forwards requests to /logistics on the backend
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="logistics_agent"
      threadId={threadId}
    >
      <ThreadIdContext.Provider value={threadId}>
        {children}
      </ThreadIdContext.Provider>
    </CopilotKit>
  );
}
