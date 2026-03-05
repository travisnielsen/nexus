import type { ParsedSpan, TreeNode } from './types'

/**
 * Build a hierarchical tree structure from flat span data
 */
export function buildSpanTree(conversationId: string, spans: ParsedSpan[]): TreeNode {
  // Group spans by trace ID (each trace = one "run")
  const traceMap = new Map<string, ParsedSpan[]>()
  for (const span of spans) {
    const existing = traceMap.get(span.traceId) || []
    existing.push(span)
    traceMap.set(span.traceId, existing)
  }

  // Sort traces by start time
  const sortedTraceIds = Array.from(traceMap.keys()).sort((a, b) => {
    const aStart = Math.min(...(traceMap.get(a) || []).map(s => s.startTime))
    const bStart = Math.min(...(traceMap.get(b) || []).map(s => s.startTime))
    return aStart - bStart
  })

  // Build run nodes
  const runNodes: TreeNode[] = sortedTraceIds.map(traceId => {
    const traceSpans = traceMap.get(traceId) || []
    const invokeSpan = traceSpans.find(s => s.name.includes('invoke_agent'))
    const chatSpans = traceSpans.filter(s => s.operation === 'chat').sort((a, b) => a.startTime - b.startTime)
    const toolSpans = traceSpans.filter(s => s.operation === 'execute_tool').sort((a, b) => a.startTime - b.startTime)

    const totalTokens = chatSpans.reduce(
      (sum, s) => sum + (s.inputTokens || 0) + (s.outputTokens || 0),
      0
    )

    // Track which tool spans have been assigned to a step (avoid duplicates)
    const usedToolSpanIds = new Set<string>()

    // Build run step nodes from chat spans
    const stepNodes: TreeNode[] = chatSpans.map((chat, idx) => {
      // Extract tool call names from this chat's output
      const toolCallNames: string[] = []
      if (chat.outputMessages) {
        for (const msg of chat.outputMessages) {
          if (msg.parts) {
            for (const part of msg.parts) {
              if (part.type === 'tool_call' && part.name) {
                toolCallNames.push(part.name)
              }
            }
          }
        }
      }

      const hasToolCalls = toolCallNames.length > 0
      const stepType = hasToolCalls ? 'tool_calls' : 'message_creation'
      const tokens = (chat.inputTokens || 0) + (chat.outputTokens || 0)

      // Find tool spans that match:
      // 1. Tool name matches one of the tool calls in this chat
      // 2. Haven't been used by a previous step
      // 3. Started after or around the time this chat started
      const chatToolSpans = toolSpans.filter(t => {
        if (!t.toolName || !toolCallNames.includes(t.toolName)) return false
        if (usedToolSpanIds.has(t.id)) return false
        // Tool should start around the same time or after the chat span
        // (allow 100ms tolerance for timing issues)
        return t.startTime >= chat.startTime - 100
      })

      // Mark these tool spans as used
      for (const t of chatToolSpans) {
        usedToolSpanIds.add(t.id)
      }

      const toolNodes: TreeNode[] = chatToolSpans.map(tool => ({
        id: `tool-${tool.id}`,
        type: 'tool' as const,
        label: `Tool ${tool.toolName}`,
        duration: tool.duration,
        data: tool,
        expanded: false,
      }))

      return {
        id: `step-${traceId}-${idx}`,
        type: 'run-step' as const,
        label: `Run step ${stepType}`,
        duration: chat.duration,
        tokens,
        children: toolNodes.length > 0 ? toolNodes : undefined,
        data: chat,
        expanded: true,
      }
    })

    return {
      id: `run-${traceId}`,
      type: 'run' as const,
      label: `run_${traceId.substring(0, 12)}`,
      duration: invokeSpan?.duration || formatMaxDuration(traceSpans),
      tokens: totalTokens,
      children: stepNodes,
      data: traceSpans,
      expanded: true,
    }
  })

  // Calculate conversation totals
  const totalConversationTokens = runNodes.reduce((sum, run) => sum + (run.tokens || 0), 0)
  const totalConversationDurationMs = sortedTraceIds.reduce((sum, traceId) => {
    const traceSpans = traceMap.get(traceId) || []
    const maxMs = Math.max(...traceSpans.map(s => s.durationMs))
    return sum + maxMs
  }, 0)

  // Root conversation node
  return {
    id: `conv-${conversationId}`,
    type: 'conversation',
    label: `Conversation ${conversationId.substring(0, 8)}...`,
    duration: formatDurationMs(totalConversationDurationMs),
    tokens: totalConversationTokens,
    children: runNodes,
    expanded: true,
  }
}

function formatMaxDuration(spans: ParsedSpan[]): string {
  const maxMs = Math.max(...spans.map(s => s.durationMs))
  if (maxMs < 1) return `${(maxMs * 1000).toFixed(0)}µs`
  if (maxMs < 1000) return `${maxMs.toFixed(0)}ms`
  return `${(maxMs / 1000).toFixed(1)}s`
}

function formatDurationMs(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/**
 * Format duration for display
 */
export function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/**
 * Get relative time string (e.g., "5m ago", "2h ago")
 */
export function getRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

/**
 * Escape HTML entities
 */
export function escapeHtml(str: string | undefined | null): string {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/**
 * Format JSON for display
 */
export function formatJson(obj: unknown): string {
  if (typeof obj === 'string') return escapeHtml(obj)
  try {
    return escapeHtml(JSON.stringify(obj, null, 2))
  } catch {
    return escapeHtml(String(obj))
  }
}

/**
 * Get text content from a message
 */
export function getTextContent(msg: { parts?: Array<{ type: string; content?: string }> }): string {
  for (const part of msg.parts || []) {
    if (part.type === 'text') return part.content || ''
  }
  return ''
}
