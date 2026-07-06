import { useMemo } from "react"
import { detectConflicts } from "../utils"

export default function BatchSummaryTable({ results, activeIndex, onSelectResult }) {
  if (!results || results.length <= 1) return null

  const conflicts = useMemo(() => detectConflicts(results), [results])

  function getStatusBadge(status) {
    const s = String(status || "").toUpperCase()
    if (s === "FULLY_FULFILLED")
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-[10px] font-bold text-green-700">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Fully Fulfilled
        </span>
      )
    if (s === "PARTIALLY_FULFILLED")
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-yellow-200 bg-yellow-50 px-2 py-0.5 text-[10px] font-bold text-yellow-700">
          <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
          Partial
        </span>
      )
    if (s === "NOT_FULFILLED")
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[10px] font-bold text-red-700">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          Not Fulfilled
        </span>
      )
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[10px] font-bold text-gray-600">
        {s || "—"}
      </span>
    )
  }

  function formatDateReadable(dateStr) {
    if (!dateStr) return "—"
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const PCF_BENCHMARK = 2.5

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-5 py-4">
        <h2 className="text-sm font-bold text-gray-900">Batch Overview</h2>
        <p className="mt-0.5 text-xs text-gray-400">Click any order to inspect details.</p>
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-xs">
          <thead className="sticky top-0 z-10 bg-gray-50">
            <tr>
              {["Order #", "Refinery", "Product", "Status", "Fulfilled (Kg)", "Unmet (Kg)", "PCF (tCO₂e/t)", "Est. Days", "Completion Date", "Conflict Risk"].map((col) => (
                <th
                  key={col}
                  className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-gray-400 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {results.map((result, idx) => {
              const summary = result?.stock_overview?.summary || {}
              const firstOpt = result?.recommendation_options?.[0] || {}
              const forecastSummary = firstOpt?.forecast_summary || {}
              const pcfPerUnit = Number(result?.pcf_per_unit_kg_co2e || 0)
              const hasPcf = pcfPerUnit > 0
              const aboveBenchmark = hasPcf && pcfPerUnit >= PCF_BENCHMARK
              const isActive = idx === activeIndex
              return (
                <tr
                  key={idx}
                  onClick={() => onSelectResult(idx)}
                  className={`cursor-pointer transition ${isActive ? "bg-blue-50" : "hover:bg-gray-50"}`}
                >
                  <td className="px-4 py-3 font-bold text-gray-900 whitespace-nowrap">
                    #{result?.order_index ?? idx + 1}
                  </td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                    {result?.facility || "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                    {result?.product || "—"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {getStatusBadge(summary.stock_status)}
                  </td>
                  <td className="px-4 py-3 text-gray-800 font-semibold whitespace-nowrap">
                    {Number(summary.fulfilled_from_stock || 0).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-800 font-semibold whitespace-nowrap">
                    {Number(summary.unmet_demand || 0).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {hasPcf ? (
                      <span className={`font-semibold ${aboveBenchmark ? "text-orange-600" : "text-green-700"}`}>
                        {aboveBenchmark ? "⚠ " : "✓ "}{pcfPerUnit.toFixed(3)}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                    {forecastSummary.total_estimated_days ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                    {formatDateReadable(forecastSummary.batch_completion_date)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {conflicts.has(idx) ? (
                      <span className="inline-flex items-center gap-1 rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-[10px] font-bold text-orange-700">
                        ⚠ High Risk
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
