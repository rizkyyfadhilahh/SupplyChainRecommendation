import React from "react"
import { getTypeColor } from "./utils"

export default function TreeNode({
  node,
  selectedId,
  onSelect,
  expanded,
  toggleExpanded,
  disabledNodes,
  depth = 0,
}) {
  const nodeId = String(node.id)
  const hasChildren = node.children?.length > 0
  const isOpen = expanded.has(nodeId)
  const isSelected = selectedId === nodeId

  return (
    <div>
      <div
        className={`group flex items-center gap-2 rounded-md py-[3px] pr-2 text-sm transition ${isSelected
            ? "bg-gray-100 text-gray-900"
            : "text-gray-700 hover:bg-gray-50"
          }`}
        style={{ paddingLeft: `${depth * 22}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              toggleExpanded(node.id)
            }}
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-slate-300 bg-white text-[10px] leading-none text-slate-500 hover:bg-slate-50"
          >
            {isOpen ? "⌄" : "›"}
          </button>
        ) : (
          <span className="h-4 w-4 shrink-0" />
        )}

        <span className="relative inline-flex shrink-0 items-center group/dot">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: getTypeColor(node.type) }}
          />

          <span className="pointer-events-none absolute left-1/2 bottom-5 z-[9999] hidden -translate-x-1/2 whitespace-nowrap rounded-lg border border-gray-100 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-gray-700 shadow-lg group-hover/dot:block">
            <span className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r border-gray-100 bg-white" />
            Facility: {node.type}
          </span>
        </span>

        <button
          type="button"
          onClick={() => onSelect(node.id)}
          className={`min-w-0 flex-1 truncate text-left text-[13px] font-medium leading-5 ${node.disabled ? "line-through text-gray-400" : ""}`}
        >
          {node.name}
        </button>

        {node.repeatedPath && (
          <span className="shrink-0 rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-[10px] font-bold text-orange-600">
            Repeated
          </span>
        )}

        {hasChildren && (
          <span className="shrink-0 text-[11px] font-medium text-gray-400">
            ({node.children.length})
          </span>
        )}
      </div>

      {hasChildren && isOpen && (
        <div className="mt-[2px]">
          {node.children.map((child) => (
            <TreeNode
              key={`${node.id}-${child.id}`}
              node={{ ...child, disabled: node.disabled || disabledNodes?.has(child.facilityId) }}
              selectedId={selectedId}
              onSelect={onSelect}
              expanded={expanded}
              toggleExpanded={toggleExpanded}
              disabledNodes={disabledNodes}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}
