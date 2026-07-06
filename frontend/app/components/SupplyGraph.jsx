"use client"
import React, { useState, useMemo } from "react"
import { toDisplayNumber, toDisplayDays, toDisplayDate } from "./SupplyGraph/utils"
import { InfoChip } from "./SupplyGraph/ui"
import TreeTableView from "./SupplyGraph/TreeTableView"
import RouteTableView from "./SupplyGraph/RouteTableView"

export default function SupplyGraph({ orderResult }) {
  const [viewMode, setViewMode] = useState("tree")

  const {
    facility,
    product,
    quantity,
    spec,
    buyer,
    warnings,
    order_index,
    forecast_summary,
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
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${viewMode === "tree"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-800"
              }`}
          >
            Tree & Table
          </button>

          <button
            type="button"
            onClick={() => setViewMode("route")}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${viewMode === "route"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-800"
              }`}
          >
            Route Table
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

      {viewMode === "route" ? (
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
