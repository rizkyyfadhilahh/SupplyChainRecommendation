"use client"

import { usePathname } from "next/navigation"
import OrderForm from "./components/OrderForm"
import OrderList from "./components/OrderList"
import SupplyGraph from "./components/SupplyGraph"
import TradeOfferGenerator from "./components/TradeOfferGenerator"

import { useTraceApi } from "./hooks/useTraceApi"
import { formatKg } from "./utils"
import SuccessPopup from "./components/SuccessPopup"
import StockAllocationSummary from "./components/StockAllocationSummary"
import BatchSummaryTable from "./components/BatchSummaryTable"
import RecommendationOptionCards from "./components/RecommendationOptionCards"
import ResultPagination from "./components/ResultPagination"
import FullScreenLoading from "./components/FullScreenLoading"
import EmptyResultState from "./components/EmptyResultState"
import ForecastSummaryDetail from "./components/ForecastSummaryDetail"
import PcfPieChart from "./components/charts/PcfPieChart"
import PcfAnalysisPanel from "./components/recommendation/PcfAnalysisPanel"

const exportToExcel = (orderResult) => {
  if (!orderResult) return
  
  const lines = []
  lines.push("Order Recommendation Export")
  lines.push(`Facility,${orderResult.facility}`)
  lines.push(`Product,${orderResult.product}`)
  lines.push(`Quantity (Kg),${orderResult.quantity}`)
  lines.push(`Buyer,${orderResult.buyer || "-"}`)
  lines.push("")

  lines.push("Stock Allocation")
  lines.push("Plant,SLOC,Material,Quantity (Kg),EUDR")
  const slocs = orderResult.stock_overview?.selected_slocs || []
  slocs.forEach(s => {
    lines.push(`${s.plant},${s.storagelocation},${s.material},${s.allocated_quantity},${s.eudr ? "YES" : "NO"}`)
  })
  lines.push("")

  lines.push("Recommendation Route Tree")
  lines.push("Level,Supplier ID,Supplier Name,Type,Product,Quantity (Kg),Est Days,Arrival")
  const tree = orderResult.tree || []
  tree.forEach(t => {
    lines.push(`${t.level},${t.supplier_id},"${t.supplier_name || ""}",${t.supplier_type},${t.product},${t.quantity},${t.estimated_days},${t.date_arrival || "-"}`)
  })

  const csvContent = lines.join("\n")
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", `Recommendation_${orderResult.facility}_${orderResult.product}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export default function Home() {
  const pathname = usePathname()

  const {
    options,
    orders,
    results,
    activeResultIndex,
    activeOptionIndex,
    loading,
    optLoading,
    error,
    showSuccessPopup,
    isInputCollapsed,
    showTradeOffer,
    setActiveOptionIndex,
    setShowTradeOffer,
    setIsInputCollapsed,
    handleAddOrder,
    handleRemoveOrder,
    handleGenerate,
    handleChangeActiveResult
  } = useTraceApi()

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

  const navLinks = [
    { href: "/", label: "Recommendation" },
    { href: "/drilldown", label: "Drill-Down" },
    { href: "/sloc", label: "SLOC Config" },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <SuccessPopup show={showSuccessPopup} />

      {showTradeOffer && (
        <TradeOfferGenerator
          orderResult={activeResult}
          selectedOption={selectedOption}
          onClose={() => setShowTradeOffer(false)}
        />
      )}

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
                <div className="flex items-center gap-2 flex-wrap">
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

              <div className="flex items-center gap-3 flex-wrap">
                {activeResult && (
                  <>
                    <button
                      type="button"
                      onClick={() => setShowTradeOffer(true)}
                      className="flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-sm font-bold text-white shadow-sm transition"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Generate Trade Offer
                    </button>
                    <a
                      href={`/drilldown?buyer=${encodeURIComponent(activeResult.buyer || '')}&product=${encodeURIComponent(activeResult.product || '')}`}
                      className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 px-4 py-2 text-sm font-bold text-gray-700 shadow-sm transition"
                    >
                      🔍 Drill Down This Order
                    </a>
                    <button
                      type="button"
                      onClick={() => exportToExcel(combinedResultForGraph)}
                      className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 px-4 py-2 text-sm font-bold text-gray-700 shadow-sm transition"
                    >
                      📥 Export Excel
                    </button>
                  </>
                )}
                <ResultPagination
                  results={results}
                  activeIndex={activeResultIndex}
                  onChange={handleChangeActiveResult}
                />
              </div>
            </div>

            {results.length > 1 && (
              <BatchSummaryTable
                results={results}
                activeIndex={activeResultIndex}
                onSelectResult={handleChangeActiveResult}
              />
            )}

            {activeResult && (
              <div className="flex flex-col gap-4">
                
                <RecommendationOptionCards 
                  options={recommendationOptions} 
                  activeIndex={activeOptionIndex} 
                  onChange={setActiveOptionIndex} 
                />
                
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

                {combinedResultForGraph?.forecast_summary && (
                  <ForecastSummaryDetail forecastSummary={combinedResultForGraph.forecast_summary} />
                )}

                {/* PCF Analysis Panel with Pie Chart and Offset Calculator */}
                {selectedOption && (() => {
                  // Aggregate pcf_stage_breakdown from all tree nodes into one
                  // flat breakdown object that PcfPieChart expects.
                  // Backend stores per-node breakdown in tree[i].pcf_stage_breakdown.
                  const tree = selectedOption.tree || []
                  const aggregated = {
                    stage1_harvest_emission_kg_co2e: 0,
                    stage2_transport_estate_to_mill_kg_co2e: 0,
                    stage3_mill_processing_emission_kg_co2e: 0,
                    stage4_transport_mill_to_refinery_kg_co2e: 0,
                    stage5_refinery_processing_emission_kg_co2e: 0,
                    total_kg_co2e: 0,
                    pcf_per_unit_kg_co2e_per_kg: 0,
                  }

                  let hasRealData = false
                  tree.forEach(node => {
                    const bd = node?.pcf_stage_breakdown
                    if (!bd) return
                    hasRealData = true
                    aggregated.stage1_harvest_emission_kg_co2e            += bd.stage1_harvest_emission_kg_co2e || 0
                    aggregated.stage2_transport_estate_to_mill_kg_co2e    += bd.stage2_transport_estate_to_mill_kg_co2e || 0
                    aggregated.stage3_mill_processing_emission_kg_co2e    += bd.stage3_mill_processing_emission_kg_co2e || 0
                    aggregated.stage4_transport_mill_to_refinery_kg_co2e  += bd.stage4_transport_mill_to_refinery_kg_co2e || 0
                    aggregated.stage5_refinery_processing_emission_kg_co2e += bd.stage5_refinery_processing_emission_kg_co2e || 0
                    aggregated.total_kg_co2e                               += bd.total_pcf_kg_co2e || 0
                  })

                  const totalQty = activeResult?.quantity || 1
                  aggregated.pcf_per_unit_kg_co2e_per_kg =
                    aggregated.total_kg_co2e > 0 ? aggregated.total_kg_co2e / totalQty : 0

                  // Round all values for display
                  Object.keys(aggregated).forEach(k => {
                    aggregated[k] = Math.round(aggregated[k] * 10000) / 10000
                  })

                  // Only show panel if there is real PCF data from the backend
                  if (!hasRealData) return null

                  const optionWithPcf = {
                    ...selectedOption,
                    pcf_breakdown: aggregated,
                    pcf_per_unit_kg_co2e: aggregated.pcf_per_unit_kg_co2e_per_kg,
                  }

                  return (
                    <PcfAnalysisPanel
                      recommendationOption={optionWithPcf}
                      buyerMaxPcf={null}
                      productVolume={totalQty}
                    />
                  )
                })()}

                <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
                  <StockAllocationSummary orderResult={activeResult} />

                  <div className="border-t border-gray-100">
                    {activeResult?.stock_overview?.summary?.stock_status === "FULLY_FULFILLED" ? (
                      <div className="rounded-2xl border border-green-200 bg-green-50 px-6 py-8 text-center m-4">
                        <p className="text-2xl mb-3">✅</p>
                        <h3 className="text-base font-bold text-green-800">No Upstream Routing Required</h3>
                        <p className="mt-2 text-sm text-green-700 leading-relaxed">
                          This order is fully satisfied from existing stock at{" "}
                          <span className="font-bold">{activeResult?.facility || "—"}</span>.
                        </p>
                        <p className="mt-1 text-sm text-green-700">
                          {formatKg(activeResult?.stock_overview?.summary?.fulfilled_from_stock)} Kg allocated from{" "}
                          {(activeResult?.stock_overview?.selected_slocs || []).length} SLOC
                          {(activeResult?.stock_overview?.selected_slocs || []).length !== 1 ? "s" : ""}.
                        </p>
                        <p className="mt-2 text-sm text-green-600">
                          No inbound supply chain movement is needed for this order.
                        </p>
                      </div>
                    ) : (
                      <SupplyGraph orderResult={combinedResultForGraph} />
                    )}
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
