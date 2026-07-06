"use client"

import { useRef } from "react"

/* ─── Helpers ─────────────────────────────────────────── */
function fmt(n, decimals = 0) {
  const num = Number(n || 0)
  if (!Number.isFinite(num)) return "0"
  return num.toLocaleString("id-ID", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function fmtDate(dateStr) {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

function addDays(days) {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

function today() {
  return new Date().toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

/* ─── Section Header ──────────────────────────────────── */
function SectionHeader({ label }) {
  return (
    <div className="offer-section-header">
      <span>{label}</span>
    </div>
  )
}

/* ─── Info Row ────────────────────────────────────────── */
function InfoRow({ label, value, accent }) {
  return (
    <div className="offer-info-row">
      <span className="offer-info-label">{label}</span>
      <span className={`offer-info-value${accent ? " offer-accent" : ""}`}>{value || "—"}</span>
    </div>
  )
}

/* ─── Stat Card ───────────────────────────────────────── */
function StatCard({ label, value, sub, color = "default" }) {
  const colorClass = {
    green: "offer-stat-green",
    red: "offer-stat-red",
    blue: "offer-stat-blue",
    default: "offer-stat-default",
  }[color] || "offer-stat-default"

  return (
    <div className={`offer-stat-card ${colorClass}`}>
      <div className="offer-stat-label">{label}</div>
      <div className="offer-stat-value">{value}</div>
      {sub && <div className="offer-stat-sub">{sub}</div>}
    </div>
  )
}

/* ─── Main Component ──────────────────────────────────── */
export default function TradeOfferGenerator({ orderResult, selectedOption, onClose }) {
  const printRef = useRef(null)

  if (!orderResult) return null

  /* Extract data */
  const stockOverview = orderResult.stock_overview || {}
  const stockSummary = stockOverview.summary || {}
  const forecastSummary = selectedOption?.forecast_summary || {}
  const tree = selectedOption?.tree || []

  const buyer = orderResult.buyer || "—"
  const facility = orderResult.facility || "—"
  const product = orderResult.product || "—"
  const spec = orderResult.spec || "ALL"
  const quantityKg = Number(orderResult.quantity || 0)
  const quantityMt = quantityKg / 1000

  const fulfilledFromStock = Number(stockSummary.fulfilled_from_stock || 0)
  const unmetDemand = Number(stockSummary.unmet_demand || 0)
  const stockStatus = stockSummary.stock_status || "NOT_FULFILLED"
  const allocatedFromUpstream = Number(forecastSummary.allocated_root_qty || 0)
  const unallocatedGap = Number(forecastSummary.unallocated_root_qty || 0)
  const fillRate = Number(forecastSummary.allocation_fulfillment_rate || 0)

  const totalDays = forecastSummary.total_estimated_days
  const scheduleStart = forecastSummary.schedule_start_date
  const arrival = forecastSummary.schedule_arrival_date || forecastSummary.batch_completion_date

  const pcfPerUnit = Number(orderResult.pcf_per_unit_kg_co2e || 0)
  const pcfTotal = Number(orderResult.total_pcf_kg_co2e || 0)
  const pcfPerTon = pcfPerUnit
  const pcfTotalTon = pcfTotal / 1000
  const hasPcf = pcfPerUnit > 0
  const PCF_BENCHMARK = 2.5

  const enableTolling = orderResult.enable_tolling
  const tracePolicy = selectedOption?.trace_policy || {}

  /* Build route rows — group by level, only top 12 rows */
  const routeRows = tree
    .slice()
    .sort((a, b) => Number(a.level) - Number(b.level))
    .slice(0, 12)

  /* Fulfillment bar */
  const totalDemand = fulfilledFromStock + unmetDemand
  const stockPct = totalDemand > 0 ? (fulfilledFromStock / totalDemand) * 100 : 0
  const upstreamPct = totalDemand > 0 ? Math.min((allocatedFromUpstream / totalDemand) * 100, 100 - stockPct) : 0

  /* Handle print */
  const handlePrint = () => {
    window.print()
  }

  return (
    <>
      {/* ── Backdrop ─────────────────────────────────── */}
      <div
        className="fixed inset-0 z-[9998] bg-black/60 backdrop-blur-sm flex items-start justify-center overflow-y-auto py-6 px-4 no-print"
        onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      >
        {/* ── Modal Shell ──────────────────────────── */}
        <div className="relative w-full max-w-3xl">
          {/* Toolbar */}
          <div className="no-print flex items-center justify-between mb-4 px-1">
            <div>
              <h2 className="text-white font-bold text-lg">Trade Offer Preview</h2>
              <p className="text-white/60 text-xs mt-0.5">Review before printing or saving as PDF</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handlePrint}
                className="flex items-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 px-5 py-2.5 text-sm font-bold text-white shadow-lg transition"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Print / Save as PDF
              </button>
              <button
                onClick={onClose}
                className="rounded-xl border border-white/20 bg-white/10 hover:bg-white/20 px-4 py-2.5 text-sm font-bold text-white transition"
              >
                Close
              </button>
            </div>
          </div>

          {/* ── Document ─────────────────────────── */}
          <div ref={printRef} className="offer-document bg-white rounded-2xl overflow-hidden shadow-2xl">

            {/* Header */}
            <div className="offer-header">
              <div className="offer-header-left">
                <div className="offer-brand">PALM OIL SUPPLY</div>
                <div className="offer-doc-title">TRADE OFFER</div>
              </div>
              <div className="offer-header-right">
                <div className="offer-meta-row">
                  <span className="offer-meta-label">Document Date</span>
                  <span className="offer-meta-value">{today()}</span>
                </div>
                <div className="offer-meta-row">
                  <span className="offer-meta-label">Valid Until</span>
                  <span className="offer-meta-value offer-validity">{addDays(3)}</span>
                </div>
                <div className="offer-meta-row">
                  <span className="offer-meta-label">Reference</span>
                  <span className="offer-meta-value">SCR-{Date.now().toString().slice(-6)}</span>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="offer-divider" />

            {/* Order Identity */}
            <div className="offer-body">
              <SectionHeader label="ORDER DETAILS" />
              <div className="offer-grid-2">
                <InfoRow label="Buyer" value={buyer} accent />
                <InfoRow label="Refinery" value={facility} accent />
                <InfoRow label="Product" value={product} />
                <InfoRow label="Volume" value={`${fmt(quantityKg)} Kg  (${fmt(quantityMt, 2)} MT)`} accent />
                <InfoRow label="Specification" value={spec} />
                <InfoRow
                  label="Fulfillment Status"
                  value={
                    stockStatus === "FULLY_FULFILLED" ? "✅ Fully Fulfilled from Stock" :
                    stockStatus === "PARTIALLY_FULFILLED" ? "⚡ Partially from Stock + Upstream" :
                    "🔄 Fully from Upstream Route"
                  }
                />
              </div>

              {/* Fulfillment bar */}
              <div className="offer-bar-section">
                <div className="offer-bar-track">
                  <div className="offer-bar-fill offer-bar-green" style={{ width: `${stockPct}%` }} />
                  <div className="offer-bar-fill offer-bar-blue" style={{ width: `${upstreamPct}%` }} />
                </div>
                <div className="offer-bar-legend">
                  <span><span className="offer-dot green" />From Stock: {fmt(fulfilledFromStock)} Kg ({fmt(stockPct, 1)}%)</span>
                  <span><span className="offer-dot blue" />From Upstream: {fmt(allocatedFromUpstream)} Kg</span>
                  {unallocatedGap > 0 && (
                    <span className="offer-gap-warning"><span className="offer-dot red" />Unallocated Gap: {fmt(unallocatedGap)} Kg</span>
                  )}
                </div>
              </div>

              {/* Stats row */}
              <div className="offer-stats-grid">
                <StatCard
                  label="From Stock"
                  value={`${fmt(fulfilledFromStock)} Kg`}
                  sub={`${fmt(stockPct, 1)}% of demand`}
                  color={fulfilledFromStock > 0 ? "green" : "default"}
                />
                <StatCard
                  label="From Upstream"
                  value={`${fmt(allocatedFromUpstream)} Kg`}
                  sub={`Route fill rate: ${fmt(fillRate * 100, 1)}%`}
                  color="blue"
                />
                <StatCard
                  label="Unallocated Gap"
                  value={unallocatedGap > 0 ? `${fmt(unallocatedGap)} Kg` : "None"}
                  color={unallocatedGap > 0 ? "red" : "green"}
                />
              </div>

              {/* Schedule */}
              <SectionHeader label="DELIVERY SCHEDULE" />
              <div className="offer-grid-3">
                <StatCard
                  label="Est. Lead Time"
                  value={totalDays != null ? `${totalDays} days` : "—"}
                  color="blue"
                />
                <StatCard
                  label="Dispatch Start"
                  value={fmtDate(scheduleStart)}
                />
                <StatCard
                  label="Est. Arrival"
                  value={fmtDate(arrival)}
                  color={arrival ? "green" : "default"}
                />
              </div>

              {forecastSummary.target_total_days_message && (
                <div className={`offer-target-msg ${forecastSummary.target_total_days_met ? "offer-target-ok" : "offer-target-warn"}`}>
                  {forecastSummary.target_total_days_met ? "✅" : "⚠️"} {forecastSummary.target_total_days_message}
                </div>
              )}

              {/* Supply chain route */}
              {routeRows.length > 0 && (
                <>
                  <SectionHeader label="SUPPLY CHAIN ROUTE" />
                  <table className="offer-table">
                    <thead>
                      <tr>
                        <th>Level</th>
                        <th>Supplier</th>
                        <th>Type</th>
                        <th>Product</th>
                        <th className="text-right">Quantity (Kg)</th>
                        <th className="text-right">Lead Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {routeRows.map((row, i) => {
                        const level = Number(row.level || 0)
                        const typeColors = {
                          MILL: "offer-badge-blue",
                          ESTATE: "offer-badge-green",
                          VENDOR: "offer-badge-orange",
                          REFINERY: "offer-badge-purple",
                        }
                        const typeColor = typeColors[row.supplier_type] || "offer-badge-gray"
                        return (
                          <tr key={i} className={level === 0 ? "offer-row-root" : ""}>
                            <td>
                              <span className="offer-level-badge">L{level}</span>
                            </td>
                            <td className="offer-supplier-name">{row.supplier_name || row.supplier_id || "—"}</td>
                            <td>
                              <span className={`offer-badge ${typeColor}`}>
                                {row.supplier_type || "—"}
                              </span>
                            </td>
                            <td>{row.product || "—"}</td>
                            <td className="text-right font-semibold">{fmt(row.quantity)}</td>
                            <td className="text-right">
                              {row.estimated_days > 0 ? `${row.estimated_days}d` : "—"}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  {tree.length > 12 && (
                    <p className="offer-truncate-note">
                      … and {tree.length - 12} more nodes not shown in this summary.
                    </p>
                  )}
                </>
              )}

              {/* Sustainability */}
              <SectionHeader label="SUSTAINABILITY & COMPLIANCE" />
              <div className="offer-grid-2">
                {hasPcf ? (
                  <>
                    <InfoRow
                      label="PCF Intensity"
                      value={`${pcfPerTon.toFixed(4)} tCO₂e / ton`}
                      accent
                    />
                    <InfoRow
                      label="Total Carbon Footprint"
                      value={`${pcfTotalTon.toFixed(3)} tCO₂e`}
                    />
                    <InfoRow
                      label="vs. Benchmark (2.5)"
                      value={pcfPerTon < PCF_BENCHMARK ? "✅ Below benchmark" : "⚠️ Above benchmark"}
                      accent={pcfPerTon < PCF_BENCHMARK}
                    />
                  </>
                ) : (
                  <InfoRow label="Carbon Footprint (PCF)" value="Not calculated for this route" />
                )}
                <InfoRow
                  label="EUDR Specification"
                  value={spec === "EUDR" ? "✅ EUDR Compliant" : "Non-EUDR (ALL spec)"}
                />
                {tracePolicy.tolling_used && (
                  <InfoRow label="CPO Tolling" value="✅ Tolling route used (961→601)" />
                )}
                {tracePolicy.terminal_vendor_used && (
                  <InfoRow label="Terminal Vendor" value="⚡ Third-party vendor included" />
                )}
              </div>

              {/* Footer notice */}
              <div className="offer-footer-notice">
                <p>
                  <strong>IMPORTANT:</strong> This offer is system-generated based on historical supply chain data
                  (3-month transaction records). Volume allocations, lead times, and supplier routes are recommendations
                  only and subject to final confirmation by the refinery operations team.
                </p>
                <p className="mt-1">
                  Specification: <strong>{spec}</strong> &nbsp;|&nbsp;
                  Generated: <strong>{today()}</strong> &nbsp;|&nbsp;
                  Valid Until: <strong>{addDays(3)}</strong>
                </p>
              </div>
            </div>
          </div>

          {/* Bottom close */}
          <div className="no-print mt-4 text-center">
            <button
              onClick={onClose}
              className="text-white/50 hover:text-white text-sm transition"
            >
              ✕ Close Preview
            </button>
          </div>
        </div>
      </div>

      {/* ── Styles ─────────────────────────────────────── */}
      <style jsx global>{`
        /* ── Print isolation ── */
        @media print {
          body > * { display: none !important; }
          .offer-document { display: block !important; }
          .no-print { display: none !important; }
          @page { margin: 18mm 15mm; size: A4; }
        }

        /* ── Document shell ── */
        .offer-document {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          font-size: 13px;
          color: #111827;
          line-height: 1.5;
        }

        /* ── Header ── */
        .offer-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          padding: 28px 32px 20px;
          background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
          color: white;
        }
        .offer-brand {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: rgba(255,255,255,0.55);
          margin-bottom: 6px;
        }
        .offer-doc-title {
          font-size: 26px;
          font-weight: 800;
          letter-spacing: -0.5px;
          color: #fff;
        }
        .offer-header-right {
          text-align: right;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .offer-meta-row {
          display: flex;
          gap: 10px;
          align-items: baseline;
          justify-content: flex-end;
        }
        .offer-meta-label {
          font-size: 10px;
          color: rgba(255,255,255,0.5);
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .offer-meta-value {
          font-size: 12px;
          color: rgba(255,255,255,0.9);
          font-weight: 600;
        }
        .offer-validity {
          color: #86efac;
          font-weight: 700;
        }

        /* ── Divider ── */
        .offer-divider { height: 4px; background: linear-gradient(90deg, #3b82f6, #10b981, #f59e0b); }

        /* ── Body ── */
        .offer-body { padding: 24px 32px 28px; display: flex; flex-direction: column; gap: 14px; }

        /* ── Section header ── */
        .offer-section-header {
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: #6b7280;
          padding-bottom: 6px;
          border-bottom: 1.5px solid #e5e7eb;
          margin-top: 6px;
        }

        /* ── Info rows ── */
        .offer-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 20px; }
        .offer-info-row { display: flex; flex-direction: column; gap: 1px; padding: 6px 0; border-bottom: 1px solid #f3f4f6; }
        .offer-info-label { font-size: 10px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.06em; }
        .offer-info-value { font-size: 13px; font-weight: 500; color: #1f2937; }
        .offer-accent { font-weight: 700; color: #111827; }

        /* ── Fulfillment bar ── */
        .offer-bar-section { background: #f9fafb; border-radius: 10px; padding: 12px 14px; }
        .offer-bar-track { height: 10px; border-radius: 99px; background: #e5e7eb; overflow: hidden; display: flex; }
        .offer-bar-fill { height: 100%; transition: width 0.3s; }
        .offer-bar-green { background: #22c55e; }
        .offer-bar-blue { background: #3b82f6; }
        .offer-bar-legend { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 8px; font-size: 11px; color: #6b7280; font-weight: 500; }
        .offer-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
        .offer-dot.green { background: #22c55e; }
        .offer-dot.blue { background: #3b82f6; }
        .offer-dot.red { background: #ef4444; }
        .offer-gap-warning { color: #dc2626; font-weight: 700; }

        /* ── Stat cards ── */
        .offer-stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .offer-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .offer-stat-card { border-radius: 10px; padding: 12px 14px; border: 1px solid; }
        .offer-stat-green { background: #f0fdf4; border-color: #bbf7d0; }
        .offer-stat-red { background: #fef2f2; border-color: #fecaca; }
        .offer-stat-blue { background: #eff6ff; border-color: #bfdbfe; }
        .offer-stat-default { background: #f9fafb; border-color: #e5e7eb; }
        .offer-stat-label { font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.06em; }
        .offer-stat-value { font-size: 14px; font-weight: 800; color: #111827; margin-top: 3px; }
        .offer-stat-sub { font-size: 10px; color: #9ca3af; margin-top: 2px; }

        /* ── Target message ── */
        .offer-target-msg { border-radius: 8px; padding: 10px 14px; font-size: 12px; font-weight: 500; }
        .offer-target-ok { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
        .offer-target-warn { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }

        /* ── Route table ── */
        .offer-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .offer-table thead tr { background: #f9fafb; }
        .offer-table th { text-align: left; padding: 8px 10px; font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1.5px solid #e5e7eb; }
        .offer-table td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; color: #374151; }
        .offer-row-root td { background: #eff6ff; font-weight: 600; }
        .offer-level-badge { font-size: 10px; font-weight: 700; background: #e5e7eb; color: #374151; padding: 2px 6px; border-radius: 4px; }
        .offer-supplier-name { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; color: #111827; }
        .offer-badge { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 99px; letter-spacing: 0.04em; }
        .offer-badge-blue { background: #dbeafe; color: #1d4ed8; }
        .offer-badge-green { background: #dcfce7; color: #15803d; }
        .offer-badge-orange { background: #ffedd5; color: #c2410c; }
        .offer-badge-purple { background: #ede9fe; color: #6d28d9; }
        .offer-badge-gray { background: #f3f4f6; color: #374151; }
        .offer-truncate-note { font-size: 11px; color: #9ca3af; font-style: italic; padding: 6px 0; }

        /* ── Footer notice ── */
        .offer-footer-notice {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          padding: 14px 16px;
          font-size: 11px;
          color: #6b7280;
          line-height: 1.6;
          margin-top: 6px;
        }
        .offer-footer-notice strong { color: #374151; }
      `}</style>
    </>
  )
}
