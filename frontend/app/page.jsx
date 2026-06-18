"use client"

import { useEffect, useRef, useState } from "react"
import OrderForm from "./components/OrderForm"
import OrderList from "./components/OrderList"
import StockOverview from "./components/StockOverview"
import SupplyGraph from "./components/SupplyGraph"

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

function formatKg(value) {
  const num = Number(value || 0)

  if (!Number.isFinite(num)) return "0"

  return num.toLocaleString("id-ID", {
    maximumFractionDigits: 0,
  })
}
function getIncomingAllocationInfo(orderResult) {
  const summary = orderResult?.forecast_summary || {}
  const tree = orderResult?.tree || []

  const facility = String(orderResult?.facility || "").trim()

  const incomingRows = tree.filter((row) => {
    const isRootLevel = Number(row?.level || 0) === 0
    const isIncomingToFacility =
      facility && String(row?.receiver_id || "").trim() === facility

    return isRootLevel || isIncomingToFacility
  })

  const incomingQtyFromRows = incomingRows.reduce(
    (sum, row) => sum + Number(row?.quantity || 0),
    0
  )

  const incomingQty = Number(
    summary?.allocated_root_qty ??
      summary?.total_incoming_allocation ??
      incomingQtyFromRows
  )

  const materialTypes = Array.from(
    new Set(
      incomingRows
        .map((row) => String(row?.product || "").trim().toUpperCase())
        .filter(Boolean)
    )
  )

  const fallbackProduct = String(orderResult?.product || "").trim().toUpperCase()

  const materialLabel =
    materialTypes.length === 1
      ? materialTypes[0]
      : materialTypes.length > 1
      ? `Mixed: ${materialTypes.join(", ")}`
      : fallbackProduct || "Material"

  return {
    quantity: Number.isFinite(incomingQty) ? incomingQty : 0,
    materialLabel,
  }
}
function SuccessPopup({ show }) {
  if (!show) return null

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-gray-900/25 backdrop-blur-[1px]">
      <div className="success-popup w-[360px] overflow-hidden rounded-3xl bg-white shadow-2xl border border-pink-100">
        <div className="relative bg-gradient-to-br from-pink-50 via-rose-50 to-white px-6 pt-8 pb-6 text-center">
          <div className="absolute left-10 top-8 h-2 w-2 rounded-full bg-pink-300" />
          <div className="absolute right-12 top-10 h-1.5 w-1.5 rounded-full bg-rose-300" />
          <div className="absolute left-20 bottom-7 h-1.5 w-1.5 rounded-full bg-pink-200" />
          <div className="absolute right-20 bottom-8 h-2 w-2 rounded-full bg-rose-200" />

          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-pink-500 text-white shadow-lg shadow-pink-200">
            <svg
              className="h-10 w-10"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2.8"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>

        <div className="px-8 py-8 text-center">
          <p className="text-2xl font-semibold leading-snug text-gray-900">
            Your Recommendation
            <br />
            generated successfully.
          </p>
        </div>
      </div>
    </div>
  )
}
function StockAllocationSummary({ orderResult }) {

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
      </div>

      {showDetails && (
        <div className="p-0">
          <StockOverview orderResult={orderResult} />
        </div>
      )}
    </div>
  )
}
function ResultPagination({ results, activeIndex, onChange }) {
  const total = results.length
  if (total <= 1) return null

  const goPrevious = () => onChange(Math.max(activeIndex - 1, 0))
  const goNext = () => onChange(Math.min(activeIndex + 1, total - 1))

  return (
    <div className="flex items-center gap-3">
      <span className="text-s text-gray-600 font-medium whitespace-nowrap">
        Showing Order {activeIndex + 1} from {total}
      </span>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={goPrevious}
          disabled={activeIndex === 0}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <button
          type="button"
          onClick={goNext}
          disabled={activeIndex === total - 1}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  )
}
function FullScreenLoading() {
  const loadingSteps = [
    "Checking stock",
    "Tracing suppliers",
    "Calculating allocation",
    "Estimating schedule",
  ]

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-white">
      <div className="w-full max-w-4xl px-6">
        <div className="rounded-3xl border border-gray-100 bg-white px-8 py-10 text-center shadow-sm">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-rose-50">
            <div className="relative h-11 w-11 animate-[spin_1.2s_linear_infinite]">
              <span className="absolute left-1/2 top-1 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-rose-500" />
              <span className="absolute left-1 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-rose-500" />
              <span className="absolute right-1 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-rose-500" />
              <span className="absolute bottom-1 left-1/2 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-rose-500" />
            </div>
          </div>

          <h2 className="text-lg font-bold text-gray-900">
            Generating supply chain recommendation
          </h2>

          <p className="mx-auto mt-2 max-w-2xl text-sm leading-relaxed text-gray-500">
            The system is checking stock availability, tracing historical suppliers,
            calculating allocation, and estimating the delivery schedule.
          </p>

          <div className="mx-auto mt-7 grid max-w-3xl grid-cols-1 gap-3 md:grid-cols-4">
            {loadingSteps.map((step, index) => (
              <div
                key={step}
                className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-rose-500 text-xs font-bold text-white">
                    {index + 1}
                  </span>

                  <p className="text-xs font-bold text-gray-700">
                    {step}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="mx-auto mt-7 h-1.5 max-w-xl overflow-hidden rounded-full bg-gray-100">
            <div className="h-full w-1/2 animate-[loadingBar_1.5s_ease-in-out_infinite] rounded-full bg-rose-300" />
          </div>

          <p className="mt-4 text-xs text-gray-400">
            Complex recommendation routes may take longer to process.
          </p>
        </div>

        <style jsx>{`
          @keyframes loadingBar {
            0% {
              transform: translateX(-100%);
            }
            50% {
              transform: translateX(70%);
            }
            100% {
              transform: translateX(220%);
            }
          }
        `}</style>
      </div>
    </div>
  )
}
function EmptyResultState() {
  return (
    <div className="rounded-2xl border border-dashed border-gray-200 bg-white px-6 py-12 text-center">
      <h3 className="mt-4 text-base font-bold text-gray-900">
        No recommendation generated yet
      </h3>

      <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-gray-500">
        Add at least one order to the queue, then generate recommendation to see
        stock allocation, supplier route, and estimated completion result.
      </p>
    </div>
  )
}

export default function Home() {

  const [options, setOptions] = useState({
    refineries: [],
    buyers: [],
    products: [],
  })

  const [orders, setOrders] = useState([])
  const [results, setResults] = useState([])
  const [activeResultIndex, setActiveResultIndex] = useState(0)
  const [activeOptionIndex, setActiveOptionIndex] = useState(0) 
  const [loading, setLoading] = useState(false)
  const [optLoading, setOptLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showSuccessPopup, setShowSuccessPopup] = useState(false)
  const [isInputCollapsed, setIsInputCollapsed] = useState(false)

  const popupTimerRef = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/options`)
    .then((res) => res.json())
    .then((data) => setOptions(data))
    .catch(() =>
      setError("Gagal terhubung ke server. Pastikan FastAPI sudah berjalan di port 8000.")
    )
    .finally(() => setOptLoading(false))

    return () => {
      if (popupTimerRef.current) {
        clearTimeout(popupTimerRef.current)
      }
    }
  }, [])

  const showCompletedPopup = () => {
    setShowSuccessPopup(true)

    if (popupTimerRef.current) {
      clearTimeout(popupTimerRef.current)
    }

    popupTimerRef.current = setTimeout(() => {
      setShowSuccessPopup(false)
    }, 550)
  }

  const handleAddOrder = (order) => {
    setOrders((prev) => [...prev, order])
    setResults([])
    setShowSuccessPopup(false)
    setIsInputCollapsed(false)
    setActiveResultIndex(0)
    setActiveOptionIndex(0)
  }

  const handleRemoveOrder = (index) => {
    setOrders((prev) => prev.filter((_, i) => i !== index))
    setResults([])
    setShowSuccessPopup(false)
    setIsInputCollapsed(false)
    setActiveResultIndex(0)
    setActiveOptionIndex(0)
  }

  const handleGenerate = async () => {
    if (!orders.length) return

    setLoading(true)
    setError(null)
    setResults([])
    setShowSuccessPopup(false)

    const controller = new AbortController()

    const timeoutId = setTimeout(() => {
      controller.abort()
    }, 120000)

    try {
      const res = await fetch(`${API_BASE_URL}/api/trace`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ orders }),
        signal: controller.signal,
      })

      const text = await res.text()

      let data
      try {
        data = JSON.parse(text)
      } catch (parseError) {
        throw new Error(text || "Backend returned a non-JSON response.")
      }

      if (!res.ok) {
        throw new Error(
          data?.message ||
            data?.detail ||
            "Terjadi kesalahan saat tracing."
        )
      }

      const generatedOrders = data.orders || []

      setResults(generatedOrders)
      setActiveResultIndex(0)
      setActiveOptionIndex(0)
      setIsInputCollapsed(true)
      showCompletedPopup()
    } catch (err) {
      if (err.name === "AbortError") {
        setError("Recommendation generation took too long and was cancelled after 120 seconds.")
      } else {
        setError(err.message || "Terjadi kesalahan saat tracing.")
      }
    } finally {
      clearTimeout(timeoutId)
      setLoading(false)
    }
  }

  const handleChangeActiveResult = (index) => {
    setActiveResultIndex(index)
    setActiveOptionIndex(0) 
  }

  const activeResult = results[activeResultIndex] || null
  const recommendationOptions = activeResult?.recommendation_options || []
  const selectedOption = recommendationOptions[activeOptionIndex] || null

  const combinedResultForGraph = activeResult && selectedOption ? {
    ...activeResult,
    tree: selectedOption.tree,
    forecast_summary: selectedOption.forecast_summary,
    option_type: selectedOption.option_type
  } : activeResult;

  if (loading) {
    return <FullScreenLoading />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <SuccessPopup show={showSuccessPopup} />

      <nav className="bg-white border-b border-gray-100 px-14 py-4 flex items-center gap-10 sticky top-0 z-10">
        <div className="flex items-center shrink-0">
          <img
            src="/logo.png"
            alt="Logo"
            className="h-11 w-auto object-contain"
          />
        </div>

        <div className="flex items-center gap-2">
          <a
            href="/"
            className="text-[#98a2b3] text-[16px] not-italic font-medium leading-6 px-3 py-2 rounded-md transition-all duration-500 hover:bg-gray-50 hover:text-[#101828]"
          >
            Recommendation
          </a>

          <a
            href="/sloc"
            className="text-[#98a2b3] text-[16px] not-italic font-medium leading-6 px-3 py-2 rounded-md transition-all duration-500 hover:bg-gray-50 hover:text-[#101828]"
          >
            SLOC Configuration
          </a>
        </div>
      </nav>

      <main className="w-full max-w-[98vw] mx-auto px-3 md:px-4 py-6 flex flex-col gap-4">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 flex items-center gap-2">
            <span>⚠️</span>
            {error}
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-gray-800">
                Order Input & Queue
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                {isInputCollapsed
                  ? "Input section is collapsed to focus on the recommendation result."
                  : "Fill the order form and generate recommendation."}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setIsInputCollapsed((prev) => !prev)}
              className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50"
            >
              {isInputCollapsed ? "Show Input" : "Hide Input"}
            </button>
          </div>

          {!isInputCollapsed && (
            <div className="p-4 flex flex-col gap-4">
              {optLoading ? (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center font-semibold text-sm text-gray-400">
                  We're processing your data. This may take a few moments...
                </div>
              ) : (
                <OrderForm options={options} onAdd={handleAddOrder} />
              )}

              <OrderList
                orders={orders}
                onRemove={handleRemoveOrder}
                onGenerate={handleGenerate}
                loading={loading}
              />
            </div>
          )}
        </div>

        {results.length > 0 && (
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-gray-900">
                    Recommendation Results
                  </h2>

                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-bold text-gray-500">
                    {results.length} order{results.length > 1 ? "s" : ""}
                  </span>
                </div>

                <p className="mt-1 text-sm text-gray-500">
                  Review stock allocation, recommendation route, and estimated completion for the selected order.
                </p>
              </div>

              <ResultPagination
                results={results}
                activeIndex={activeResultIndex}
                onChange={handleChangeActiveResult}
              />
            </div>

            {activeResult && (
              <div className="flex flex-col gap-4">
                
                {combinedResultForGraph?.forecast_summary?.target_total_days_message && (
                  <div
                    className={`rounded-xl px-4 py-3 text-sm border ${
                      combinedResultForGraph?.forecast_summary?.target_total_days_met
                        ? "bg-green-50 border-green-200 text-green-700"
                        : "bg-yellow-50 border-yellow-200 text-yellow-700"
                    }`}
                  >
                    {combinedResultForGraph.forecast_summary.target_total_days_message}
                  </div>
                )}

                <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
                  <StockAllocationSummary orderResult={activeResult} />

                  <div className="border-t border-gray-100">
                    <SupplyGraph orderResult={combinedResultForGraph} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        {results.length === 0 && !loading && (
          <EmptyResultState />
        )}
      </main>
    </div>
  )
}