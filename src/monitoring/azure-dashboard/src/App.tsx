import { useState, useCallback, useMemo } from 'react'
import { useMsal, AuthenticatedTemplate, UnauthenticatedTemplate } from '@azure/msal-react'
import { LogAnalyticsClient } from './lib/logAnalyticsClient'
import { buildSpanTree } from './lib/utils'
import type { ParsedSpan, TreeNode, RecentConversation, DashboardConfig } from './lib/types'
import { Sidebar } from './components/Sidebar'
import { DetailPanel } from './components/DetailPanel'
import { ConfigPanel } from './components/ConfigPanel'
import { LoginButton } from './components/LoginButton'

function App() {
  const { instance } = useMsal()

  // Configuration state
  const [config, setConfig] = useState<DashboardConfig>({
    workspaceId: import.meta.env.VITE_LOG_ANALYTICS_WORKSPACE_ID || '',
    hoursToQuery: 168, // 7 days
    maxResults: 50,
  })
  const [showConfig, setShowConfig] = useState(!config.workspaceId)

  // Data state
  const [conversationId, setConversationId] = useState('')
  const [spans, setSpans] = useState<ParsedSpan[]>([])
  const [recentConversations, setRecentConversations] = useState<RecentConversation[]>([])
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [diagnostics, setDiagnostics] = useState<{
    hasDependencies: boolean
    hasTraces: boolean
    samplePropertyKeys: string[]
    totalDependencies: number
    dependenciesWithConvId: number
  } | null>(null)

  // Build tree from spans
  const tree = useMemo(() => {
    if (!conversationId || spans.length === 0) return null
    return buildSpanTree(conversationId, spans)
  }, [conversationId, spans])

  // Create Log Analytics client
  const client = useMemo(() => {
    if (!config.workspaceId) return null
    return new LogAnalyticsClient(instance, config.workspaceId)
  }, [instance, config.workspaceId])

  // Run diagnostics
  const runDiagnostics = useCallback(async () => {
    if (!client) return
    try {
      setLoading(true)
      setError(null)
      const diag = await client.runDiagnostics()
      setDiagnostics(diag)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Diagnostics failed')
    } finally {
      setLoading(false)
    }
  }, [client])

  // Load recent conversations
  const loadRecentConversations = useCallback(async () => {
    if (!client) return
    
    try {
      setLoading(true)
      setError(null)
      const recent = await client.getRecentConversations(config.hoursToQuery, 20)
      setRecentConversations(recent)
      
      // If no conversations found, run diagnostics automatically
      if (recent.length === 0) {
        const diag = await client.runDiagnostics()
        setDiagnostics(diag)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recent conversations')
    } finally {
      setLoading(false)
    }
  }, [client, config.hoursToQuery])

  // Load conversation spans
  const loadConversation = useCallback(async (convId: string) => {
    if (!client || !convId) return

    try {
      setLoading(true)
      setError(null)
      setConversationId(convId)
      setSelectedNode(null)
      
      const conversationSpans = await client.getConversationSpans(convId, config.hoursToQuery * 7) // Look back further for specific conversation
      setSpans(conversationSpans)
      
      if (conversationSpans.length === 0) {
        setError(`No traces found for conversation: ${convId}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation')
      setSpans([])
    } finally {
      setLoading(false)
    }
  }, [client, config.hoursToQuery])

  // Handle node selection
  const handleNodeSelect = useCallback((node: TreeNode) => {
    setSelectedNode(node)
  }, [])

  // Handle config save
  const handleConfigSave = useCallback((newConfig: DashboardConfig) => {
    setConfig(newConfig)
    setShowConfig(false)
    // Reset state when config changes
    setSpans([])
    setRecentConversations([])
    setSelectedNode(null)
    setConversationId('')
  }, [])

  return (
    <div className="flex h-screen">
      {/* Unauthenticated state */}
      <UnauthenticatedTemplate>
        <div className="flex-1 flex items-center justify-center bg-vscode-bg">
          <div className="text-center p-8">
            <h1 className="text-2xl font-bold text-amber-500 mb-4">🤖 Agent Trace Dashboard</h1>
            <p className="text-vscode-muted mb-6">
              Sign in with your Azure account to query Application Insights traces
            </p>
            <LoginButton />
          </div>
        </div>
      </UnauthenticatedTemplate>

      {/* Authenticated state */}
      <AuthenticatedTemplate>
        {showConfig ? (
          <ConfigPanel
            config={config}
            onSave={handleConfigSave}
            onCancel={() => config.workspaceId && setShowConfig(false)}
          />
        ) : (
          <>
            {/* Sidebar */}
            <Sidebar
              tree={tree}
              selectedNode={selectedNode}
              conversationId={conversationId}
              recentConversations={recentConversations}
              loading={loading}
              error={error}
              diagnostics={diagnostics}
              onSearch={loadConversation}
              onLoadRecent={loadRecentConversations}
              onSelectNode={handleNodeSelect}
              onShowConfig={() => setShowConfig(true)}
              onRunDiagnostics={runDiagnostics}
            />

            {/* Detail Panel */}
            <DetailPanel
              node={selectedNode}
              spans={spans}
            />
          </>
        )}
      </AuthenticatedTemplate>
    </div>
  )
}

export default App
