import { IPublicClientApplication } from '@azure/msal-browser'
import { logAnalyticsScopes } from './msalConfig'
import type { QueryResult, ParsedSpan, RecentConversation } from './types'

/**
 * Log Analytics API client for querying Application Insights data
 */

const LOG_ANALYTICS_API = 'https://api.loganalytics.io/v1'

export class LogAnalyticsClient {
  private msalInstance: IPublicClientApplication
  private workspaceId: string

  constructor(msalInstance: IPublicClientApplication, workspaceId: string) {
    this.msalInstance = msalInstance
    this.workspaceId = workspaceId
  }

  /**
   * Get an access token for the Log Analytics API
   */
  private async getAccessToken(): Promise<string> {
    const accounts = this.msalInstance.getAllAccounts()
    if (accounts.length === 0) {
      throw new Error('No authenticated accounts. Please sign in.')
    }

    try {
      const response = await this.msalInstance.acquireTokenSilent({
        ...logAnalyticsScopes,
        account: accounts[0],
      })
      return response.accessToken
    } catch {
      // If silent token acquisition fails, redirect to login
      // This will navigate away from the page and return after authentication
      await this.msalInstance.acquireTokenRedirect(logAnalyticsScopes)
      // This line won't be reached as redirect navigates away
      throw new Error('Redirecting to login...')
    }
  }

