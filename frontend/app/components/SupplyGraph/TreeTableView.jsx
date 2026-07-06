import React, { Fragment, useState, useEffect, useMemo } from "react"
import {
  getTypeColor,
  getTypeBadgeClass,
  toDisplayNumber,
  toDisplayDays,
  toDisplayPercentage,
  formatFacilityTypeLabel,
  inferFacilityTypeFromName,
  normalizeDisplayFacilityType,
  buildTreeData,
} from "./utils"
import { EmptyState } from "./ui"
import TreeNode from "./TreeNode"
import CalculationDetailCard from "./CalculationDetailCard"

export default function TreeTableView({ orderResult }) {
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
  const [disabledNodes, setDisabledNodes] = useState(() => new Set())

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
        const nameA = a.supplier_name || a.supplier_id || ""
        const nameB = b.supplier_name || b.supplier_id || ""

        const typeA = inferFacilityTypeFromName(nameA, a.supplier_type).toUpperCase()
        const typeB = inferFacilityTypeFromName(nameB, b.supplier_type).toUpperCase()

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

        const daysA = Number(a.estimated_days || 0)
        const daysB = Number(b.estimated_days || 0)

        if (daysA !== daysB) {
          return daysA - daysB
        }

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

        const daysA = Number(a.estimated_days || 0)
        const daysB = Number(b.estimated_days || 0)

        if (daysA !== daysB) {
          return daysA - daysB
        }

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

  const totalAllocationQty = allocationRows.reduce((sum, row) => {
    if (disabledNodes.has(row.supplier_id) || disabledNodes.has(row.receiver_id)) return sum;
    return sum + Number(row.allocation_basis_quantity ?? row.quantity ?? 0);
  }, 0)

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
              className={`mb-3 inline-flex items-center gap-2 text-[12px] font-bold ${isAllExpanded
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
                node={{ ...root, disabled: disabledNodes.has(root.facilityId) }}
                selectedId={selectedId}
                onSelect={setSelectedId}
                expanded={expanded}
                toggleExpanded={toggleExpanded}
                disabledNodes={disabledNodes}
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

                  {selectedFacilityId !== String(facility) && (
                    <div className="mt-6 rounded-xl border border-rose-100 bg-rose-50/50 p-4">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                        <div>
                          <p className="text-sm font-bold text-rose-900">What-If Simulation</p>
                          <p className="text-xs text-rose-700 mt-1">Exclude this facility to simulate a supply chain disruption.</p>
                        </div>
                        <button
                          onClick={() => {
                            setDisabledNodes(prev => {
                              const next = new Set(prev)
                              if (next.has(selectedFacilityId)) next.delete(selectedFacilityId)
                              else next.add(selectedFacilityId)
                              return next
                            })
                          }}
                          className={`shrink-0 px-4 py-2 rounded-lg text-xs font-bold transition ${disabledNodes.has(selectedFacilityId)
                              ? "bg-rose-600 text-white shadow-md hover:bg-rose-700"
                              : "bg-white border border-rose-200 text-rose-600 hover:bg-rose-100"
                            }`}
                        >
                          {disabledNodes.has(selectedFacilityId) ? "Restore Facility" : "Exclude Facility"}
                        </button>
                      </div>
                    </div>
                  )}
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
                className={`rounded-lg px-4 py-2 text-xs font-bold transition ${routeDirection === "incoming"
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
                className={`rounded-lg px-4 py-2 text-xs font-bold transition ${routeDirection === "outgoing"
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
              className={`rounded-xl border px-4 py-3 ${isRefinerySelected
                  ? "bg-blue-50 border-blue-100"
                  : "bg-orange-50 border-orange-100"
                }`}
            >
              <p
                className={`text-[10px] uppercase tracking-wide font-bold ${isIncomingView ? "text-blue-500" : "text-orange-500"
                  }`}
              >
                {isIncomingView
                  ? "Total Incoming Allocation"
                  : "Total Outgoing Allocation"}
              </p>
              <p
                className={`text-lg font-bold mt-1 ${isIncomingView ? "text-blue-800" : "text-orange-800"
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
                    {isIncomingView ? "Incoming Quantity" : "Outgoing Quantity"}
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    {isIncomingView ? "Source Plant" : "Destination Facility"}
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    {isIncomingView ? "Incoming Share" : "Outgoing Share"}
                  </th>
                  <th className="px-5 py-3 text-left text-[13px] font-bold tracking-wide text-gray-500">
                    {isIncomingView ? "Source Type" : "Destination Type"}
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

                    const allocationShare = totalAllocationQty > 0 ? (Number(row.allocation_basis_quantity ?? row.quantity ?? 0) / totalAllocationQty) * 100 : 0
                    const isDisabled = disabledNodes.has(row.supplier_id) || disabledNodes.has(row.receiver_id)

                    return (
                      <Fragment key={calculationKey}>
                        <tr className={`hover:bg-gray-50 transition-all ${isDisabled ? "opacity-50 grayscale bg-gray-50" : ""}`}>
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
                                  className={`h-full rounded-full ${isIncomingView ? "bg-blue-500" : "bg-orange-500"
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
