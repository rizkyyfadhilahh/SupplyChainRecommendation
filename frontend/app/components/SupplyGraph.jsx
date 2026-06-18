"use client"

import React, { Fragment, useEffect, useMemo, useRef, useState } from "react"

const TYPE_COLORS = {
  ESTATE: "#10B981",
  MILL: "#F59E0B",
  KCP: "#8B5CF6",
  REFINERY: "#3B82F6",
  VENDOR: "#A112C1",
  BULKING: "#111827",
  TRADER: "#64748B",
  TRADING: "#64748B",
  UNKNOWN: "#94A3B8",
}

const TYPE_BADGE_CLASSES = {
  REFINERY: "bg-blue-50 text-blue-700 border-blue-200",
  MILL: "bg-amber-50 text-amber-700 border-amber-200",
  ESTATE: "bg-green-50 text-green-700 border-green-200",
  VENDOR: "bg-purple-50 text-purple-700 border-purple-200",
  BULKING: "bg-gray-100 text-gray-700 border-gray-200",
  TRADER: "bg-slate-50 text-slate-700 border-slate-200",
  TRADING: "bg-slate-50 text-slate-700 border-slate-200",
  KCP: "bg-violet-50 text-violet-700 border-violet-200",
  UNKNOWN: "bg-gray-50 text-gray-600 border-gray-200",
}

function toDisplayDays(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return "0.0"

  if (num > 0 && num < 0.1) {
    return "<0.1"
  }

  return num.toFixed(1)
}

function toDisplayNumber(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return "0"
  return num.toLocaleString("id-ID")
}

function normalizeDisplayFacilityType(type) {
  const value = String(type || "UNKNOWN").toUpperCase().trim()
  if (value === "TRADING") return "TRADER"
  return value || "UNKNOWN"
}

function inferFacilityTypeFromName(name, fallbackType = "UNKNOWN") {
  const facilityName = String(name || "").toUpperCase()
  const fallback = normalizeDisplayFacilityType(fallbackType)

  if (
    facilityName.includes("ESTATE") ||
    facilityName.includes("PLASMA")
  ) {
    return "ESTATE"
  }

  return fallback || "UNKNOWN"
}

function getTypeColor(type) {
  return TYPE_COLORS[normalizeDisplayFacilityType(type)] || TYPE_COLORS.UNKNOWN
}

function getTypeBadgeClass(type) {
  return TYPE_BADGE_CLASSES[normalizeDisplayFacilityType(type)] || TYPE_BADGE_CLASSES.UNKNOWN
}

function getRouteBadgeMeta(routeKind = "", supplierSourceKind = "") {
  const value = String(routeKind || supplierSourceKind || "").toUpperCase()

  if (value.includes("KCP_PK_TO_PKO")) {
    return {
      label: "KCP Route",
      className: "bg-violet-50 text-violet-700 border-violet-200",
    }
  }

  if (value.includes("TOLLING_RECEIVER")) {
    return {
      label: "Tolling Receiver",
      className: "bg-orange-50 text-orange-700 border-orange-200",
    }
  }

  if (value.includes("TOLLING_PROCESSING")) {
    return {
      label: "Tolling Processor",
      className: "bg-amber-50 text-amber-700 border-amber-200",
    }
  }

  if (value.includes("TOLLING")) {
    return {
      label: "Tolling",
      className: "bg-orange-50 text-orange-700 border-orange-200",
    }
  }

  if (value.includes("FFB_ORIGIN") || value.includes("KCP_PK_FFB_ORIGIN")) {
    return {
      label: "FFB Origin",
      className: "bg-green-50 text-green-700 border-green-200",
    }
  }

  if (value.includes("TERMINAL_MILL")) {
    return {
      label: "Terminal Mill",
      className: "bg-slate-50 text-slate-700 border-slate-200",
    }
  }

  if (value.includes("DIRECT")) {
    return {
      label: "Direct Supply",
      className: "bg-blue-50 text-blue-700 border-blue-200",
    }
  }

  if (String(supplierSourceKind || "").toUpperCase().includes("VENDOR")) {
    return {
      label: "Vendor",
      className: "bg-purple-50 text-purple-700 border-purple-200",
    }
  }

  return {
    label: "Route",
    className: "bg-gray-50 text-gray-600 border-gray-200",
  }
}

