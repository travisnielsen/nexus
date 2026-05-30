import type { TraceCoverageSummary } from '../lib/types'

interface TraceCoverageSummaryProps {
  summary: TraceCoverageSummary | null
  loading: boolean
}

function pctClass(value: number): string {
  if (value >= 99) return 'text-green-400'
  if (value >= 95) return 'text-yellow-400'
  return 'text-red-400'
}

export function TraceCoverageSummaryPanel({ summary, loading }: TraceCoverageSummaryProps) {
  if (loading) {
    return (
      <div className="p-3 border-b border-vscode-border text-sm text-vscode-muted">
        Calculating trace coverage...
      </div>
    )
  }

  if (!summary) {
    return null
  }

  return (
    <div className="p-3 border-b border-vscode-border bg-vscode-bg">
      <div className="text-xs uppercase text-vscode-muted mb-2">Trace Coverage ({summary.windowHours}h)</div>
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div>
          <div className="text-vscode-muted">Turns</div>
          <div className={pctClass(summary.turnCoveragePct)}>{summary.turnCoveragePct.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-vscode-muted">Tools</div>
          <div className={pctClass(summary.toolCoveragePct)}>{summary.toolCoveragePct.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-vscode-muted">A2A</div>
          <div className={pctClass(summary.a2aCoveragePct)}>{summary.a2aCoveragePct.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-vscode-muted">Turns Sampled</div>
          <div className="text-vscode-text">{summary.sampledTurns}</div>
        </div>
      </div>
    </div>
  )
}
