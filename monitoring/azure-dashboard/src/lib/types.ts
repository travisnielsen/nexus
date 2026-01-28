/**
 * Type definitions for the trace dashboard
 */

// Raw span data from Application Insights / Log Analytics
export interface RawSpan {
  timestamp: string
  id: string
  operation_Id: string
  operation_ParentId?: string
  name: string
  duration: number
  success: boolean
  customDimensions: Record<string, string | number | undefined>
}

// Parsed span with extracted gen_ai attributes
export interface ParsedSpan {
  id: string
  traceId: string
  parentId?: string
  name: string
  operation?: string
  model?: string
  agentName?: string
  conversationId?: string
  toolName?: string
  toolArgs?: string
  toolResult?: string
  inputMessages?: Message[]
  outputMessages?: Message[]
  startTime: number
  duration: string
  durationMs: number
  inputTokens?: number
  outputTokens?: number
  success: boolean
  attributes: Record<string, string | number | undefined>
}

// Message structure from gen_ai.input.messages / gen_ai.output.messages
export interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool'
  parts?: MessagePart[]
}

export interface MessagePart {
  type: 'text' | 'tool_call' | 'tool_call_response'
  content?: string
  name?: string
  arguments?: Record<string, unknown>
  response?: string
}

// Tree node for the sidebar
export interface TreeNode {
  id: string
  type: 'conversation' | 'run' | 'run-step' | 'tool' | 'message'
  label: string
  duration?: string
  tokens?: number
  children?: TreeNode[]
  data?: ParsedSpan | ParsedSpan[]
  expanded?: boolean
}

// Recent conversation entry
export interface RecentConversation {
  id: string
  time: Date
  traceCount: number
}

// Log Analytics query result
export interface QueryResult {
  tables: Array<{
    name: string
    columns: Array<{ name: string; type: string }>
    rows: Array<Array<string | number | boolean | null>>
  }>
}

// Dashboard configuration
export interface DashboardConfig {
  workspaceId: string
  resourceGroup?: string
  subscriptionId?: string
  hoursToQuery: number
  maxResults: number
}

// Tab types for detail panel
export type DetailTab = 'io' | 'metadata'

// Node selection state
export interface SelectionState {
  node: TreeNode | null
  span: ParsedSpan | null
  spans: ParsedSpan[]
}
