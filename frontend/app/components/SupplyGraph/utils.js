export const TYPE_COLORS = {
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

export const TYPE_BADGE_CLASSES = {
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

export function toDisplayDays(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return "0.0"

  if (num > 0 && num < 0.1) {
    return "<0.1"
  }

  return num.toFixed(1)
}

export function toDisplayNumber(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return "0"
  return num.toLocaleString("id-ID")
}

export function normalizeDisplayFacilityType(type) {
  const value = String(type || "UNKNOWN").toUpperCase().trim()
  if (value === "TRADING") return "TRADER"
  return value || "UNKNOWN"
}

export function inferFacilityTypeFromName(name, fallbackType = "UNKNOWN") {
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

export function getTypeColor(type) {
  return TYPE_COLORS[normalizeDisplayFacilityType(type)] || TYPE_COLORS.UNKNOWN
}

export function getTypeBadgeClass(type) {
  return TYPE_BADGE_CLASSES[normalizeDisplayFacilityType(type)] || TYPE_BADGE_CLASSES.UNKNOWN
}

export function toRawNumber(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return 0
  return num
}

export function hasQueueSchedule(row) {
  return Boolean(row?.queue_enabled || row?.arrival_date || row?.start_date)
}

export function toDisplayDate(value) {
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

export function toDisplayQueueDay(startDay, finishDay) {
  const start = Number(startDay ?? 0)
  const finish = Number(finishDay ?? 0)

  if (!Number.isFinite(start) || !Number.isFinite(finish)) {
    return "-"
  }

  return `Day ${start} → Day ${finish}`
}

export function getEstimatedFormula(row) {
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

export function formatFacilityTypeLabel(type) {
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

export function getAllocationMaterialLabel(rows, fallbackProduct = "") {
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

export function toDisplayPercentage(value) {
  const num = Number(value || 0)

  if (!Number.isFinite(num)) return "0.0"

  return num.toLocaleString("id-ID", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
}

export function getUniqueOptions(rows, getter) {
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

export function getRouteGroupValue(row, groupBy) {
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

export function groupRouteRows(rows, groupBy) {
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

export function buildTreeData({ facility, tree }) {
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
        edgeRow: row,
        parentFacilityId: parentFacilityId,
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
