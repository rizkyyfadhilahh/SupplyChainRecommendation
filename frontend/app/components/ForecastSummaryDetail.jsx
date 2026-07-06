function ConfidenceBadge({ pathSummaries }) {
  if (!pathSummaries || pathSummaries.length === 0) return null
  // Derive confidence from path count — more paths = more data
  const count = pathSummaries.length
  const { label, color } = count >= 5
    ? { label: "High Confidence", color: "bg-green-100 text-green-700 border-green-200" }
    : count >= 2
    ? { label: "Medium Confidence", color: "bg-yellow-100 text-yellow-700 border-yellow-200" }
    : { label: "Low Confidence", color: "bg-orange-100 text-orange-700 border-orange-200" }
  return (
    <span
      title={`Based on ${count} supply path${count !== 1 ? "s" : ""} from historical data`}
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${color}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label} · {count} path{count !== 1 ? "s" : ""}
    </span>
  )
}

export default function ForecastSummaryDetail({ forecastSummary }) {
  if (!forecastSummary) return null

  const allocatedRoot = Number(forecastSummary.allocated_root_qty || 0)
  const unallocatedRoot = Number(forecastSummary.unallocated_root_qty || 0)
  const fillRate = Number(forecastSummary.allocation_fulfillment_rate || 0)
  const totalDays = forecastSummary.total_estimated_days
  const scheduleStart = forecastSummary.schedule_start_date
  const batchCompletion = forecastSummary.batch_completion_date
  const pathSummaries = forecastSummary.path_summaries || []

  const hasMeaningfulData =
    allocatedRoot > 0 || unallocatedRoot > 0 || fillRate > 0 || totalDays != null

  if (!hasMeaningfulData) return null

  function formatDateReadable(dateStr) {
    if (!dateStr) return null
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <p className="text-sm font-bold text-gray-900">📋 Routing Summary</p>
        <ConfidenceBadge pathSummaries={pathSummaries} />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-wide text-blue-500">Allocated from Upstream</p>
          <p className="mt-1 text-sm font-bold text-blue-900">
            {allocatedRoot.toLocaleString()} Kg
          </p>
        </div>

        <div className={`rounded-xl border px-4 py-2.5 ${unallocatedRoot > 0 ? "border-red-100 bg-red-50" : "border-green-100 bg-green-50"}`}>
          <p className={`text-[10px] font-bold uppercase tracking-wide ${unallocatedRoot > 0 ? "text-red-500" : "text-green-500"}`}>
            Unallocated Gap
          </p>
          <p className={`mt-1 text-sm font-bold ${unallocatedRoot > 0 ? "text-red-900" : "text-green-900"}`}>
            {unallocatedRoot > 0 ? `${unallocatedRoot.toLocaleString()} Kg` : "Fully Allocated"}
          </p>
        </div>

        <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">Route Fill Rate</p>
          <p className="mt-1 text-sm font-bold text-gray-900">
            {(fillRate * 100).toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%
          </p>
        </div>

        {totalDays != null && (
          <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-2.5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">Est. Lead Time</p>
            <p className="mt-1 text-sm font-bold text-gray-900">{totalDays} days</p>
          </div>
        )}

        {scheduleStart && formatDateReadable(scheduleStart) && (
          <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-2.5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">Dispatch Date</p>
            <p className="mt-1 text-sm font-bold text-gray-900">{formatDateReadable(scheduleStart)}</p>
          </div>
        )}

        {batchCompletion && formatDateReadable(batchCompletion) && (
          <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-2.5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">Est. Arrival</p>
            <p className="mt-1 text-sm font-bold text-gray-900">{formatDateReadable(batchCompletion)}</p>
          </div>
        )}
      </div>
    </div>
  )
}