  /**
   * Execute a KQL query against the Log Analytics workspace
   */
  async query(kql: string): Promise<QueryResult> {
    const token = await this.getAccessToken()
    
    const response = await fetch(
      `${LOG_ANALYTICS_API}/workspaces/${this.workspaceId}/query`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: kql }),
      }
    )

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Log Analytics query failed: ${response.status} - ${error}`)
    }

    return response.json()
  }

  /**
   * Run diagnostic queries to check what data exists in the workspace
   */
  async runDiagnostics(): Promise<{
    hasDependencies: boolean
    hasTraces: boolean
    samplePropertyKeys: string[]
    totalDependencies: number
    dependenciesWithConvId: number
  }> {
    // Check if AppDependencies has data
    const countQuery = `
      AppDependencies
      | where TimeGenerated > ago(7d)
      | summarize Total = count()
    `
    
    let totalDependencies = 0
    let hasDependencies = false
    try {
      const countResult = await this.query(countQuery)
      if (countResult.tables?.[0]?.rows?.[0]) {
        totalDependencies = countResult.tables[0].rows[0][0] as number
        hasDependencies = totalDependencies > 0
      }
    } catch (e) {
      console.error('Count query failed:', e)
    }

    // Check for gen_ai conversation IDs
    let dependenciesWithConvId = 0
    const convIdQuery = `
      AppDependencies
      | where TimeGenerated > ago(7d)
      | where Properties has "gen_ai" or Properties has "conversation"
      | summarize Total = count()
    `
    try {
      const convResult = await this.query(convIdQuery)
      if (convResult.tables?.[0]?.rows?.[0]) {
        dependenciesWithConvId = convResult.tables[0].rows[0][0] as number
      }
    } catch (e) {
      console.error('Conv ID query failed:', e)
    }

    // Get sample property keys
    let samplePropertyKeys: string[] = []
    const propsQuery = `
      AppDependencies
      | where TimeGenerated > ago(7d)
      | take 1
      | project Properties
    `
    try {
      const propsResult = await this.query(propsQuery)
      if (propsResult.tables?.[0]?.rows?.[0]) {
        const props = propsResult.tables[0].rows[0][0]
        if (typeof props === 'string') {
          try {
            const parsed = JSON.parse(props)
            samplePropertyKeys = Object.keys(parsed)
          } catch { /* ignore */ }
        } else if (typeof props === 'object' && props !== null) {
          samplePropertyKeys = Object.keys(props)
        }
      }
    } catch (e) {
      console.error('Props query failed:', e)
    }

    // Check AppTraces
    let hasTraces = false
    try {
      const tracesQuery = `AppTraces | where TimeGenerated > ago(7d) | summarize count()`
      const tracesResult = await this.query(tracesQuery)
      if (tracesResult.tables?.[0]?.rows?.[0]) {
        hasTraces = (tracesResult.tables[0].rows[0][0] as number) > 0
      }
    } catch (e) {
      console.error('Traces query failed:', e)
    }

    return {
      hasDependencies,
      hasTraces,
      samplePropertyKeys,
      totalDependencies,
      dependenciesWithConvId,
    }
  }

  /**
   * Get recent conversations (distinct conversation IDs)
   */
  async getRecentConversations(hours: number = 24, limit: number = 20): Promise<RecentConversation[]> {
    // Try multiple property name variations - the telemetry may use different formats
    const kql = `
      AppDependencies
      | where TimeGenerated > ago(${hours}h)
      | extend convId = coalesce(
          tostring(Properties.gen_ai_conversation_id),
          tostring(Properties["gen_ai.conversation.id"]),
          tostring(Properties["gen_ai.conversation_id"])
        )
      | where isnotempty(convId)
      | summarize 
          FirstSeen = min(TimeGenerated),
          TraceCount = count()
        by conversationId = convId
      | order by FirstSeen desc
      | take ${limit}
    `

    const result = await this.query(kql)
    
    if (!result.tables || result.tables.length === 0) {
      return []
    }

    const table = result.tables[0]
    const convIdIdx = table.columns.findIndex(c => c.name === 'conversationId')
    const firstSeenIdx = table.columns.findIndex(c => c.name === 'FirstSeen')
    const traceCountIdx = table.columns.findIndex(c => c.name === 'TraceCount')

    return table.rows.map(row => ({
      id: row[convIdIdx] as string,
      time: new Date(row[firstSeenIdx] as string),
      traceCount: row[traceCountIdx] as number,
    }))
  }

  /**
   * Get all spans for a specific conversation ID
   */
  async getConversationSpans(conversationId: string, hours: number = 168): Promise<ParsedSpan[]> {
    // First, get OperationIds that have this conversation ID
    // Then get ALL spans with those OperationIds (to include tool executions, etc.)
    // Note: Azure Monitor may store duplicate spans, so we deduplicate by spanId using summarize/arg_min
    const kql = `
      let convId = "${conversationId}";
      let timeRange = ${hours}h;
      
      // Find all OperationIds associated with this conversation
      let opIds = AppDependencies
      | where TimeGenerated > ago(timeRange)
      | where Properties.gen_ai_conversation_id == convId
         or Properties["gen_ai.conversation.id"] == convId
      | distinct OperationId;
      
      // Get all AppDependencies with those OperationIds, deduplicated by spanId
      AppDependencies
      | where TimeGenerated > ago(timeRange)
      | where OperationId in (opIds)
      | extend 
          spanId = Id,
          traceId = OperationId,
          parentId = ParentId,
          spanName = Name,
          durationMs = DurationMs,
          isSuccess = Success,
          dims = Properties
      | summarize arg_min(TimeGenerated, *) by spanId
      | project TimeGenerated, spanId, traceId, parentId, spanName, durationMs, isSuccess, dims
      | order by TimeGenerated asc
    `

    console.log('Query:', kql)
    const result = await this.query(kql)
    console.log('Result columns:', result.tables?.[0]?.columns)
    console.log('Result rows count:', result.tables?.[0]?.rows?.length)
    console.log('First row:', result.tables?.[0]?.rows?.[0])
    
    if (!result.tables || result.tables.length === 0) {
      return []
    }

    return this.parseSpans(result)
  }

  /**
   * Parse query results into ParsedSpan objects
   */
  private parseSpans(result: QueryResult): ParsedSpan[] {
    const table = result.tables[0]
    const columns = table.columns.map(c => c.name)
    
    return table.rows.map(row => {
      const rowObj: Record<string, unknown> = {}
      columns.forEach((col, idx) => {
        rowObj[col] = row[idx]
      })

      // Parse Properties/customDimensions if it's a string
      let dims: Record<string, string | number | undefined> = {}
      if (rowObj.dims) {
        if (typeof rowObj.dims === 'string') {
          try {
            dims = JSON.parse(rowObj.dims)
          } catch {
            dims = {}
          }
        } else {
          dims = rowObj.dims as Record<string, string | number | undefined>
        }
      }

      // Handle both TimeGenerated (workspace-based) and timestamp (classic)
      const timeField = rowObj.TimeGenerated || rowObj.timestamp
      const startTime = new Date(timeField as string).getTime()
      const durationMs = rowObj.durationMs as number

      // Parse input/output messages if present
      let inputMessages, outputMessages
      try {
        if (dims['gen_ai.input.messages']) {
          inputMessages = JSON.parse(dims['gen_ai.input.messages'] as string)
        }
        if (dims['gen_ai.output.messages']) {
          outputMessages = JSON.parse(dims['gen_ai.output.messages'] as string)
        }
      } catch {
        // Ignore parse errors
      }

      return {
        id: rowObj.spanId as string,
        traceId: rowObj.traceId as string,
        parentId: rowObj.parentId as string | undefined,
        name: rowObj.spanName as string,
        operation: dims['gen_ai.operation.name'] as string | undefined,
        model: (dims['gen_ai.request.model'] || dims['gen_ai.response.model']) as string | undefined,
        agentName: dims['gen_ai.agent.name'] as string | undefined,
        conversationId: (dims['gen_ai_conversation_id'] || dims['gen_ai.conversation.id']) as string | undefined,
        toolName: dims['gen_ai.tool.name'] as string | undefined,
        toolArgs: dims['gen_ai.tool.call.arguments'] as string | undefined,
        toolResult: dims['gen_ai.tool.call.result'] as string | undefined,
        inputMessages,
        outputMessages,
        startTime,
        duration: formatDuration(durationMs),
        durationMs,
        // Parse token counts as integers - they come as strings from Application Insights
        inputTokens: parseInt(String(dims['gen_ai.usage.input_tokens'] || '0'), 10) || 0,
        outputTokens: parseInt(String(dims['gen_ai.usage.output_tokens'] || '0'), 10) || 0,
        success: rowObj.isSuccess as boolean,
        attributes: dims,
      }
    })
  }
}

/**
 * Format milliseconds into a human-readable duration
 */
function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}
