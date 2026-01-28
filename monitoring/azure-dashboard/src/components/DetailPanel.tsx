import { useState, useMemo } from 'react'
import type { TreeNode, ParsedSpan, DetailTab, Message } from '../lib/types'
import { formatJson, getTextContent } from '../lib/utils'

interface DetailPanelProps {
  node: TreeNode | null
  spans: ParsedSpan[]
}

export function DetailPanel({ node }: DetailPanelProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>('io')

  // Get relevant spans for the selected node
  const nodeSpans = useMemo(() => {
    if (!node) return []
    
    if (Array.isArray(node.data)) {
      return node.data as ParsedSpan[]
    }
    if (node.data) {
      return [node.data as ParsedSpan]
    }
    return []
  }, [node])

  if (!node) {
    return (
      <div className="flex-1 flex items-center justify-center bg-vscode-sidebar text-vscode-muted">
        <div className="text-center">
          <h2 className="text-lg mb-2">Select a node</h2>
          <p className="text-sm">Click on a trace node to view details</p>
        </div>
      </div>
    )
  }

  // Icon styles
  const iconStyles: Record<string, string> = {
    conversation: 'bg-gray-500',
    run: 'bg-purple-500',
    'run-step': 'bg-blue-500',
    tool: 'bg-emerald-500',
    message: 'bg-amber-500',
  }

  const iconLetters: Record<string, string> = {
    conversation: 'C',
    run: 'R',
    'run-step': 'S',
    tool: 'F',
    message: 'M',
  }

  return (
    <div className="flex-1 flex flex-col bg-vscode-sidebar overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-vscode-border">
        <span
          className={`
            w-6 h-6 rounded flex items-center justify-center
            text-xs font-semibold text-white
            ${iconStyles[node.type] || 'bg-gray-500'}
          `}
        >
          {iconLetters[node.type] || '?'}
        </span>
        <h2 className="flex-1 text-sm font-medium truncate">{node.label}</h2>
        {node.duration && <span className="text-xs text-vscode-muted">⏱ {node.duration}</span>}
        {node.tokens !== undefined && node.tokens > 0 && (
          <span className="px-2 py-0.5 bg-blue-900/50 text-blue-400 text-xs rounded">
            ⊛ {node.tokens}t
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-vscode-border bg-vscode-bg">
        <button
          onClick={() => setActiveTab('io')}
          className={`
            px-4 py-2.5 text-sm border-b-2 transition-colors
            ${activeTab === 'io'
              ? 'text-vscode-text border-vscode-accent'
              : 'text-vscode-muted border-transparent hover:text-vscode-text'}
          `}
        >
          Input & Output
        </button>
        <button
          onClick={() => setActiveTab('metadata')}
          className={`
            px-4 py-2.5 text-sm border-b-2 transition-colors
            ${activeTab === 'metadata'
              ? 'text-vscode-text border-vscode-accent'
              : 'text-vscode-muted border-transparent hover:text-vscode-text'}
          `}
        >
          Metadata
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'io' ? (
          <IOContent node={node} spans={nodeSpans} />
        ) : (
          <MetadataContent spans={nodeSpans} />
        )}
      </div>
    </div>
  )
}

function IOContent({ node, spans }: { node: TreeNode; spans: ParsedSpan[] }) {
  // For tool nodes, show arguments and result
  if (node.type === 'tool' && spans.length === 1) {
    const span = spans[0]
    let args: unknown = span.toolArgs
    let result: unknown = span.toolResult

    try {
      if (typeof args === 'string') args = JSON.parse(args)
    } catch { /* ignore */ }
    try {
      if (typeof result === 'string') result = JSON.parse(result)
    } catch { /* ignore */ }

    // Clean null values
    if (typeof args === 'object' && args !== null) {
      args = Object.fromEntries(
        Object.entries(args as Record<string, unknown>).filter(([, v]) => v !== null)
      )
    }

    return (
      <div className="space-y-5">
        <Section title="Arguments">
          <pre className="code-block">{formatJson(args)}</pre>
        </Section>
        <Section title="Result">
          <pre className="code-block">{formatJson(result)}</pre>
        </Section>
      </div>
    )
  }

  // For run-step nodes, show only the last user message (not the full history)
  // For run nodes, show all unique user messages
  const allUserMessages: string[] = []
  const allOutputMessages: Message[] = []
  const seenOutputContents = new Set<string>()

  for (const span of spans) {
    if (span.inputMessages) {
      for (const msg of span.inputMessages) {
        if (msg.role === 'user') {
          const content = getTextContent(msg)
          if (content && !allUserMessages.includes(content)) {
            allUserMessages.push(content)
          }
        }
      }
    }
    if (span.outputMessages) {
      for (const msg of span.outputMessages) {
        // Deduplicate output messages by their content
        const msgKey = JSON.stringify(msg)
        if (!seenOutputContents.has(msgKey)) {
          seenOutputContents.add(msgKey)
          allOutputMessages.push(msg)
        }
      }
    }
  }

  // For run and run-step nodes, only show the last user message (the one that triggered this run/step)
  // The full conversation history can be viewed at the Conversation level
  const displayUserMessages = (node.type === 'run' || node.type === 'run-step') && allUserMessages.length > 0
    ? [allUserMessages[allUserMessages.length - 1]]
    : allUserMessages

  return (
    <div className="space-y-5">
      {displayUserMessages.length > 0 && (
        <Section title="Input">
          {displayUserMessages.map((content, idx) => (
            <MessageBubble key={idx} role="user" content={content} />
          ))}
        </Section>
      )}
      
      {allOutputMessages.length > 0 && (
        <Section title="Output">
          {allOutputMessages.map((msg, idx) => (
            <MessageBubbleFromMessage key={idx} message={msg} />
          ))}
        </Section>
      )}

      {displayUserMessages.length === 0 && allOutputMessages.length === 0 && (
        <div className="text-center text-vscode-muted py-8">
          No input/output messages available
        </div>
      )}
    </div>
  )
}

function MetadataContent({ spans }: { spans: ParsedSpan[] }) {
  const primarySpan = spans[0]

  // Collect all unique attributes
  const allAttrs: Record<string, string | number | undefined> = {}
  for (const span of spans) {
    Object.assign(allAttrs, span.attributes)
  }

  return (
    <div className="space-y-5">
      {primarySpan && (
        <>
          <Section title="Span Information">
            <div className="space-y-2">
              <MetadataItem label="Trace ID" value={primarySpan.traceId} />
              <MetadataItem label="Span ID" value={primarySpan.id} />
              {primarySpan.parentId && <MetadataItem label="Parent ID" value={primarySpan.parentId} />}
              <MetadataItem label="Name" value={primarySpan.name} />
              <MetadataItem label="Duration" value={primarySpan.duration} />
              <MetadataItem label="Start Time" value={new Date(primarySpan.startTime).toLocaleString()} />
            </div>
          </Section>

          {(primarySpan.model || primarySpan.agentName) && (
            <Section title="Model">
              <div className="space-y-2">
                {primarySpan.model && <MetadataItem label="Model" value={primarySpan.model} />}
                {primarySpan.agentName && <MetadataItem label="Agent" value={primarySpan.agentName} />}
              </div>
            </Section>
          )}

          {(primarySpan.inputTokens || primarySpan.outputTokens) && (
            <Section title="Token Usage">
              <div className="space-y-2">
                <MetadataItem label="Input Tokens" value={String(primarySpan.inputTokens || 0)} />
                <MetadataItem label="Output Tokens" value={String(primarySpan.outputTokens || 0)} />
                <MetadataItem 
                  label="Total" 
                  value={String((primarySpan.inputTokens || 0) + (primarySpan.outputTokens || 0))} 
                />
              </div>
            </Section>
          )}
        </>
      )}

      {Object.keys(allAttrs).length > 0 && (
        <Section title="All Attributes">
          <div className="space-y-2">
            {Object.entries(allAttrs)
              .filter(([, v]) => v !== undefined)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([key, value]) => (
                <MetadataItem 
                  key={key} 
                  label={key} 
                  value={typeof value === 'object' ? JSON.stringify(value) : String(value)} 
                />
              ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-vscode-muted uppercase mb-2">{title}</h3>
      {children}
    </div>
  )
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between p-2 bg-vscode-bg border border-vscode-border rounded">
      <span className="text-xs text-vscode-muted">{label}</span>
      <span className="text-xs font-mono text-vscode-text break-all max-w-[60%] text-right">{value}</span>
    </div>
  )
}

function MessageBubble({ role, content }: { role: string; content: string }) {
  const borderColors: Record<string, string> = {
    user: 'border-l-blue-500',
    assistant: 'border-l-emerald-500',
    system: 'border-l-gray-500',
    tool: 'border-l-amber-500',
  }

  const labelColors: Record<string, string> = {
    user: 'text-blue-400',
    assistant: 'text-emerald-400',
    system: 'text-gray-400',
    tool: 'text-amber-400',
  }

  return (
    <div className={`bg-vscode-bg border border-vscode-border rounded-lg p-3 mb-2 border-l-[3px] ${borderColors[role] || 'border-l-gray-500'}`}>
      <div className={`text-[11px] font-semibold uppercase mb-1.5 ${labelColors[role] || 'text-gray-400'}`}>
        {role}
      </div>
      <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">{content}</div>
    </div>
  )
}

function MessageBubbleFromMessage({ message }: { message: Message }) {
  const { role, parts } = message

  for (const part of parts || []) {
    if (part.type === 'text' && part.content) {
      // Truncate long system messages
      let content = part.content
      if (role === 'system' && content.length > 200) {
        content = content.substring(0, 200) + '... (truncated)'
      }
      return <MessageBubble role={role} content={content} />
    }
    if (part.type === 'tool_call') {
      return (
        <div className="bg-vscode-bg border border-vscode-border rounded-lg p-3 mb-2 border-l-[3px] border-l-amber-500 font-mono text-xs">
          <div className="text-[11px] font-semibold uppercase mb-1.5 text-amber-400 flex items-center gap-2">
            tool_call: {part.name}
          </div>
          <pre className="code-block">{formatJson(part.arguments)}</pre>
        </div>
      )
    }
    if (part.type === 'tool_call_response') {
      let result = part.response
      try {
        if (typeof result === 'string') result = JSON.parse(result)
      } catch { /* ignore */ }
      return (
        <div className="bg-vscode-bg border border-vscode-border rounded-lg p-3 mb-2 border-l-[3px] border-l-amber-500 font-mono text-xs">
          <div className="text-[11px] font-semibold uppercase mb-1.5 text-amber-400">tool_result</div>
          <pre className="code-block">{formatJson(result)}</pre>
        </div>
      )
    }
  }

  return null
}
