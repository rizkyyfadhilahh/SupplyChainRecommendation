import React, { Fragment, useState, useMemo } from "react"
import { buildTreeData, inferFacilityTypeFromName, getUniqueOptions, groupRouteRows } from "./utils"
import { EmptyState, SearchableFilterDropdown } from "./ui"
import MemoizedRouteRow from "./MemoizedRouteRow"

export default function RouteTableView({ orderResult }) {
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

                <th className="px-5 py-3 text-right text-[11px] font-bold uppercase tracking-wide text-gray-500 whitespace-nowrap">
                  🌱 PCF/unit
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
