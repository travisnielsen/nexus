import { useState, useCallback } from 'react'
import type { TreeNode } from '../lib/types'

interface TreeViewProps {
  tree: TreeNode
  selectedNode: TreeNode | null
  onSelectNode: (node: TreeNode) => void
}

export function TreeView({ tree, selectedNode, onSelectNode }: TreeViewProps) {
  return (
    <div className="py-2">
      <TreeNodeComponent
        node={tree}
        depth={0}
        selectedNode={selectedNode}
        onSelectNode={onSelectNode}
      />
    </div>
  )
}

interface TreeNodeComponentProps {
  node: TreeNode
  depth: number
  selectedNode: TreeNode | null
  onSelectNode: (node: TreeNode) => void
}

function TreeNodeComponent({ node, depth, selectedNode, onSelectNode }: TreeNodeComponentProps) {
  const [expanded, setExpanded] = useState(node.expanded ?? true)
  
  const hasChildren = node.children && node.children.length > 0
  const isSelected = selectedNode?.id === node.id

  const handleToggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (hasChildren) {
      setExpanded(!expanded)
    }
  }, [hasChildren, expanded])

  const handleSelect = useCallback(() => {
    onSelectNode(node)
  }, [node, onSelectNode])

  // Icon colors based on node type
  const iconStyles: Record<string, string> = {
    conversation: 'bg-gray-500',
    run: 'bg-purple-500',
    'run-step': 'bg-blue-500',
    tool: 'bg-emerald-500',
    message: 'bg-amber-500',
  }

  // Icon letters
  const iconLetters: Record<string, string> = {
    conversation: 'C',
    run: 'R',
    'run-step': 'S',
    tool: 'F',
    message: 'M',
  }

  return (
    <div className="select-none">
      <div
        onClick={handleSelect}
        className={`
          flex items-center gap-1.5 px-2 py-1 cursor-pointer
          border-l-[3px] border-transparent
          ${isSelected ? 'bg-vscode-selected border-l-vscode-accent' : 'hover:bg-vscode-hover'}
        `}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {/* Expand/collapse icon */}
        <span
          onClick={handleToggle}
          className={`
            w-4 h-4 flex items-center justify-center text-[10px] text-vscode-muted
            transition-transform duration-150
            ${expanded ? 'rotate-90' : ''}
            ${hasChildren ? 'cursor-pointer' : 'invisible'}
          `}
        >
          ▶
        </span>

        {/* Node type icon */}
        <span
          className={`
            w-[18px] h-[18px] rounded flex items-center justify-center
            text-[10px] font-semibold text-white
            ${iconStyles[node.type] || 'bg-gray-500'}
          `}
        >
          {iconLetters[node.type] || '?'}
        </span>

        {/* Label */}
        <span className="flex-1 text-sm truncate">{node.label}</span>

        {/* Metadata */}
        {(node.duration || node.tokens !== undefined) && (
          <span className="flex gap-2 text-[11px] text-vscode-muted">
            {node.duration && <span>⏱ {node.duration}</span>}
            {node.tokens !== undefined && node.tokens > 0 && <span>⊛ {node.tokens}t</span>}
          </span>
        )}
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div className="border-l border-vscode-border ml-5">
          {node.children!.map((child) => (
            <TreeNodeComponent
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedNode={selectedNode}
              onSelectNode={onSelectNode}
            />
          ))}
        </div>
      )}
    </div>
  )
}
