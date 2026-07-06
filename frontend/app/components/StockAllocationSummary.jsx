import { useState } from "react"
import StockOverview from "./StockOverview"
import { formatKg } from "../utils"

export default function StockAllocationSummary({ orderResult }) {

  const orderIndex = orderResult?.orderIndex || "-"
  const [showDetails, setShowDetails] = useState(false)

  const stockOverview = orderResult?.stock_overview || {}
  const summary = stockOverview?.summary || {}

  const stockStatus = summary.stock_status || "UNKNOWN"
  const fulfilledFromStock = Number(summary.fulfilled_from_stock || 0)
  const unmetDemand = Number(summary.unmet_demand || 0)
  const totalStockAllocated = Number(summary.total_stock_allocated || 0)

  const stockDemandBasis = fulfilledFromStock + unmetDemand
  const fulfilledPercentage = stockDemandBasis > 0 ? (fulfilledFromStock / stockDemandBasis) * 100 : 0
  const unmetPercentage = stockDemandBasis > 0 ? (unmetDemand / stockDemandBasis) * 100 : 0

  const formatPercent = (value) =>
    Number(value || 0).toLocaleString("id-ID", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })

  const selectedSlocs = stockOverview?.selected_slocs || []
  const selectedSlocCount = selectedSlocs.length

  const statusLabel =
    stockStatus === "FULLY_FULFILLED"
      ? "Fully Fulfilled"
      : stockStatus === "PARTIALLY_FULFILLED"
      ? "Partially Fulfilled"
      : stockStatus === "NOT_FULFILLED"
      ? "Not Fulfilled"
      : stockStatus

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold text-gray-900">
                Stock Allocation Summary
              </h2>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowDetails((prev) => !prev)}
            className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-bold text-gray-600 hover:bg-gray-50"
          >
            {showDetails ? "Hide Stock & SLOC Details" : "View Stock & SLOC Details"}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-4">
          <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-2.5">
            <p className="text-[10px] uppercase tracking-wide text-gray-400 font-bold">
              Status
            </p>
            <p className="text-sm font-bold text-gray-800 mt-1">
              {statusLabel}
            </p>
          </div>

          <div className="rounded-xl border border-green-100 bg-green-50 px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-green-600">
              Fulfilled From Stock
            </p>
            <p className="mt-1 text-sm font-bold text-green-900">
              {formatKg(fulfilledFromStock)} Kg / {formatPercent(fulfilledPercentage)}%
            </p>
          </div>

          <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-red-600">
              Unmet Demand
            </p>
            <p className="mt-1 text-sm font-bold text-red-900">
              {formatKg(unmetDemand)} Kg / {formatPercent(unmetPercentage)}%
            </p>
          </div>

          <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-2.5">
            <p className="text-[10px] uppercase tracking-wide text-gray-400 font-bold">
              Selected SLOCs
            </p>
            <p className="text-sm font-bold text-gray-800 mt-1">
              {selectedSlocCount} SLOC{selectedSlocCount !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
          <p className="text-s text-blue-800 leading-relaxed">
            {stockStatus === "FULLY_FULFILLED"
              ? `The order is fully fulfilled from available stock. ${formatKg(
                  totalStockAllocated
                )} Kg has been allocated from selected SLOCs, so no additional recommendation volume is required.`
              : stockStatus === "PARTIALLY_FULFILLED"
              ? `${formatKg(
                  fulfilledFromStock
                )} Kg (${formatPercent(
                  fulfilledPercentage
                )}%) is fulfilled from available stock, while ${formatKg(
                  unmetDemand
                )} Kg (${formatPercent(
                  unmetPercentage
                )}%) remains as unmet demand and will be covered by the recommendation route.`
              : `No available stock was allocated for this order. The full requested quantity (${formatPercent(
                unmetPercentage
              )}%) will be covered by the recommendation route.`}
          </p>
        </div>

        {stockDemandBasis > 0 && (
          <div className="mt-3">
            <div className="rounded-xl overflow-hidden h-3 bg-gray-100 border border-gray-100 flex">
              <div
                className="bg-green-500 h-full transition-all"
                style={{ width: `${fulfilledPercentage}%` }}
              />
              <div
                className="bg-red-400 h-full transition-all"
                style={{ width: `${unmetPercentage}%` }}
              />
            </div>
            <div className="mt-1.5 flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-[11px] font-medium text-gray-500">
                  Fulfilled from stock {formatPercent(fulfilledPercentage)}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-red-400" />
                <span className="text-[11px] font-medium text-gray-500">
                  Unmet demand {formatPercent(unmetPercentage)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {showDetails && (
        <div className="p-0">
          <StockOverview orderResult={orderResult} />
        </div>
      )}
    </div>
  )
}
