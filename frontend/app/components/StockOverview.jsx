"use client"

function formatNumber(value) {
  const num = Number(value || 0)

  if (!Number.isFinite(num)) return "0"

  return num.toLocaleString("id-ID", {
    maximumFractionDigits: 2,
  })
}

function getStatusMeta(status = "") {
  const value = String(status || "UNKNOWN").toUpperCase()

  if (value === "FULLY_FULFILLED") {
    return {
      label: "Fully Fulfilled",
      className: "border-green-200 bg-green-50 text-green-700",
      dotClassName: "bg-green-500",
    }
  }

  if (value === "PARTIALLY_FULFILLED") {
    return {
      label: "Partially Fulfilled",
      className: "border-yellow-200 bg-yellow-50 text-yellow-700",
      dotClassName: "bg-yellow-500",
    }
  }

  if (value === "NOT_FULFILLED") {
    return {
      label: "Not Fulfilled",
      className: "border-red-200 bg-red-50 text-red-700",
      dotClassName: "bg-red-500",
    }
  }

  return {
    label: value,
    className: "border-gray-200 bg-gray-50 text-gray-700",
    dotClassName: "bg-gray-400",
  }
}

function StatusBadge({ status }) {
  const meta = getStatusMeta(status)

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-bold ${meta.className}`}
    >
      <span className={`h-2 w-2 rounded-full ${meta.dotClassName}`} />
      {meta.label}
    </span>
  )
}

function MetricCard({ label, value, suffix = "", tone = "default", helper }) {
  const toneClass =
    tone === "blue"
      ? "border-blue-100 bg-blue-50"
      : tone === "green"
      ? "border-green-100 bg-green-50"
      : tone === "red"
      ? "border-red-100 bg-red-50"
      : "border-gray-100 bg-gray-50"

  const valueClass =
    tone === "blue"
      ? "text-blue-900"
      : tone === "green"
      ? "text-green-900"
      : tone === "red"
      ? "text-red-900"
      : "text-gray-900"

  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClass}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">
        {label}
      </p>

      <p className={`mt-1 text-base font-bold ${valueClass}`}>
        {value}
        {suffix ? <span className="ml-1 text-xs font-semibold">{suffix}</span> : null}
      </p>

      {helper && (
        <p className="mt-1 text-[11px] font-medium text-gray-400">
          {helper}
        </p>
      )}
    </div>
  )
}

function InfoCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-white px-4 py-3">
      <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">
        {label}
      </p>

      <p className="mt-1 text-sm font-bold text-gray-900">
        {value || "-"}
      </p>
    </div>
  )
}

function EmptyTableState({ message }) {
  return (
    <div className="px-6 py-10 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-50 text-lg">
        —
      </div>

      <p className="mt-3 text-sm font-semibold text-gray-500">
        {message}
      </p>
    </div>
  )
}

function SectionTable({ title, rows, emptyMessage, description }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white">
      <div className="border-b border-gray-100 px-6 py-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-sm font-bold text-gray-900">
              {title}
            </h3>

            {description && (
              <p className="mt-1 text-xs text-gray-400">
                {description}
              </p>
            )}
          </div>

          <span className="w-fit rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-bold text-gray-500">
            {rows?.length || 0} row{rows?.length === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      {rows?.length ? (
        <div className="max-h-[300px] overflow-auto">
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 z-10 bg-gray-50 text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wide text-gray-500">
                  Plant
                </th>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wide text-gray-500">
                  SLOC
                </th>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wide text-gray-500">
                  Commodity
                </th>
                <th className="px-4 py-3 text-right font-bold uppercase tracking-wide text-gray-500">
                  Stock Before
                </th>
                <th className="px-4 py-3 text-right font-bold uppercase tracking-wide text-gray-500">
                  Allocated
                </th>
                <th className="px-4 py-3 text-left font-bold uppercase tracking-wide text-gray-500">
                  Reason
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-100">
              {rows.map((row, i) => (
                <tr key={i} className="text-gray-700 transition hover:bg-gray-50">
                  <td className="px-4 py-3 align-top">
                    <p className="font-bold text-gray-900">
                      {row.name1 || "-"}
                    </p>
                    <p className="mt-0.5 text-[11px] font-medium text-gray-400">
                      ID: {row.plant || "-"}
                    </p>
                  </td>

                  <td className="px-4 py-3 align-top">
                    <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-bold text-gray-700">
                      {row.storage_location || "-"}
                    </span>
                  </td>

                  <td className="px-4 py-3 align-top">
                    <span className="inline-flex rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700">
                      {row.material_description || "-"}
                    </span>
                  </td>

                  <td className="px-4 py-3 text-right align-top font-semibold text-gray-800 whitespace-nowrap">
                    {formatNumber(row.stock_before)}
                  </td>

                  <td className="px-4 py-3 text-right align-top font-bold text-gray-900 whitespace-nowrap">
                    {formatNumber(row.allocated_qty)}
                  </td>

                  <td className="px-4 py-3 align-top">
                    <p className="min-w-[240px] text-xs leading-relaxed text-gray-500">
                      {row.eligibility_reason || "-"}
                    </p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyTableState message={emptyMessage} />
      )}
    </div>
  )
}

export default function StockOverview({ orderResult }) {
  const stockOverview = orderResult?.stock_overview || {}
  const summary = stockOverview?.summary || {}
  const basis = stockOverview?.stock_check_basis || {}

  const stockSnapshotMaxDate = orderResult?.max_date || "-"
  const selected = stockOverview?.selected_slocs || []
  const eligibleUnused = stockOverview?.eligible_but_unused_slocs || []
  const ineligible = stockOverview?.ineligible_slocs || []

  const requestedProduct = basis.requested_product || orderResult?.product || "-"
  const requestedRefinery = basis.refinery_group || orderResult?.facility || "-"
  const requestDate = basis.request_date || "-"
  const status = summary.stock_status || "UNKNOWN"

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white">
        <div className="border-b border-gray-100 bg-gradient-to-br from-white to-gray-50 px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-bold text-gray-900">
                  Stock & SLOC Details
                </h2>

                <StatusBadge status={status} />
              </div>

              <p className="mt-1 text-sm text-gray-500">
                Current stock snapshot and SLOC allocation details for the selected order.
              </p>
            </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-blue-100 bg-blue-50 px-3 py-3">
              <p className="text-[9px] font-bold uppercase tracking-wide text-blue-500">
                Total Stock
              </p>
              <p className="mt-1 text-sm font-bold text-blue-900">
                {formatNumber(summary.total_stock_before_allocation)} Kg
              </p>
            </div>

            <div className="rounded-2xl border border-gray-100 bg-white px-4 py-3">
              <p className="text-[9px] font-bold uppercase tracking-wide text-gray-400">
                Stock As Per
              </p>
              <p className="mt-1 text-sm font-bold text-gray-900">
                {stockSnapshotMaxDate}
              </p>
            </div>
          </div>
          </div>
        </div>

        <div className="px-2 py-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <InfoCard label="Requested Product" value={requestedProduct} />
            <InfoCard label="Requested Refinery" value={requestedRefinery} />
            <InfoCard label="Request Date" value={requestDate} />
          </div>
        </div>
      </div>

      <SectionTable
        title="Selected SLOCs"
        description="SLOCs used to fulfill stock allocation for this order."
        rows={selected}
        emptyMessage="No SLOC was selected for stock allocation."
      />
    </div>
  )
}