function RouteBadge({ routeKind, supplierSourceKind }) {
  const meta = getRouteBadgeMeta(routeKind, supplierSourceKind)

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-bold whitespace-nowrap ${meta.className}`}
    >
      {meta.label}
    </span>
  )
}

function QuantityWithBasis({ row, align = "right" }) {
  const product = String(row?.product || "").toUpperCase()
  const actualQty = Number(row?.quantity || 0)

  const basisProduct = String(
    row?.allocation_basis_product || product
  ).toUpperCase()

  const basisQty = Number(
    row?.allocation_basis_quantity ?? actualQty
  )

  const showBasis =
    basisProduct &&
    product &&
    basisProduct !== product &&
    Number.isFinite(basisQty) &&
    basisQty > 0

  return (
    <div className={align === "right" ? "text-right" : "text-left"}>
      <p className="font-semibold text-gray-800 whitespace-nowrap">
        {toDisplayNumber(actualQty)} Kg
      </p>

      {showBasis && (
        <p className="mt-1 text-[11px] font-medium text-gray-400 whitespace-nowrap">
          ≈ {toDisplayNumber(basisQty)} Kg {basisProduct} basis
        </p>
      )}
    </div>
  )
}

function InfoChip({ label, value, className = "" }) {
  return (
    <div
      className={`flex flex-col items-center border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 min-w-[80px] ${className}`}
    >
      <span className="text-[10px] text-gray-700 uppercase tracking-wide font-medium">
        {label}
      </span>
      <span className="text-xs font-semibold text-gray-700 mt-0.5">
        {value}
      </span>
    </div>
  )
}

function EmptyState({ message = "No supply chain recommendation." }) {
  return (
    <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
      {message}
    </div>
  )
}

function buildTreeData({ facility, tree }) {
  const rows = tree || []
  const facilityKey = String(facility || "")

  const facilityMetaMap = new Map()

  facilityMetaMap.set(facilityKey, {
    name: facilityKey,
    type: "REFINERY",
  })

  rows.forEach((row) => {
    const supplierId = String(row.supplier_id || "").trim()
    const receiverId = String(row.receiver_id || facilityKey).trim()

    if (supplierId) {
      const supplierName = row.supplier_name || supplierId
      const supplierType = inferFacilityTypeFromName(
        supplierName,
        row.supplier_type || "UNKNOWN"
      )

      if (!facilityMetaMap.has(supplierId)) {
        facilityMetaMap.set(supplierId, {
          name: supplierName,
          type: supplierType,
        })
      } else {
        const existing = facilityMetaMap.get(supplierId)

        if (!existing.name || existing.name === supplierId) {
          existing.name = supplierName
        }

        if (
          (!existing.type || existing.type === "UNKNOWN") &&
          supplierType !== "UNKNOWN"
        ) {
          existing.type = supplierType
        }

        existing.type = inferFacilityTypeFromName(existing.name, existing.type)
      }
    }

    if (receiverId && !facilityMetaMap.has(receiverId)) {
      facilityMetaMap.set(receiverId, {
        name: receiverId,
        type: receiverId === facilityKey ? "REFINERY" : inferFacilityTypeFromName(receiverId, "UNKNOWN"),
      })
    }
  })

  const rowsByReceiver = new Map()

  rows.forEach((row, index) => {
    const receiverId = String(row.receiver_id || facilityKey).trim()

    if (!rowsByReceiver.has(receiverId)) {
      rowsByReceiver.set(receiverId, [])
    }

    rowsByReceiver.get(receiverId).push({
      ...row,
      __rowIndex: index,
    })
  })

  const nodeMap = new Map()

  const root = {
    id: `root__${facilityKey}`,
    facilityId: facilityKey,
    name: facilityKey,
    type: "REFINERY",
    children: [],
    level: 0,
    repeatedPath: false,
  }

  nodeMap.set(root.id, root)

  const buildChildren = (parentNode, ancestors, depth = 0) => {
    const parentFacilityId = String(parentNode.facilityId)
    const childRows = rowsByReceiver.get(parentFacilityId) || []

    childRows.forEach((row) => {
      const supplierId = String(row.supplier_id || "").trim()
      if (!supplierId) return

      const supplierMeta = facilityMetaMap.get(supplierId) || {}
      const supplierName = supplierMeta.name || row.supplier_name || supplierId
      const supplierType = inferFacilityTypeFromName(
        supplierName,
        supplierMeta.type || row.supplier_type || "UNKNOWN"
      )

      const isRepeated = ancestors.has(supplierId)

      const nodeInstanceId = [
        parentNode.id,
        supplierId,
        row.product || "",
        row.__rowIndex,
      ].join("__")

      const childNode = {
        id: nodeInstanceId,
        facilityId: supplierId,
        name: supplierName,
        type: supplierType,
        children: [],
        level: Number(row.level || depth) + 1,
        repeatedPath: isRepeated,
        edgeRow : row,
        parentFacilityId : parentFacilityId,
      }

      nodeMap.set(childNode.id, childNode)
      parentNode.children.push(childNode)

      if (!isRepeated) {
        const nextAncestors = new Set(ancestors)
        nextAncestors.add(supplierId)
        buildChildren(childNode, nextAncestors, depth + 1)
      }
    })
  }

  buildChildren(root, new Set([facilityKey]), 0)

  nodeMap.forEach((node) => {
    node.children.sort((a, b) => {
      const typeCompare = String(a.type || "").localeCompare(String(b.type || ""))
      if (typeCompare !== 0) return typeCompare
      return String(a.name).localeCompare(String(b.name))
    })
  })

  return {
    root,
    nodeMap,
    facilityMetaMap,
  }
}

function TreeNode({
  node,
  selectedId,
  onSelect,
  expanded,
  toggleExpanded,
  depth = 0,
}) {
  const nodeId = String(node.id)
  const hasChildren = node.children?.length > 0
  const isOpen = expanded.has(nodeId)
  const isSelected = selectedId === nodeId

  return (
    <div>
      <div
        className={`group flex items-center gap-2 rounded-md py-[3px] pr-2 text-sm transition ${
          isSelected
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
          className="min-w-0 flex-1 truncate text-left text-[13px] font-medium leading-5"
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
              node={child}
              selectedId={selectedId}
              onSelect={onSelect}
              expanded={expanded}
              toggleExpanded={toggleExpanded}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function toRawNumber(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return 0
  return num
}

function hasQueueSchedule(row) {
  return Boolean(row?.queue_enabled || row?.arrival_date || row?.start_date)
}

function toDisplayDate(value) {
  if (!value) return "-"

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

function toDisplayQueueDay(startDay, finishDay) {
  const start = Number(startDay ?? 0)
  const finish = Number(finishDay ?? 0)

  if (!Number.isFinite(start) || !Number.isFinite(finish)) {
    return "-"
  }

  return `Day ${start} → Day ${finish}`
}

function getEstimatedFormula(row) {
  const qty = toRawNumber(row.quantity)
  const throughput = toRawNumber(row.throughput_tpd)
  const flow = throughput > 0 ? qty / throughput : 0
  const finalDays = flow > 0 ? Math.ceil(flow) : 0

  return {
    qty,
    throughput,
    flow,
    finalDays,
  }
}

function MiniTooltip({ text }) {
  return (
    <span className="relative inline-flex items-center group">
      <span className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-blue-200 bg-blue-50 text-[10px] font-bold text-blue-600 cursor-help">
        i
      </span>

      <span className="pointer-events-none absolute left-1/2 bottom-full mb-2 z-[9999] hidden w-max max-w-[220px] -translate-x-1/2 rounded-xl border border-gray-100 bg-white px-3 py-2 text-left text-xs font-normal leading-relaxed text-gray-600 shadow-xl group-hover:block">
        <span className="absolute -bottom-1 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-b border-r border-gray-100 bg-white" />
        {text}
      </span>
    </span>
  )
}

function CalculationMetricCard({ label, value, tooltip }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
      <p className="text-[10px] font-bold tracking-wide text-gray-400 inline-flex items-center">
        {label}
        <MiniTooltip text={tooltip} />
      </p>

      <p className="mt-1 text-sm font-bold text-gray-800">
        {value}
      </p>
    </div>
  )
}

function CalculationDetailCard({ row, isRefinerySelected, getDestinationName }) {
  const formula = getEstimatedFormula(row)
  const queueEnabled = hasQueueSchedule(row)

  const directionLabel = isRefinerySelected
    ? "Incoming Route"
    : "Outgoing Route"

  const fromLabel = row.supplier_name || row.supplier_id || "-"
  const toLabel = getDestinationName(row.receiver_id)

  return (
 <div className="w-full overflow-visible rounded-2xl border border-gray-200 bg-white shadow-sm transition-all hover:shadow-md">
      {/* 1. Header Section - Clean context framing */}
      <div className="rounded-t-2xl border-b border-gray-100 bg-gray-50/50 px-5 py-4">
       <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div>
            <p className="mb-1 text-[10px] font-bold tracking-widest text-slate-400 uppercase">
              Route Insight • {directionLabel}
            </p>
            
            <div className="flex items-center gap-2 text-sm font-bold text-gray-900">
              <span>{fromLabel}</span>
              <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path>
              </svg>
              <span>{toLabel}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-[11px] font-bold text-gray-600 shadow-sm">
              {row.product || "-"}
            </span>
            <span className="flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700 shadow-sm">
              <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              {toDisplayDays(row.estimated_days)} Days
            </span>
          </div>
        </div>
      </div>

      {/* 2. Metrics Body Section */}
      <div className="p-5">
        <div className={`grid grid-cols-2 gap-4 ${queueEnabled ? "md:grid-cols-3" : ""}`}>
          <CalculationMetricCard
            label="Allocated Qty"
            value={`${toDisplayNumber(formula.qty)} Kg`}
            tooltip={`This route can process approximately ${toDisplayNumber(formula.throughput)} Kg per day.`}
          />

          <CalculationMetricCard
            label="Estimated Days"
            value={`${toDisplayDays(formula.finalDays)} Days`}
            tooltip="The final estimated days used in the recommendation result. This is Flow Days rounded up."
          />

          {queueEnabled && (
            <CalculationMetricCard
              label="Arrival Date"
              value={toDisplayDate(row.arrival_date)}
              tooltip="The estimated arrival date for this route after applying flow days and sequential queue scheduling."
            />
          )}
        </div>

        {/* 3. Highlight/Takeaway Callout */}
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50/50 to-transparent px-4 py-3.5">
          <div className="mt-0.5 shrink-0 text-blue-500">
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path>
            </svg>
          </div>
          <div>
            <p className="text-xs font-bold tracking-wide text-blue-900">
              Why This Route?
            </p>
            <p className="mt-1 text-sm leading-relaxed text-blue-800/80">
              <span className="font-semibold text-blue-900">{toDisplayNumber(formula.qty)} Kg</span> can be delivered through this route and is expected to arrive on <span className="font-semibold text-blue-900">{toDisplayDate(row.arrival_date)}</span>.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatFacilityTypeLabel(type) {
  const value = normalizeDisplayFacilityType(type)

    if (value === "REFINERY") return "Refinery"
    if (value === "MILL") return "Mill"
    if (value === "ESTATE") return "Estate"
    if (value === "VENDOR") return "Vendor"
    if (value === "BULKING") return "Bulking"
    if (value === "TRADER") return "Trader"
    if (value === "KCP") return "KCP"

  return "Facility"
}

function getAllocationMaterialLabel(rows, fallbackProduct = "") {
  const products = Array.from(
    new Set(
      (rows || [])
        .map((row) => String(row?.product || "").trim().toUpperCase())
        .filter(Boolean)
    )
  )

  if (products.length === 1) {
    return products[0]
  }

  if (products.length > 1) {
    return `Mixed: ${products.join(", ")}`
  }

  return String(fallbackProduct || "Material").toUpperCase()
}

function toDisplayPercentage(value) {
  const num = Number(value || 0)

  if (!Number.isFinite(num)) return "0.0"

  return num.toLocaleString("id-ID", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
}

function TreeTableView({ orderResult }) {
  const { facility, tree, product } = orderResult
  const { root, nodeMap, facilityMetaMap } = useMemo(
    () => buildTreeData({ facility, tree }),
    [facility, tree]
  )

  const rootId = root?.id || `root__${String(facility)}`

  const [selectedId, setSelectedId] = useState(rootId)
  const [expanded, setExpanded] = useState(() => new Set([rootId]))
  const [expandedCalculationKey, setExpandedCalculationKey] = useState(null)
  const [routeDirection, setRouteDirection] = useState("incoming")

  useEffect(() => {
    const nextRootId = root?.id || `root__${String(facility)}`

    setSelectedId(nextRootId)
    setExpandedCalculationKey(null)
    setRouteDirection("incoming")

    const defaultExpanded = new Set([nextRootId])

    nodeMap.forEach((node) => {
      if (Number(node.level || 0) <= 1) {
        defaultExpanded.add(node.id)
      }
    })

    setExpanded(defaultExpanded)
  }, [facility, tree, root, nodeMap])

  const selectedNode = nodeMap.get(selectedId) || root
  const selectedFacilityId = String(selectedNode?.facilityId || facility)

  const isRefinerySelected =
    selectedFacilityId === String(facility) ||
    normalizeDisplayFacilityType(selectedNode?.type) === "REFINERY"

  const selectedFacilityType = normalizeDisplayFacilityType(selectedNode?.type)
  const selectedFacilityTypeLabel = formatFacilityTypeLabel(selectedFacilityType)

  const incomingRows = useMemo(() => {
      if (!selectedNode) return []

      return (tree || [])
        .filter((row) => {
          const receiverId = String(row.receiver_id || facility).trim()
          return receiverId === selectedFacilityId
        })
        .sort((a, b) => {
          // Ambil nama dan inferensi tipe agar sorting 100% cocok dengan badge di UI
          const nameA = a.supplier_name || a.supplier_id || ""
          const nameB = b.supplier_name || b.supplier_id || ""
          
          const typeA = inferFacilityTypeFromName(nameA, a.supplier_type).toUpperCase()
          const typeB = inferFacilityTypeFromName(nameB, b.supplier_type).toUpperCase()

          // 1. Sistem Skor Prioritas (Estate tertinggi, disusul Mill, terakhir Vendor/Lainnya)
          const getWeight = (t) => {
            if (t === "ESTATE") return 3
            if (t === "MILL") return 2
            if (t === "VENDOR") return 1
            return 0
          }

          const weightA = getWeight(typeA)
          const weightB = getWeight(typeB)

          if (weightA !== weightB) {
            return weightB - weightA // Descending (Skor terbesar di atas)
          }

          // 2. Prioritas Estimated Days terkecil
          const daysA = Number(a.estimated_days || 0)
          const daysB = Number(b.estimated_days || 0)

          if (daysA !== daysB) {
            return daysA - daysB
          }

          // 3. Fallback: Urutkan nama sesuai abjad
          return String(nameA).localeCompare(String(nameB))
        })
    }, [tree, selectedNode, selectedFacilityId, facility])

  const outgoingRows = useMemo(() => {
      if (!selectedNode) return []

      return (tree || [])
        .filter((row) => {
          const supplierId = String(row.supplier_id || "").trim()
          return supplierId === selectedFacilityId
        })
        .sort((a, b) => {
          const nameA = a.receiver_name || a.receiver_id || ""
          const nameB = b.receiver_name || b.receiver_id || ""
          
          const typeA = inferFacilityTypeFromName(nameA, a.receiver_type).toUpperCase()
          const typeB = inferFacilityTypeFromName(nameB, b.receiver_type).toUpperCase()

          // 1. Sistem Skor Prioritas
          const getWeight = (t) => {
            if (t === "ESTATE") return 3
            if (t === "MILL") return 2
            if (t === "VENDOR") return 1
            return 0
          }

          const weightA = getWeight(typeA)
          const weightB = getWeight(typeB)

          if (weightA !== weightB) {
            return weightB - weightA
          }

          // 2. Prioritas Estimated Days terkecil
          const daysA = Number(a.estimated_days || 0)
          const daysB = Number(b.estimated_days || 0)

          if (daysA !== daysB) {
            return daysA - daysB
          }

          // 3. Fallback: Urutkan nama sesuai abjad
          return String(nameA).localeCompare(String(nameB))
        })
    }, [tree, selectedNode, selectedFacilityId])

  const allocationRows = useMemo(() => {
    if (routeDirection === "incoming") {
      return incomingRows
    }

    return outgoingRows
  }, [routeDirection, incomingRows, outgoingRows])

  const isIncomingView = routeDirection === "incoming"

  const totalAllocationQty = allocationRows.reduce(
    (sum, row) => sum + Number(row.allocation_basis_quantity ?? row.quantity ?? 0),
    0
  )

  const allocationMaterialLabel = (() => {
    const basisProducts = Array.from(
      new Set(
        (allocationRows || [])
          .map((row) => String(row?.allocation_basis_product || row?.product || "").trim().toUpperCase())
          .filter(Boolean)
      )
    )
    if (basisProducts.length === 1) return basisProducts[0]
    if (basisProducts.length > 1) return `Mixed: ${basisProducts.join(", ")}`
    return String(product || "Material").toUpperCase()
  })()

  const getDestinationName = (receiverId) => {
    const meta = facilityMetaMap.get(String(receiverId))
    return meta?.name || String(receiverId || "-")
  }

  const toggleExpanded = (nodeId) => {
    setExpanded((prev) => {
      const next = new Set(prev)

      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }

      return next
    })
  }

  const expandAll = () => {
    setExpanded(new Set(Array.from(nodeMap.keys())))
  }

  const collapseAll = () => {
    setExpanded(new Set([rootId]))
  }

  const allNodeIds = Array.from(nodeMap.keys())
  const isAllExpanded =
    allNodeIds.length > 0 && allNodeIds.every((id) => expanded.has(id))

  const toggleExpandCollapseAll = () => {
    if (isAllExpanded) {
      collapseAll()
    } else {
      expandAll()
    }
  }

  const toggleCalculationRow = (key) => {
    setExpandedCalculationKey((prev) => (prev === key ? null : key))
  }

  if (!tree?.length) {
    return <EmptyState />
  }

  return (
    <div className="p-4 bg-gray-50">
      <div className="grid grid-cols-1 xl:grid-cols-[500px_1fr] rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="border-r border-gray-200 bg-white">
          <div className="tree-scrollbar h-[500px] overflow-y-auto overflow-x-hidden p-4">
            <button
              type="button"
              onClick={toggleExpandCollapseAll}
              className={`mb-3 inline-flex items-center gap-2 text-[12px] font-bold ${
                isAllExpanded
                  ? "text-red-500 hover:text-red-600"
                  : "text-blue-600 hover:text-blue-700"
              }`}
            >
              <span className="flex h-4 w-4 items-center justify-center rounded-full border border-slate-300 bg-white text-[10px] text-slate-500">
                {isAllExpanded ? "×" : "⌄"}
              </span>
              {isAllExpanded ? "Collapse All" : "Expand All"}
            </button>

            {root ? (
              <TreeNode
                node={root}
                selectedId={selectedId}
                onSelect={setSelectedId}
                expanded={expanded}
                toggleExpanded={toggleExpanded}
              />
            ) : (
              <EmptyState message="Tree data is not available." />
            )}
          </div>
        </div>

        <div className="tree-scrollbar bg-white h-[500px] overflow-y-auto">
          <div className="px-5 py-4 border-b border-gray-100">
            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5">
              <div className="flex items-start gap-4">
                <div
                  className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
                  style={{
                    backgroundColor: `${getTypeColor(selectedFacilityType)}22`,
                    color: getTypeColor(selectedFacilityType),
                  }}
                >
                  <span
                    className="h-5 w-5 rounded-full"
                    style={{ backgroundColor: getTypeColor(selectedFacilityType) }}
                  />
                </div>

                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-bold text-gray-900">
                      {selectedNode?.name || "-"}
                    </h2>

                    {selectedNode?.repeatedPath && (
                      <span className="rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-[10px] font-bold text-orange-600">
                        Repeated path
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-gray-400 mt-1">
                    Selected facility from the recommendation route.
                  </p>

                  <div className="mt-5">
                    <h3 className="text-lg font-bold text-gray-900">
                      {selectedFacilityTypeLabel} Detail
                    </h3>

                    <div className="mt-3 space-y-3 text-sm">
                      <div className="grid grid-cols-[150px_12px_1fr] items-start gap-2">
                        <p className="text-gray-500">
                          {selectedFacilityTypeLabel} Name
                        </p>
                        <p className="text-gray-400">:</p>
                        <p className="font-semibold text-gray-900">
                          {selectedNode?.name || "-"}
                        </p>
                      </div>

                      <div className="grid grid-cols-[150px_12px_1fr] items-start gap-2">
                        <p className="text-gray-500">
                          {selectedFacilityTypeLabel} ID
                        </p>
                        <p className="text-gray-400">:</p>
                        <p className="font-semibold text-gray-900">
                          {selectedNode?.facilityId || selectedNode?.id || "-"}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>

          <div className="px-5 py-3 border-b border-gray-100 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-bold text-gray-900">
              
              </p>
              <p className="mt-0.5 text-xs text-gray-400">
               
              </p>
            </div>

            <div className="inline-flex w-fit rounded-xl border border-gray-200 bg-gray-50 p-1">
              <button
                type="button"
                onClick={() => setRouteDirection("incoming")}
                className={`rounded-lg px-4 py-2 text-xs font-bold transition ${
                  routeDirection === "incoming"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-800"
                }`}
              >
                Incoming Sources
                <span className="ml-1 text-[10px] text-gray-400">
                  ({incomingRows.length})
                </span>
              </button>

              <button
                type="button"
                onClick={() => setRouteDirection("outgoing")}
                className={`rounded-lg px-4 py-2 text-xs font-bold transition ${
                  routeDirection === "outgoing"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-800"
                }`}
              >
                Outgoing Route
                <span className="ml-1 text-[10px] text-gray-400">
                  ({outgoingRows.length})
                </span>
              </button>
            </div>
          </div>          

          <div className="px-5 py-4 border-b border-gray-100 grid grid-cols-1 md:grid-cols-1 gap-3">
            <div
              className={`rounded-xl border px-4 py-3 ${
                isRefinerySelected
                  ? "bg-blue-50 border-blue-100"
                  : "bg-orange-50 border-orange-100"
              }`}
            >
              <p
                className={`text-[10px] uppercase tracking-wide font-bold ${
                  isIncomingView  ? "text-blue-500" : "text-orange-500"
                }`}
              >
                {isIncomingView
                  ? "Total Incoming Allocation"
                  : "Total Outgoing Allocation"}
              </p>
              <p
                className={`text-lg font-bold mt-1 ${
                  isIncomingView  ? "text-blue-800" : "text-orange-800"
                }`}
              >
                {toDisplayNumber(totalAllocationQty)} Kg {allocationMaterialLabel}
              </p>
            </div>
          </div>

          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-200 border-b border-gray-100">
                <tr>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    Commodity
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    {isIncomingView  ? "Incoming Quantity" : "Outgoing Quantity"}
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    {isIncomingView  ? "Source Plant" : "Destination Facility"}
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    {isIncomingView  ? "Incoming Share" : "Outgoing Share"}
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    {isIncomingView  ? "Source Type" : "Destination Type"}
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    Estimated Days
                  </th>
                  <th className="px-5 py-3 text-right text-[13px] font-bold tracking-wide text-gray-500">
                    Details
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-100">
                {allocationRows.length > 0 ? (
                  allocationRows.map((row, index) => {
                    const destinationNode = facilityMetaMap.get(String(row.receiver_id))

                    const displayName = isIncomingView
                      ? row.supplier_name || row.supplier_id || "-"
                      : row.receiver_name || getDestinationName(row.receiver_id)

                    const displayId = isIncomingView
                      ? row.supplier_id || "-"
                      : row.receiver_id || "-"

                    const displayType = isIncomingView
                      ? inferFacilityTypeFromName(displayName, row.supplier_type || "UNKNOWN")
                      : inferFacilityTypeFromName(
                          displayName,
                          row.receiver_type || destinationNode?.type || "UNKNOWN"
                        )

                    const calculationKey = `${row.supplier_id}-${row.receiver_id}-${row.product}-${index}`

                    // ✅ SESUDAH
                    const allocationShare = totalAllocationQty > 0 ? (Number(row.allocation_basis_quantity ?? row.quantity ?? 0) / totalAllocationQty) * 100 : 0

                    return (
                      <Fragment key={calculationKey}>
                        <tr className="hover:bg-gray-50">
                          <td className="px-5 py-3">
                            <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-1 text-xs font-bold text-gray-700">
                              {row.product || "-"}
                            </span>
                          </td>

                          <td className="px-5 py-3 text-left font-semibold text-gray-800">
                            {toDisplayNumber(row.allocation_basis_quantity ?? row.quantity)} Kg
                          </td>

                          <td className="px-5 py-3">
                            <p className="font-semibold text-gray-800">
                              {displayName}
                            </p>
                            <p className="text-xs text-gray-400">
                              ID: {displayId}
                            </p>
                          </td>

                          <td className="px-5 py-3">
                            <div className="min-w-[120px]">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-sm font-bold text-gray-800">
                                  {toDisplayPercentage(allocationShare)}%
                                </span>
                              </div>

                              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-100">
                                <div
                                  className={`h-full rounded-full ${
                                    isIncomingView  ? "bg-blue-500" : "bg-orange-500"
                                  }`}
                                  style={{
                                    width: `${Math.min(Math.max(allocationShare, 0), 100)}%`,
                                  }}
                                />
                              </div>
                            </div>
                          </td>

                          <td className="px-5 py-3">
                            <span
                              className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${getTypeBadgeClass(
                                displayType
                              )}`}
                            >
                              {displayType}
                            </span>
                          </td>

                          <td className="px-5 py-3 text-left font-semibold text-gray-700">
                            {toDisplayDays(row.estimated_days)} days
                          </td>

                          <td className="px-5 py-3 text-right">
                            <button
                              type="button"
                              onClick={() => toggleCalculationRow(calculationKey)}
                              className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50"
                            >
                              {expandedCalculationKey === calculationKey ? "Hide" : "Details"}
                            </button>
                          </td>
                        </tr>

                        {expandedCalculationKey === calculationKey && (
                          <tr>
                            <td colSpan={6} className="bg-gray-50 px-5 py-4">
                              <CalculationDetailCard
                                row={row}
                                isRefinerySelected={isRefinerySelected}
                                getDestinationName={getDestinationName}
                              />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })
                ) : (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-5 py-10 text-center text-sm text-gray-400"
                    >
                      {isIncomingView
                        ? "Table shows incoming allocation sources flowing into the selected facility."
                        : "Table shows outgoing allocation from the selected facility to its next destination in the supply chain."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="px-5 py-3 bg-gray-50 border-t border-gray-100">
            <p className="text-xs text-gray-400">
              {isIncomingView
                        ? "Table shows incoming allocation sources flowing into the selected facility."
                        : "Table shows outgoing allocation from the selected facility to its next destination in the supply chain."}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function getUniqueOptions(rows, getter) {
  return Array.from(
    new Set(
      (rows || [])
        .map(getter)
        .filter(
          (value) =>
            value !== null &&
            value !== undefined &&
            String(value).trim() !== ""
        )
        .map((value) => String(value))
    )
  ).sort((a, b) => a.localeCompare(b))
}

function SearchableFilterDropdown({
  label,
  value,
  onChange,
  options = [],
  placeholder = "All",
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(value || "")

  useEffect(() => {
    setQuery(value || "")
  }, [value])

  const filteredOptions = useMemo(() => {
    const keyword = String(query || "").trim().toLowerCase()

    if (!keyword) return options.slice(0, 50)

    return options
      .filter((item) => String(item).toLowerCase().includes(keyword))
      .slice(0, 50)
  }, [options, query])

  const handlePick = (item) => {
    setQuery(item)
    onChange(item)
    setOpen(false)
  }

  const handleClear = () => {
    setQuery("")
    onChange("")
    setOpen(false)
  }

  return (
    <div className="relative flex flex-col gap-1">
      <label className="text-[10px] font-bold uppercase tracking-wide text-gray-400">
        {label}
      </label>

      <div
        className={`flex h-10 items-center rounded-lg border bg-white px-3 transition ${
          open ? "border-red-300 ring-2 ring-red-50" : "border-gray-200"
        }`}
      >
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent text-xs font-semibold text-gray-700 placeholder:text-gray-300 focus:outline-none"
        />

        {query ? (
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={handleClear}
            className="ml-2 shrink-0 text-xs font-bold text-gray-400 hover:text-gray-700"
          >
            ×
          </button>
        ) : (
          <span className="ml-2 shrink-0 text-xs text-gray-400">⌄</span>
        )}
      </div>

      {open && (
        <div className="tree-scrollbar absolute left-0 right-0 top-[58px] z-[9999] max-h-56 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-xl">
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={handleClear}
            className="block w-full px-3 py-2 text-left text-xs font-semibold text-gray-400 hover:bg-gray-50"
          >
            All
          </button>

          {filteredOptions.length > 0 ? (
            filteredOptions.map((item) => (
              <button
                key={item}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => handlePick(item)}
                className="block w-full px-3 py-2 text-left text-xs font-semibold text-gray-700 hover:bg-red-50"
              >
                {item}
              </button>
            ))
          ) : (
            <div className="px-3 py-3 text-xs text-gray-400">
              No options found
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function getRouteGroupValue(row, groupBy) {
  if (groupBy === "level") {
    return `Level ${Number(row.level || 0) + 1}`
  }

  if (groupBy === "from") {
    return row.supplier_name || row.supplier_id || "-"
  }

  if (groupBy === "to") {
    return row.receiver_name || row.receiver_id || "-"
  }

  if (groupBy === "commodity") {
    return row.product || "-"
  }

  return "All Routes"
}

function groupRouteRows(rows, groupBy) {
  if (!groupBy || groupBy === "none") {
    return [
      {
        key: "all",
        label: "All Routes",
        rows,
      },
    ]
  }

  const groupMap = new Map()

  rows.forEach((row) => {
    const label = getRouteGroupValue(row, groupBy)
    const key = `${groupBy}-${label}`

    if (!groupMap.has(key)) {
      groupMap.set(key, {
        key,
        label,
        rows: [],
      })
    }

    groupMap.get(key).rows.push(row)
  })

  return Array.from(groupMap.values()).sort((a, b) =>
    String(a.label).localeCompare(String(b.label))
  )
}

const MemoizedRouteRow = React.memo(({ 
  row, 
  routeKey, 
  fromType, 
  toType, 
  isDirectToRefinery, 
  getDestinationName, 
  isExpanded, 
  onToggle 
}) => {
  return (
    <Fragment>
      <tr className="hover:bg-gray-50 align-top">
        <td className="px-5 py-4">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600">
            {Number(row.level || 0) + 1}
          </span>
        </td>

        <td className="px-5 py-4">
          <div className="flex items-start gap-2">
            <span
              className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: getTypeColor(fromType) }}
            />
            <div className="min-w-0">
              <p className="font-semibold text-gray-800 leading-snug break-words">
                {row.supplier_name || row.supplier_id || "-"}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                ID: {row.supplier_id || "-"} • {fromType}
              </p>
            </div>
          </div>
        </td>

        <td className="px-5 py-4">
          <div className="flex items-start gap-2">
            <span
              className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: getTypeColor(toType) }}
            />
            <div className="min-w-0">
              <p className="font-semibold text-gray-800 leading-snug break-words">
                {row.receiver_name || getDestinationName(row.receiver_id)}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                ID: {row.receiver_id || "-"} • {toType}
              </p>
            </div>
          </div>
        </td>

        <td className="px-5 py-4">
          <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-1 text-xs font-bold text-gray-700">
            {row.product || "-"}
          </span>
        </td>

        <td className="px-5 py-4 text-right font-semibold text-gray-800 whitespace-nowrap">
          {toDisplayNumber(row.quantity)} Kg
        </td>

        <td className="px-5 py-4 text-right font-semibold text-gray-700 whitespace-nowrap">
          {toDisplayDays(row.estimated_days)} days
        </td>

        <td className="px-5 py-4 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
          {hasQueueSchedule(row) ? toDisplayDate(row.start_date) : "-"}
        </td>

        <td className="px-5 py-4 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
          {hasQueueSchedule(row) ? toDisplayDate(row.arrival_date) : "-"}
        </td>

        <td className="px-5 py-4 text-right">
          <button
            type="button"
            onClick={() => onToggle(routeKey)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50"
          >
            {isExpanded ? "Hide" : "Details"}
          </button>
        </td>
      </tr>

      {isExpanded && (
        <tr className="w-full">
          <td colSpan={100} className="w-full bg-gray-50 px-5 py-4">
            <CalculationDetailCard
              row={row}
              isRefinerySelected={isDirectToRefinery}
              getDestinationName={getDestinationName}
            />
          </td>
        </tr>
      )}
    </Fragment>
  )
});

function RouteTableView({ orderResult }) {
  const { facility, tree } = orderResult
  const { facilityMetaMap } = useMemo(
    () => buildTreeData({ facility, tree }),
    [facility, tree]
  )

  const [expandedRouteKey, setExpandedRouteKey] = useState(null)
  const [groupBy, setGroupBy] = useState("none")
  const [draftGroupBy, setDraftGroupBy] = useState("none")

  const [draftFilters, setDraftFilters] = useState({
    fromFacility: "",
    toFacility: "",
    commodity: "",
    facilityType: "",
    facilityId: "",
  })

  const [appliedFilters, setAppliedFilters] = useState({
    fromFacility: "",
    toFacility: "",
    commodity: "",
    facilityType: "",
    facilityId: "",
  })

  const getDestinationName = (receiverId) => {
    const meta = facilityMetaMap.get(String(receiverId))
    return meta?.name || String(receiverId || "-")
  }

  const getDestinationType = (receiverId) => {
    const meta = facilityMetaMap.get(String(receiverId))
    return meta?.type || "REFINERY"
  }

  const routeRows = useMemo(() => {
    return (tree || [])
      .map((row, index) => {
        const receiverId = String(row.receiver_id || facility)
        const destinationNode = facilityMetaMap.get(receiverId)

        return {
          ...row,
          row_index: index,
          receiver_id: receiverId,
          receiver_name: destinationNode?.name || receiverId,
          receiver_type: destinationNode?.type || "REFINERY",
        }
      })
      .sort((a, b) => {
        const levelCompare = Number(a.level || 0) - Number(b.level || 0)
        if (levelCompare !== 0) return levelCompare

        const fromCompare = String(a.supplier_name || "").localeCompare(
          String(b.supplier_name || "")
        )

        if (fromCompare !== 0) return fromCompare

        return String(a.receiver_name || "").localeCompare(
          String(b.receiver_name || "")
        )
      })
  }, [tree, facility, facilityMetaMap])

  const fromFacilityOptions = useMemo(
    () =>
      getUniqueOptions(
        routeRows,
        (row) => row.supplier_name || row.supplier_id
      ),
    [routeRows]
  )

  const toFacilityOptions = useMemo(
    () =>
      getUniqueOptions(
        routeRows,
        (row) => row.receiver_name || row.receiver_id
      ),
    [routeRows]
  )

  const commodityOptions = useMemo(
    () => getUniqueOptions(routeRows, (row) => row.product),
    [routeRows]
  )

  const facilityTypeOptions = useMemo(() => {
    const supplierTypes = getUniqueOptions(
      routeRows,
      (row) =>
        inferFacilityTypeFromName(
          row.supplier_name || row.supplier_id,
          row.supplier_type
        )
    )

    const receiverTypes = getUniqueOptions(
      routeRows,
      (row) =>
        inferFacilityTypeFromName(
          row.receiver_name || row.receiver_id,
          row.receiver_type
        )
    )

    return Array.from(new Set([...supplierTypes, ...receiverTypes])).sort(
      (a, b) => a.localeCompare(b)
    )
  }, [routeRows])

  const filteredRouteRows = useMemo(() => {
    return routeRows.filter((row) => {
      const fromName = String(
        row.supplier_name || row.supplier_id || ""
      ).toLowerCase()
      const toName = String(
        row.receiver_name || row.receiver_id || ""
      ).toLowerCase()
      const commodity = String(row.product || "").toLowerCase()

      const fromType = inferFacilityTypeFromName(
        row.supplier_name || row.supplier_id,
        row.supplier_type
      ).toLowerCase()

      const toType = inferFacilityTypeFromName(
        row.receiver_name || row.receiver_id,
        row.receiver_type
      ).toLowerCase()

      const supplierId = String(row.supplier_id || "").toLowerCase()
      const receiverId = String(row.receiver_id || "").toLowerCase()

      if (
        appliedFilters.fromFacility &&
        fromName !== String(appliedFilters.fromFacility).toLowerCase()
      ) {
        return false
      }

      if (
        appliedFilters.toFacility &&
        toName !== String(appliedFilters.toFacility).toLowerCase()
      ) {
        return false
      }

      if (
        appliedFilters.commodity &&
        commodity !== String(appliedFilters.commodity).toLowerCase()
      ) {
        return false
      }

      if (appliedFilters.facilityType) {
        const selectedType = String(appliedFilters.facilityType).toLowerCase()

        if (fromType !== selectedType && toType !== selectedType) {
          return false
        }
      }

      if (appliedFilters.facilityId) {
        const keyword = String(appliedFilters.facilityId).toLowerCase()

        if (!supplierId.includes(keyword) && !receiverId.includes(keyword)) {
          return false
        }
      }

      return true
    })
  }, [routeRows, appliedFilters])

  const groupedRouteRows = useMemo(
    () => groupRouteRows(filteredRouteRows, groupBy),
    [filteredRouteRows, groupBy]
  )

  const totalRouteQty = filteredRouteRows.reduce(
    (sum, row) => sum + Number(row.quantity || 0),
    0
  )

  const maxEstimatedDays = filteredRouteRows.reduce(
    (max, row) => Math.max(max, Number(row.estimated_days || 0)),
    0
  )

  const toggleRouteDetail = (key) => {
    setExpandedRouteKey((prev) => (prev === key ? null : key))
  }

  const applyRouteFilters = () => {
    setAppliedFilters(draftFilters)
    setGroupBy(draftGroupBy)
    setExpandedRouteKey(null)
  }

  const resetRouteFilters = () => {
    const emptyFilters = {
      fromFacility: "",
      toFacility: "",
      commodity: "",
      facilityType: "",
      facilityId: "",
    }

    setDraftFilters(emptyFilters)
    setAppliedFilters(emptyFilters)
    setDraftGroupBy("none")
    setGroupBy("none")
    setExpandedRouteKey(null)
  }

  if (!tree?.length) {
    return <EmptyState />
  }

  return (
    <div className="p-4 bg-gray-50">
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="px-5 py-5 border-b border-gray-100">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900">
                Route Table
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                All recommended supply chain movements for this order.
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-3">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-[120px_1.2fr_1.2fr_120px_120px_1fr_80px_80px] gap-2 items-end">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold uppercase tracking-wide text-gray-400">
                  Group By
                </label>
                <select
                  value={draftGroupBy}
                  onChange={(e) => setDraftGroupBy(e.target.value)}
                  className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-xs font-semibold text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-100"
                >
                  <option value="none">None</option>
                  <option value="level">Level</option>
                  <option value="from">From</option>
                  <option value="to">To</option>
                  <option value="commodity">Commodity</option>
                </select>
              </div>

              <SearchableFilterDropdown
                label="From"
                value={draftFilters.fromFacility}
                onChange={(value) =>
                  setDraftFilters((prev) => ({
                    ...prev,
                    fromFacility: value,
                  }))
                }
                options={fromFacilityOptions}
                placeholder="All from facilities"
              />

              <SearchableFilterDropdown
                label="To"
                value={draftFilters.toFacility}
                onChange={(value) =>
                  setDraftFilters((prev) => ({
                    ...prev,
                    toFacility: value,
                  }))
                }
                options={toFacilityOptions}
                placeholder="All destinations"
              />

              <SearchableFilterDropdown
                label="Commodity"
                value={draftFilters.commodity}
                onChange={(value) =>
                  setDraftFilters((prev) => ({
                    ...prev,
                    commodity: value,
                  }))
                }
                options={commodityOptions}
                placeholder="All"
              />

              <SearchableFilterDropdown
                label="Type"
                value={draftFilters.facilityType}
                onChange={(value) =>
                  setDraftFilters((prev) => ({
                    ...prev,
                    facilityType: value,
                  }))
                }
                options={facilityTypeOptions}
                placeholder="All"
              />

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold uppercase tracking-wide text-gray-400">
                  Facility ID
                </label>
                <input
                  value={draftFilters.facilityId}
                  onChange={(e) =>
                    setDraftFilters((prev) => ({
                      ...prev,
                      facilityId: e.target.value,
                    }))
                  }
                  placeholder="Search ID..."
                  className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-xs font-semibold text-gray-700 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-red-100"
                />
              </div>

              <button
                type="button"
                onClick={applyRouteFilters}
                className="h-10 rounded-lg bg-red-500 px-4 text-xs font-bold text-white hover:bg-red-600"
              >
                Search
              </button>

              <button
                type="button"
                onClick={resetRouteFilters}
                className="h-10 rounded-lg border border-gray-200 bg-white px-4 text-xs font-bold text-gray-600 hover:bg-gray-50"
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        <div className="tree-scrollbar max-h-[500px] overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-gray-500 w-[70px]">
                  Level
                </th>

                <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-gray-500 min-w-[240px]">
                  From
                </th>

                <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-gray-500 min-w-[240px]">
                  To
                </th>

                <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-gray-500">
                  Commodity
                </th>

                <th className="px-5 py-3 text-right text-[11px] font-bold uppercase tracking-wide text-gray-500">
                  Quantity
                </th>

                <th className="px-5 py-3 text-right text-[11px] font-bold uppercase tracking-wide text-gray-500">
                  Est. Days
                </th>

                <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-gray-500">
                  Start
                </th>

                <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-gray-500">
                  Arrival
                </th>

                <th className="px-5 py-3 text-right text-[11px] font-bold uppercase tracking-wide text-gray-500">
                  Details
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-100">
              {groupedRouteRows.length > 0 ? (
                groupedRouteRows.map((group) => (
                  <Fragment key={group.key}>
                    {groupBy !== "none" && (
                      <tr>
                        <td colSpan={9} className="bg-gray-100 px-5 py-2">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-xs font-bold uppercase tracking-wide text-gray-600">
                              {groupBy === "level"
                                ? "Level"
                                : groupBy === "from"
                                ? "From Facility"
                                : groupBy === "to"
                                ? "To Facility"
                                : "Commodity"}
                              :{" "}
                              <span className="normal-case tracking-normal">
                                {group.label}
                              </span>
                            </p>

                            <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold text-gray-500 border border-gray-200">
                              {group.rows.length} route
                              {group.rows.length !== 1 ? "s" : ""}
                            </span>
                          </div>
                        </td>
                      </tr>
                    )}

                    {group.rows.map((row, index) => {
                      const routeKey = `${group.key}-${row.supplier_id}-${row.receiver_id}-${row.product}-${row.row_index ?? index}`

                      const fromType = inferFacilityTypeFromName(
                        row.supplier_name || row.supplier_id,
                        row.supplier_type || "UNKNOWN"
                      )

                      const toType = inferFacilityTypeFromName(
                        row.receiver_name || getDestinationName(row.receiver_id),
                        row.receiver_type || getDestinationType(row.receiver_id)
                      )

                      const isDirectToRefinery =
                        String(row.receiver_id || "") === String(facility)

                      return (
                        <MemoizedRouteRow
                      key={routeKey}
                      row={row}
                      routeKey={routeKey}
                      fromType={fromType}
                      toType={toType}
                      isDirectToRefinery={isDirectToRefinery}
                      getDestinationName={getDestinationName}
                      isExpanded={expandedRouteKey === routeKey}
                      onToggle={toggleRouteDetail}
                    />
                  )
                })}
                  </Fragment>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={9}
                    className="px-5 py-10 text-center text-sm text-gray-400"
                  >
                    No routes match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="px-5 py-3 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-400">
            Route Table shows all source-to-destination movements in one view.
            Facility name, ID, and type are shown together to avoid cutting important information.
          </p>
        </div>
      </div>
    </div>
  )
}

function GraphView({ orderResult }) {
  const containerRef = useRef(null)
  const networkRef = useRef(null)

  const { facility, quantity, tree, warnings, forecast_summary } = orderResult

  const unmetDemandQty = Number(forecast_summary?.unmet_demand_qty || 0)

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      !containerRef.current ||
      !tree?.length
    ) {
      return
    }

    const loadVis = () =>
      new Promise((resolve) => {
        if (window.vis) return resolve()

        const script = document.createElement("script")
        script.src =
          "https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"
        script.onload = resolve
        document.head.appendChild(script)
      })

    let cancelled = false

    loadVis().then(() => {
      if (cancelled || !containerRef.current || !window.vis) return

      // Menggunakan requestAnimationFrame agar UI tidak freeze saat pindah tab
      requestAnimationFrame(() => {
        if (cancelled) return;

        const warnedIds = new Set((warnings || []).map((w) => w.supplier_id))
        const nodesMap = {}
        const edgesArr = []

        nodesMap[facility] = {
          id: facility,
          label: `${facility}\n${toDisplayNumber(unmetDemandQty)} Kg`,
          level: 0,
          color: TYPE_COLORS.REFINERY,
          borderColor: "#FFFFFF",
          bwidth: unmetDemandQty > 0 ? 3 : 1,
        }

        tree.forEach((row) => {
          const supplierId = String(row.supplier_id)
          const receiverNode = row.level === 0 ? facility : String(row.receiver_id)
          const supplierQty = Number(row.quantity || 0)
          const supplierType = inferFacilityTypeFromName(
            row.supplier_name || supplierId,
            row.supplier_type || "UNKNOWN"
          )

          if (!nodesMap[supplierId]) {
            nodesMap[supplierId] = {
              id: supplierId,
              label: `${row.supplier_name || supplierId}\n${toDisplayNumber(supplierQty)} Kg`,
              level: Number(row.level || 0) + 1,
              color: getTypeColor(supplierType),
              borderColor: warnedIds.has(supplierId) ? "#FF0000" : "#FFFFFF",
              bwidth: warnedIds.has(supplierId) ? 4 : 1,
            }
          }

          edgesArr.push({
            from: supplierId,
            to: receiverNode,
            label: hasQueueSchedule(row)
              ? `${row.product} • ${toDisplayDays(row.estimated_days)}d • ${toDisplayDate(row.arrival_date)}`
              : `${row.product} • ${toDisplayDays(row.estimated_days)}d`,
          })
        })

        const visNodes = Object.values(nodesMap).map((node) => ({
          id: node.id,
          label: node.label,
          level: node.level,
          shape: "box",
          margin: { top: 10, right: 14, bottom: 10, left: 14 },
          widthConstraint: { minimum: 140, maximum: 190 },
          color: {
            background: node.color,
            border: node.borderColor,
            highlight: { background: node.color, border: "#111827" },
          },
          borderWidth: node.bwidth,
          font: { size: 11, color: "#FFFFFF", face: "Arial", bold: true, multi: "md" },
        }))

        const visEdges = edgesArr.map((edge, index) => ({
          id: index,
          from: edge.from,
          to: edge.to,
          label: edge.label,
          arrows: "to",
          font: { size: 10, align: "middle", color: "#4B5563", strokeWidth: 0 },
          color: { color: "#A3A3A3" },
          smooth: { type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 },
        }))

        const nodes = new window.vis.DataSet(visNodes)
        const edges = new window.vis.DataSet(visEdges)

        const options = {
          layout: {
            hierarchical: {
              enabled: true,
              direction: "RL",
              sortMethod: "directed",
              levelSeparation: 260,
              nodeSpacing: 120,
              treeSpacing: 180,
              blockShifting: true,
              edgeMinimization: true,
              parentCentralization: true,
            },
          },
          physics: { enabled: false },
          interaction: { hover: false, zoomView: true, dragView: true, tooltipDelay: 100 },
        }

        if (networkRef.current) {
          networkRef.current.destroy()
        }

        networkRef.current = new window.vis.Network(
          containerRef.current,
          { nodes, edges },
          options
        )
      }); // Penutup requestAnimationFrame
    })

    return () => {
      cancelled = true

      if (networkRef.current) {
        networkRef.current.destroy()
        networkRef.current = null
      }
    }
  }, [tree, facility, quantity, warnings, unmetDemandQty])

  if (!tree?.length) {
    return <EmptyState />
  }

  return (
    <div className="p-4">
      <div
        ref={containerRef}
        className="w-full overflow-auto rounded-xl border border-gray-100 bg-gray-50"
        style={{
          height: "500px",
          minWidth: "1200px",
        }}
      />
    </div>
  )
}

export default function SupplyGraph({ orderResult }) {
  const [viewMode, setViewMode] = useState("tree")

  const {
    facility,
    product,
    quantity,
    spec,
    buyer,
    tree,
    warnings,
    order_index,
    forecast_summary,
    option_type,
  } = orderResult

  const uniqueWarnings = useMemo(
    () =>
      (warnings || []).filter(
        (warning, index, arr) =>
          arr.findIndex((item) => item.supplier_id === warning.supplier_id) ===
          index
      ),
    [warnings]
  )

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Recommendation Supply Plan
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
             Review the recommended stock usage, incoming allocation, supplier route, and estimated completion.
          </p>
        </div>

        <div className="inline-flex rounded-xl border border-gray-200 bg-gray-50 p-1">
          <button
            type="button"
            onClick={() => setViewMode("tree")}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
              viewMode === "tree"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            Tree & Table
          </button>

          <button
            type="button"
            onClick={() => setViewMode("route")}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
              viewMode === "route"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            Route Table
          </button>

          <button
            type="button"
            onClick={() => setViewMode("graph")}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
              viewMode === "graph"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            Supply Graph
          </button>
        </div>
      </div>

      <div className="px-5 py-3 border-b border-gray-100 bg-gray-50/50 flex flex-wrap items-center gap-2">
        <span className="bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full">
          Order #{order_index}
        </span>

        <div className="flex flex-wrap gap-2">
          <InfoChip label="Refinery" value={facility} />
          <InfoChip label="Product" value={product} />
          <InfoChip label="Quantity" value={`${toDisplayNumber(quantity)} Kg`} />
          <InfoChip
            label="Spec"
            value={spec}
            className={
              spec === "EUDR"
                ? "bg-green-50 border-green-200 text-green-700"
                : ""
            }
          />

          {buyer && (
            <InfoChip
              label="Buyer"
              value={buyer}
              className="bg-purple-50 border-purple-200 text-purple-700"
            />
          )}

          <InfoChip
            label="Unmet Demand"
            value={`${toDisplayNumber(
              forecast_summary?.unmet_demand_qty || 0
            )} Kg`}
          />

          <InfoChip
            label="Total Estimated Days"
            value={`${toDisplayDays(
              forecast_summary?.total_estimated_days
            )} days`}
          />

          {forecast_summary?.queue_scheduling_enabled && (
            <InfoChip
              label="Batch Completion Date"
              value={toDisplayDate(forecast_summary?.batch_completion_date)}
              className="bg-emerald-50 border-emerald-200 text-emerald-700"
            />
          )}
        </div>
      </div>

      {viewMode === "graph" ? (
        <GraphView orderResult={orderResult} />
      ) : viewMode === "route" ? (
        <RouteTableView orderResult={orderResult} />
      ) : (
        <TreeTableView orderResult={orderResult} />
      )}

      {uniqueWarnings.length > 0 && (
        <div className="mx-6 mb-6 bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-800">
          <p className="font-semibold mb-1">
            ⚠️ Tree adjustment: Buyer{" "}
            <span className="font-bold">{buyer}</span> menerapkan no-buy list
            untuk:
          </p>

          <ul className="list-disc pl-5 space-y-0.5">
            {uniqueWarnings.map((warning) => (
              <li key={warning.supplier_id}>
                {warning.supplier_id} - {warning.supplier_name}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
