"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useSessionHistoryContext } from "@/lib/sessionHistoryContext";
import { mapTranscriptToChatMessages } from "@/lib/sessionTranscriptHydration";
import { useCopilotChat, useCopilotChatInternal } from "@copilotkit/react-core";
import { useNewChat, useThreadId, useResumeSession } from "./NoAuthCopilotKit";

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }
  return date.toLocaleString();
}

function scheduleTranscriptHydration(
  setMessages: (messages: unknown[]) => void,
  messages: unknown[],
) {
  // CopilotKit can briefly reset message state when threadId changes.
  // Re-apply hydration on staggered ticks so first-click resume is reliable.
  const delays = [0, 40, 120, 300, 700];
  for (const delay of delays) {
    setTimeout(() => {
      setMessages(messages);
    }, delay);
  }
}

export function SessionHistoryFlyout() {
  const [open, setOpen] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const history = useSessionHistoryContext();
  const currentThreadId = useThreadId();
  const newChat = useNewChat();
  const resumeSession = useResumeSession();
  const { isLoading: isRunning } = useCopilotChat();
  const { setMessages } = useCopilotChatInternal();
  const isRunningRef = useRef(isRunning);

  useEffect(() => {
    isRunningRef.current = isRunning;
  }, [isRunning]);

  const sessions = useMemo(() => history?.sessions ?? [], [history]);

  // In no-auth mode, history context is intentionally disabled.
  if (!history) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="fixed left-4 top-20 z-40 rounded-lg border border-gray-700 bg-gray-900/90 px-3 py-2 text-sm text-gray-200 hover:bg-gray-800"
      >
        {open ? "Hide Sessions" : "Sessions"}
      </button>

      {open ? (
        <aside className="fixed left-4 top-32 z-40 h-[70vh] w-80 overflow-hidden rounded-xl border border-gray-700 bg-gray-900/95 shadow-2xl">
          <div className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
            <h3 className="text-sm font-semibold text-white">Session History</h3>
            <button
              onClick={() => {
                if (isRunning) {
                  return;
                }
                if (newChat) {
                  newChat();
                }
              }}
              disabled={isRunning}
              className="rounded-md bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
            >
              New Chat
            </button>
          </div>

          <div className="h-[calc(70vh-56px)] overflow-y-auto p-2">
            {history.isLoading ? (
              <p className="px-2 py-3 text-sm text-gray-400">Loading sessions...</p>
            ) : sessions.length === 0 ? (
              <p className="px-2 py-3 text-sm text-gray-400">No sessions yet.</p>
            ) : (
              <ul className="space-y-2">
                {sessions.map((session) => {
                  const isActive = session.session_id === currentThreadId;
                  const unavailable = session.availability === "unavailable";
                  const selectSession = async () => {
                    const wasRunning = isRunningRef.current;
                    const payload = await history.selectSession(session.session_id, {
                      blockReason: wasRunning
                        ? "Finish or cancel the active run before switching sessions."
                        : null,
                    });
                    if (!payload) {
                      return;
                    }
                    if (!isRunningRef.current && !unavailable && resumeSession) {
                      resumeSession(session.session_id);
                      const hydratedMessages = mapTranscriptToChatMessages(payload.transcript);
                      if (hydratedMessages.length > 0) {
                        scheduleTranscriptHydration(
                          setMessages as (messages: unknown[]) => void,
                          hydratedMessages as unknown[],
                        );
                      }
                    }
                  };
                  return (
                    <li key={session.session_id}>
                      <div
                        role="button"
                        tabIndex={isRunning ? -1 : 0}
                        aria-disabled={isRunning}
                        onClick={() => {
                          void selectSession();
                        }}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            void selectSession();
                          }
                        }}
                        className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                          isActive
                            ? "border-blue-500 bg-blue-500/10"
                            : "border-gray-700 bg-gray-800/70 hover:bg-gray-800"
                        } ${isRunning ? "cursor-not-allowed opacity-70" : "cursor-pointer"}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="line-clamp-2 text-sm font-medium text-white">{session.title}</span>
                          <span
                            className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                              unavailable
                                ? "bg-amber-500/20 text-amber-300"
                                : "bg-emerald-500/20 text-emerald-300"
                            }`}
                          >
                            {session.availability}
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-gray-400">
                          {formatDateTime(session.display_datetime)}
                        </div>
                        <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setEditingSessionId(session.session_id);
                              setEditingTitle(session.title);
                            }}
                            className="rounded border border-gray-600 px-2 py-0.5 hover:bg-gray-700"
                          >
                            Rename
                          </button>
                          <button
                            type="button"
                            onClick={async (event) => {
                              event.stopPropagation();
                              const confirmed = window.confirm(
                                `Delete session \"${session.title}\" from history?`,
                              );
                              if (!confirmed) {
                                return;
                              }
                              const wasActive = session.session_id === currentThreadId;
                              await history.remove(session.session_id);
                              if (wasActive && newChat) {
                                newChat();
                              }
                            }}
                            className="rounded border border-red-700 px-2 py-0.5 text-red-300 hover:bg-red-900/30"
                          >
                            Delete
                          </button>
                          {history.mutationStatusBySession[session.session_id] ? (
                            <span className="rounded bg-gray-700 px-2 py-0.5">
                              {history.mutationStatusBySession[session.session_id]}
                            </span>
                          ) : null}
                        </div>
                      </div>
                      {editingSessionId === session.session_id ? (
                        <form
                          className="mt-2 flex items-center gap-2"
                          onSubmit={async (event) => {
                            event.preventDefault();
                            await history.rename(session.session_id, editingTitle);
                            setEditingSessionId(null);
                          }}
                        >
                          <input
                            value={editingTitle}
                            onChange={(event) => setEditingTitle(event.target.value)}
                            onClick={(event) => event.stopPropagation()}
                            className="flex-1 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-white"
                          />
                          <button
                            type="submit"
                            className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingSessionId(null)}
                            className="rounded border border-gray-600 px-2 py-1 text-xs text-gray-200 hover:bg-gray-700"
                          >
                            Cancel
                          </button>
                        </form>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}

            {history.error ? <p className="mt-3 text-xs text-red-400">{history.error}</p> : null}
          </div>
        </aside>
      ) : null}
    </>
  );
}
