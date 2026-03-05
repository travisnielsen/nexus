import { useState, useRef, useEffect } from 'react'
import type { TreeNode, RecentConversation } from '../lib/types'
import { getRelativeTime } from '../lib/utils'
import { LogoutButton } from './LoginButton'
import { TreeView } from './TreeView'

interface DiagnosticsData {
  hasDependencies: boolean
  hasTraces: boolean
  samplePropertyKeys: string[]
  totalDependencies: number
  dependenciesWithConvId: number
}

interface SidebarProps {
  tree: TreeNode | null
  selectedNode: TreeNode | null
  conversationId: string
  recentConversations: RecentConversation[]
  loading: boolean
  error: string | null
  diagnostics?: DiagnosticsData | null
  onSearch: (conversationId: string) => void
  onLoadRecent: () => void
  onSelectNode: (node: TreeNode) => void
  onShowConfig: () => void
  onRunDiagnostics?: () => void
}

export function Sidebar({
  tree,
  selectedNode,
  conversationId,
  recentConversations,
  loading,
  error,
  diagnostics,
  onSearch,
  onLoadRecent,
  onSelectNode,
  onShowConfig,
  onRunDiagnostics,
}: SidebarProps) {
  const [searchValue, setSearchValue] = useState(conversationId)
  const [showRecent, setShowRecent] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Update search value when conversationId changes
  useEffect(() => {
    setSearchValue(conversationId)
  }, [conversationId])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowRecent(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchValue.trim()) {
      onSearch(searchValue.trim())
    }
  }

  const handleToggleRecent = () => {
    if (!showRecent) {
      onLoadRecent()
    }
    setShowRecent(!showRecent)
  }

  const handleSelectRecent = (convId: string) => {
    setSearchValue(convId)
    setShowRecent(false)
    onSearch(convId)
  }

  return (
    <div className="w-[450px] border-r border-vscode-border flex flex-col h-screen bg-vscode-bg">
      {/* Header */}
      <div className="p-4 border-b border-vscode-border bg-vscode-sidebar">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-amber-500 text-lg font-semibold">🤖 Agent Trace Dashboard</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={onShowConfig}
              className="p-1 text-vscode-muted hover:text-white"
              title="Settings"
            >
              ⚙️
            </button>
            <LogoutButton />
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative" ref={containerRef}>
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Enter Conversation ID..."
              className="flex-1 px-3 py-2 bg-vscode-bg border border-vscode-border rounded text-vscode-text text-sm placeholder-vscode-muted focus:outline-none focus:border-vscode-accent"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-vscode-accent hover:bg-blue-600 disabled:bg-gray-600 text-white rounded text-sm font-medium transition-colors"
            >
              Load
            </button>
            <button
              type="button"
              onClick={handleToggleRecent}
              className="px-3 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded text-sm transition-colors"
              title="Recent conversations"
            >
              ▾
            </button>
          </form>

          {/* Recent Dropdown */}
          {showRecent && (
            <div className="absolute top-full right-0 mt-1 w-96 max-h-96 overflow-y-auto bg-vscode-bg border border-vscode-border rounded-lg shadow-xl z-50">
              {loading ? (
                <div className="p-4 text-center text-vscode-muted">Loading recent conversations...</div>
              ) : recentConversations.length === 0 ? (
                <div className="p-4 text-center text-vscode-muted">No recent conversations found</div>
              ) : (
                recentConversations.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => handleSelectRecent(conv.id)}
                    className="p-3 border-b border-vscode-border last:border-b-0 hover:bg-vscode-hover cursor-pointer"
                  >
                    <div className="font-mono text-xs text-blue-400">{conv.id}</div>
                    <div className="flex gap-3 text-xs text-vscode-muted mt-1">
                      <span>{conv.time.toLocaleString()}</span>
                      <span>{getRelativeTime(conv.time)}</span>
                      <span>{conv.traceCount} spans</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tree View */}
      <div className="flex-1 overflow-y-auto">
        {loading && !tree ? (
          <div className="p-8 text-center text-vscode-muted">Loading traces...</div>
        ) : error ? (
          <div className="m-4 p-3 bg-red-900/30 border border-red-600 rounded text-red-300 text-sm">
            {error}
          </div>
        ) : tree ? (
          <TreeView
            tree={tree}
            selectedNode={selectedNode}
            onSelectNode={onSelectNode}
          />
        ) : diagnostics ? (
          <div className="p-4">
            <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-amber-500 mb-3">🔍 Workspace Diagnostics</h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-vscode-muted">AppDependencies table:</span>
                  <span className={diagnostics.hasDependencies ? 'text-green-400' : 'text-red-400'}>
                    {diagnostics.hasDependencies ? `✓ ${diagnostics.totalDependencies} rows` : '✗ No data'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vscode-muted">AppTraces table:</span>
                  <span className={diagnostics.hasTraces ? 'text-green-400' : 'text-red-400'}>
                    {diagnostics.hasTraces ? '✓ Has data' : '✗ No data'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vscode-muted">Rows with gen_ai/conversation:</span>
                  <span className={diagnostics.dependenciesWithConvId > 0 ? 'text-green-400' : 'text-yellow-400'}>
                    {diagnostics.dependenciesWithConvId}
                  </span>
                </div>
                {diagnostics.samplePropertyKeys.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-vscode-border">
                    <span className="text-vscode-muted block mb-1">Sample property keys:</span>
                    <div className="flex flex-wrap gap-1">
                      {diagnostics.samplePropertyKeys.slice(0, 10).map(key => (
                        <span key={key} className="px-1.5 py-0.5 bg-vscode-bg rounded text-[10px] font-mono">
                          {key}
                        </span>
                      ))}
                      {diagnostics.samplePropertyKeys.length > 10 && (
                        <span className="text-vscode-muted">+{diagnostics.samplePropertyKeys.length - 10} more</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
              {diagnostics.dependenciesWithConvId === 0 && diagnostics.hasDependencies && (
                <p className="mt-3 text-xs text-yellow-400">
                  ⚠️ No conversation IDs found. Make sure your backend is sending telemetry with 
                  <code className="mx-1 px-1 bg-vscode-bg rounded">gen_ai_conversation_id</code> 
                  in Properties.
                </p>
              )}
            </div>
            {onRunDiagnostics && (
              <button
                onClick={onRunDiagnostics}
                className="mt-3 w-full px-3 py-2 text-xs bg-gray-700 hover:bg-gray-600 rounded transition-colors"
              >
                🔄 Re-run Diagnostics
              </button>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-vscode-muted">
            <h2 className="text-lg mb-2">Enter a Conversation ID</h2>
            <p className="text-sm mb-4">Paste a conversation ID to view the trace tree</p>
            <p className="text-xs">Or click the ▾ button to load recent conversations</p>
          </div>
        )}
      </div>
    </div>
  )
}
