import React from "react"
import { getEstimatedFormula, hasQueueSchedule, toDisplayDays, toDisplayDate, toDisplayNumber } from "./utils"
import { CalculationMetricCard } from "./ui"
import PcfNodePanel from "./PcfNodePanel"

export default function CalculationDetailCard({ row, isRefinerySelected, getDestinationName }) {
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
            {Number(row?.pcf_per_unit || 0) > 0 && (
              <span className="flex items-center gap-1 rounded-md border border-green-200 bg-green-50 px-2.5 py-1 text-[11px] font-bold text-green-700 shadow-sm">
                🌱 PCF {Number(row.pcf_per_unit).toFixed(4)} kg/kg
              </span>
            )}
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

        {/* 3. PCF Stage Breakdown Panel */}
        <PcfNodePanel row={row} />

        {/* 4. Highlight/Takeaway Callout */}
        <div className="mt-5 flex items-start gap-3 rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50/50 to-transparent px-4 py-3.5">
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
