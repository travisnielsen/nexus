import { useState } from 'react'
import type { DashboardConfig } from '../lib/types'

interface ConfigPanelProps {
  config: DashboardConfig
  onSave: (config: DashboardConfig) => void
  onCancel: () => void
}

export function ConfigPanel({ config, onSave, onCancel }: ConfigPanelProps) {
  const [workspaceId, setWorkspaceId] = useState(config.workspaceId)
  const [hoursToQuery, setHoursToQuery] = useState(config.hoursToQuery)
  const [maxResults, setMaxResults] = useState(config.maxResults)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      workspaceId,
      hoursToQuery,
      maxResults,
    })
  }

  const isValid = workspaceId.trim().length > 0

  return (
    <div className="flex-1 flex items-center justify-center bg-vscode-bg">
      <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-8 max-w-lg w-full mx-4">
        <h2 className="text-xl font-bold text-amber-500 mb-6">⚙️ Configuration</h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Workspace ID */}
          <div>
            <label className="block text-sm font-medium text-vscode-text mb-2">
              Log Analytics Workspace ID *
            </label>
            <input
              type="text"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full px-3 py-2 bg-vscode-bg border border-vscode-border rounded text-vscode-text placeholder-vscode-muted focus:outline-none focus:border-vscode-accent"
            />
            <p className="mt-1 text-xs text-vscode-muted">
              Find this in Azure Portal → Log Analytics workspace → Properties → Workspace ID
            </p>
          </div>

          {/* Hours to Query */}
          <div>
            <label className="block text-sm font-medium text-vscode-text mb-2">
              Default Time Range (hours)
            </label>
            <input
              type="number"
              value={hoursToQuery}
              onChange={(e) => setHoursToQuery(parseInt(e.target.value) || 24)}
              min={1}
              max={168}
              className="w-32 px-3 py-2 bg-vscode-bg border border-vscode-border rounded text-vscode-text focus:outline-none focus:border-vscode-accent"
            />
          </div>

          {/* Max Results */}
          <div>
            <label className="block text-sm font-medium text-vscode-text mb-2">
              Max Results per Query
            </label>
            <input
              type="number"
              value={maxResults}
              onChange={(e) => setMaxResults(parseInt(e.target.value) || 50)}
              min={10}
              max={1000}
              className="w-32 px-3 py-2 bg-vscode-bg border border-vscode-border rounded text-vscode-text focus:outline-none focus:border-vscode-accent"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={!isValid}
              className="px-4 py-2 bg-vscode-accent hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded font-medium transition-colors"
            >
              Save Configuration
            </button>
            {config.workspaceId && (
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded font-medium transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </form>

        {/* Help Section */}
        <div className="mt-8 pt-6 border-t border-vscode-border">
          <h3 className="text-sm font-medium text-vscode-text mb-3">Prerequisites</h3>
          <ul className="text-xs text-vscode-muted space-y-2">
            <li>✓ Azure AD app registration with Log Analytics API permissions</li>
            <li>✓ Application Insights connected to a Log Analytics workspace</li>
            <li>✓ Reader access to the Log Analytics workspace</li>
          </ul>
          <p className="mt-4 text-xs text-vscode-muted">
            Set <code className="bg-vscode-bg px-1 rounded">VITE_AZURE_CLIENT_ID</code> and{' '}
            <code className="bg-vscode-bg px-1 rounded">VITE_AZURE_TENANT_ID</code> in your{' '}
            <code className="bg-vscode-bg px-1 rounded">.env.local</code> file.
          </p>
        </div>
      </div>
    </div>
  )
}
