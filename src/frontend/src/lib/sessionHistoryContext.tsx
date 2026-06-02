"use client";

import { createContext, useContext } from "react";

import type { SessionHistoryState } from "./useSessionHistory";

export const SessionHistoryContext = createContext<SessionHistoryState | null>(null);

export function useSessionHistoryContext(): SessionHistoryState | null {
  return useContext(SessionHistoryContext);
}
