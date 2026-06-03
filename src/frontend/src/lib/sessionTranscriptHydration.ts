import {
  Message,
  MessageStatusCode,
  Role,
  TextMessage,
} from "@copilotkit/runtime-client-gql";

// Marker prefix for assistant messages that should be rendered as a hydrated
// tool-call card rather than as Markdown text. Format:
//   __HYDRATED_TOOL__:<toolName>:<jsonPayload>
// where <jsonPayload> is { args, result } (either may be null/undefined).
export const HYDRATED_TOOL_MARKER = "__HYDRATED_TOOL__";

const SUCCESS_STATUS = { code: MessageStatusCode.Success } as const;

// Tools that should render a hydrated card/info-bar on replay.
const RENDERABLE_TOOLS = new Set<string>([
  "filter_flights",
  "reset_filters",
  "analyze_flights",
  "get_historical_payload",
  "get_predicted_payload",
  "get_recommendations",
]);

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function parseMaybeJson(value: unknown): unknown {
  if (typeof value !== "string") return value;
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
}

export interface HydratedToolPayload {
  toolName: string;
  args: unknown;
  result: unknown;
}

export function parseHydratedToolMarker(content: string): HydratedToolPayload | null {
  if (!content.startsWith(`${HYDRATED_TOOL_MARKER}:`)) {
    return null;
  }
  const rest = content.slice(HYDRATED_TOOL_MARKER.length + 1);
  const sep = rest.indexOf(":");
  if (sep === -1) return null;
  const toolName = rest.slice(0, sep);
  const json = rest.slice(sep + 1);
  let parsed: { args?: unknown; result?: unknown } = {};
  try {
    parsed = JSON.parse(json);
  } catch {
    parsed = { result: json };
  }
  return { toolName, args: parsed.args, result: parsed.result };
}

/**
 * Convert backend-normalized Foundry transcript items into a flat list of
 * CopilotKit TextMessages for replay. Tool calls for known renderable tools
 * are emitted as assistant messages with a marker the chat renderer detects
 * and replaces with the matching component.
 */
export function mapTranscriptToChatMessages(
  transcript: Array<Record<string, unknown>>,
): Message[] {
  const messages: Message[] = [];
  const callIdToName = new Map<string, string>();
  const callIdToArgs = new Map<string, unknown>();

  // First pass: collect call_id -> { name, args } from function_call items
  // (they may appear after their corresponding outputs in the transcript).
  for (const item of transcript) {
    const raw = asRecord(item.raw);
    const rawType = typeof raw.type === "string" ? raw.type.toLowerCase() : "";
    if (rawType !== "function_call" && rawType !== "tool_call") continue;
    const name =
      (typeof raw.name === "string" && raw.name) ||
      (typeof raw.tool_name === "string" && raw.tool_name) ||
      "";
    const callId =
      (typeof raw.call_id === "string" && raw.call_id) ||
      (typeof raw.tool_call_id === "string" && raw.tool_call_id) ||
      "";
    if (!name || !callId) continue;
    callIdToName.set(callId, name);
    callIdToArgs.set(callId, parseMaybeJson(raw.arguments));
  }

  let synthId = 0;
  const nextId = (prefix: string) => `${prefix}-${synthId++}`;

  // Dedup plain-text message items by (role, normalized_text). The Foundry
  // transcript can contain repeat history items appended on subsequent turns
  // (AG-UI runtime re-sends the full conversation each turn). The first
  // occurrence is the original (often paired with tool calls); later bare
  // copies are redundant and would render as duplicates in the chat.
  const seenMessageKeys = new Set<string>();

  for (const item of transcript) {
    const role = typeof item.role === "string" ? item.role : "";
    const text = typeof item.text === "string" ? item.text : "";
    const raw = asRecord(item.raw);
    const rawType = typeof raw.type === "string" ? raw.type.toLowerCase() : "";
    const itemId =
      (typeof item.id === "string" && item.id.length > 0 && item.id) ||
      (typeof raw.id === "string" && (raw.id as string).length > 0 && (raw.id as string)) ||
      undefined;

    if (rawType === "function_call" || rawType === "tool_call") {
      continue;
    }

    if (rawType === "function_call_output" || rawType === "tool_result" || role === "tool") {
      const callId =
        (typeof raw.call_id === "string" && raw.call_id) ||
        (typeof raw.tool_call_id === "string" && raw.tool_call_id) ||
        "";
      const toolName =
        (typeof raw.name === "string" && raw.name) ||
        (typeof raw.tool_name === "string" && raw.tool_name) ||
        (callId ? (callIdToName.get(callId) ?? "") : "");

      if (!toolName || !RENDERABLE_TOOLS.has(toolName)) {
        continue;
      }

      const args = callId ? callIdToArgs.get(callId) : undefined;
      const result =
        raw.output !== undefined ? parseMaybeJson(raw.output) : text || undefined;

      const payloadJson = JSON.stringify({ args, result });
      messages.push(
        new TextMessage({
          id: itemId ?? nextId("tool-result"),
          role: Role.Assistant,
          content: `${HYDRATED_TOOL_MARKER}:${toolName}:${payloadJson}`,
          status: SUCCESS_STATUS,
        }),
      );
      continue;
    }

    if (rawType === "reasoning") continue;

    const trimmed = text.trim();
    if (!trimmed) continue;

    const dedupKey = `${role || "assistant"}::${trimmed}`;
    if (seenMessageKeys.has(dedupKey)) continue;
    seenMessageKeys.add(dedupKey);

    messages.push(
      new TextMessage({
        id: itemId ?? nextId("msg"),
        role: role === "user" ? Role.User : Role.Assistant,
        content: trimmed,
        status: SUCCESS_STATUS,
      }),
    );
  }

  return messages;
}
