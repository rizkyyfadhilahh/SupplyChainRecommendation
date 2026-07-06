"use client"

import { useState, useEffect, useRef, useMemo } from "react"
import { useSearchParams } from "next/navigation"
import SupplyGraph from "./SupplyGraph"
import BlastRadiusPanel from "./drilldown/BlastRadiusPanel"

/* ─────────────────────────────────────────────────────────────────
   Formatters  (match page.jsx conventions exactly)
   ───────────────────────────────────────────────────────────────── */
const fmtKg = v => Number.isFinite(Number(v)) ? Number(v).toLocaleString("id-ID", { maximumFractionDigits: 0 }) + " Kg" : "0 Kg"
const fmtMT = v => Number.isFinite(Number(v)) ? Number(v).toLocaleString("id-ID", { maximumFractionDigits: 0 }) + " MT" : "0 MT"
const fmtNum = (v, d = 2) => Number.isFinite(Number(v)) ? Number(v).toFixed(d) : "0"
const fmtPct = v => fmtNum(v, 1) + "%"
const fmtDate = s => { try { return new Date(s).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) } catch { return s } }

/* ─────────────────────────────────────────────────────────────────
   Shared primitives — match existing app style (rounded-2xl, shadow-sm,
   border-gray-100, rose-500 primary, gray-50 bg)
   ───────────────────────────────────────────────────────────────── */
function Card({ children, className = "", style }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden ${className}`} style={style}>
      {children}
    </div>
  )
}
function CardHeader({ title, subtitle, icon, right }) {
  return (
    <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        {icon && <span className="text-xl">{icon}</span>}
        <div>
          <h3 className="text-sm font-bold text-gray-900">{title}</h3>
          {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
  )
}
function Badge({ children, color = "gray" }) {
  const cls = {
    green: "bg-green-50  border-green-200  text-green-700",
    red: "bg-red-50    border-red-200    text-red-700",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
    orange: "bg-orange-50 border-orange-200 text-orange-700",
    blue: "bg-blue-50   border-blue-200   text-blue-700",
    purple: "bg-purple-50 border-purple-200 text-purple-700",
    gray: "bg-gray-100  border-gray-200   text-gray-600",
  }[color] || "bg-gray-100 border-gray-200 text-gray-600"
  return (
    <span className={`inline-flex items-center border rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap ${cls}`}>
      {children}
    </span>
  )
}
function KpiCell({ label, value, sub, bg = "bg-gray-50 border-gray-100" }) {
  return (
    <div className={`rounded-xl border px-3 py-2.5 ${bg}`}>
      <p className="text-[9px] font-bold uppercase tracking-wide text-gray-400">{label}</p>
      <p className="text-sm font-bold text-gray-900 mt-0.5 leading-tight">{value}</p>
      {sub && <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}
function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10">
      <div className="relative h-11 w-11 animate-[spin_1.2s_linear_infinite]">
        {["top-1 left-1/2 -translate-x-1/2", "left-1 top-1/2 -translate-y-1/2", "right-1 top-1/2 -translate-y-1/2", "bottom-1 left-1/2 -translate-x-1/2"].map(p => (
          <span key={p} className={`absolute ${p} h-2.5 w-2.5 rounded-full bg-rose-500`} />
        ))}
      </div>
      <p className="text-sm font-semibold text-gray-500">{label}</p>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Step 1 — Buyer selector (white bg per spec)
   ───────────────────────────────────────────────────────────────── */
function BuyerSelector({ buyers, selectedBuyer, onSelect }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")

  const filtered = buyers.filter(b => b.name.toLowerCase().includes(q.toLowerCase())).slice(0, 20)

  const pick = b => { onSelect(b); setQ(b.name); setOpen(false) }

  useEffect(() => { if (!selectedBuyer) setQ("") }, [selectedBuyer])

  return (
    <Card className="!overflow-visible relative z-20">
      <CardHeader icon="🌍" title="Step 1 — Select Global Buyer" subtitle="Choose a buyer to load their purchase history" />
      <div className="p-5">
        <label className="text-xs font-semibold text-gray-600 tracking-wide block mb-1">Buyer</label>
        <div className="relative">
          <input
            value={q}
            onChange={e => { setQ(e.target.value); setOpen(true) }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            placeholder="Search buyer…"
            autoComplete="off"
            className="w-full border border-gray-200 rounded-lg px-3 h-11 !py-0 leading-[42px] text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-rose-400"
            style={{ background: "#FFFFFF" }}
          />
          {open && filtered.length > 0 && (
            <div className="absolute left-0 right-0 top-11 z-30 max-h-56 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-lg">
              {filtered.map(b => (
                <button key={b.id} type="button"
                  onMouseDown={e => e.preventDefault()}
                  onClick={() => pick(b)}
                  className="block w-full px-3 py-2.5 text-left text-sm text-gray-700 hover:bg-rose-50"
                >
                  <span className="font-semibold">{b.name}</span>
                  <span className="ml-2 text-xs text-gray-400">{b.country} · {b.segment}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {selectedBuyer && (
          <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400 mb-2">Buyer Profile</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                ["Country", selectedBuyer.country],
                ["Segment", selectedBuyer.segment],
                ["Max PCF", `${selectedBuyer.max_pcf_limit} tCO₂e/ton`],
                ["Products", (selectedBuyer.products || []).join(", ")],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-[9px] font-bold uppercase text-gray-400">{k}</p>
                  <p className="text-xs font-semibold text-gray-800">{v}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Step 2 — Product grid (clickable pills)
   ───────────────────────────────────────────────────────────────── */
const PROD_ICONS = { CPO: "🛢️", RBDPO: "🍶", PKO: "🌰", RBDPKO: "🥃", PFAD: "⚗️", RBDOLN: "🫧" }
const PROD_LABELS = { CPO: "Crude Palm Oil", RBDPO: "RBD Palm Olein", PKO: "Palm Kernel Oil", RBDPKO: "RBD Palm Kernel Oil", PFAD: "Palm Fatty Acid Distillate", RBDOLN: "RBD Palm Olein" }

function ProductGrid({ buyer, selected, onSelect }) {
  if (!buyer) return null
  return (
    <Card>
      <CardHeader icon="📦" title="Step 2 — Select Product" subtitle="Click a product to trigger deep supply chain analysis" />
      <div className="p-5">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {(buyer.products || []).map(code => (
            <button key={code} onClick={() => onSelect(code)}
              className={`rounded-xl border px-3 py-3 text-left transition-all duration-150 ${selected === code
                ? "border-rose-500 bg-rose-50 shadow-sm"
                : "border-gray-100 bg-gray-50 hover:border-rose-200 hover:bg-rose-50/50"
                }`}
            >
              <div className="text-xl mb-1">{PROD_ICONS[code] || "📦"}</div>
              <p className="text-xs font-bold text-gray-900">{code}</p>
              <p className="text-[10px] text-gray-500 leading-tight">{PROD_LABELS[code] || code}</p>
            </button>
          ))}
        </div>
      </div>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Widget A — Historical Route card with frequency analysis
   ───────────────────────────────────────────────────────────────── */
function HistoricalRouteCard({ ctx }) {
  const r = ctx.historical.route
  const pcf = ctx.historical.pcf_breakdown || {}
  const history = ctx.shipping_history || []

  // Compute most-used estate / mill from shipping history
  const estateFreq = {}
  const millFreq = {}
  history.forEach(s => {
    const e = s.route?.estate?.name
    const m = s.route?.mill?.name
    if (e) estateFreq[e] = (estateFreq[e] || 0) + 1
    if (m) millFreq[m] = (millFreq[m] || 0) + 1
  })
  const topEstates = Object.entries(estateFreq).sort((a, b) => b[1] - a[1]).slice(0, 3)
  const topMills = Object.entries(millFreq).sort((a, b) => b[1] - a[1]).slice(0, 3)

  const NODES = [
    { key: "estate", icon: "🌴", bg: "bg-emerald-50 border-emerald-200", label: "Estate" },
    { key: "mill", icon: "🏭", bg: "bg-amber-50   border-amber-200", label: "Mill" },
    { key: "refinery", icon: "⛽", bg: "bg-blue-50    border-blue-200", label: "Refinery" },
  ]
  const stages = [
    { label: "Stage 1 · Harvest", val: pcf.stage1_harvest_emission_kg_co2e, color: "bg-emerald-500" },
    { label: "Stage 2 · Transport E→M", val: pcf.stage2_transport_estate_to_mill_kg_co2e, color: "bg-yellow-500" },
    { label: "Stage 3 · Mill Processing", val: pcf.stage3_mill_processing_emission_kg_co2e, color: "bg-amber-500" },
    { label: "Stage 4 · Transport M→R", val: pcf.stage4_transport_mill_to_refinery_kg_co2e, color: "bg-orange-500" },
    { label: "Stage 5 · Refinery Process", val: pcf.stage5_refinery_processing_emission_kg_co2e, color: "bg-blue-500" },
  ]
  const totalPcf = pcf.total_kg_co2e || 0

  return (
    <Card>
      <CardHeader icon="🗺️" title="Historical Supply Chain Route"
        subtitle={`Verified baseline route — ${ctx.product_label}`}
        right={<Badge color="blue">Baseline</Badge>}
      />
      <div className="p-5 space-y-5">
        {/* 3-hop flow */}
        <div className="flex items-start gap-1 justify-between">
          {NODES.map(({ key, icon, bg, label }, i) => {
            const node = r[key]
            return (
              <div key={key} className="flex items-start gap-1 flex-1">
                <div className="flex-1">
                  <div className={`rounded-xl border ${bg} p-3 flex flex-col items-center text-center`}>
                    <span className="text-xl mb-1">{icon}</span>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-gray-400">{label}</p>
                    <p className="text-[11px] font-semibold text-gray-800 mt-1 leading-tight">{node?.name || "—"}</p>
                    <p className="text-[9px] text-gray-400 mt-0.5">ID: {node?.id}</p>
                    {node?.spec && (
                      <span className={`mt-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${node.spec === "EUDR" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                        }`}>{node.spec}</span>
                    )}
                  </div>
                </div>
                {i < 2 && (
                  <div className="flex items-center pt-7 px-0.5 shrink-0">
                    <svg width="20" height="12" viewBox="0 0 20 12" fill="none">
                      <path d="M0 6h16" stroke="#d1d5db" strokeWidth="2" />
                      <path d="M12 1l5 5-5 5" stroke="#d1d5db" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* PCF per-stage breakdown */}
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">
            PCF Per-Stage Breakdown — Total {fmtNum(totalPcf / 1000, 4)} tCO₂e
          </p>
          <div className="space-y-2">
            {stages.map(s => {
              const pct = totalPcf > 0 ? (Number(s.val) / totalPcf * 100) : 0
              return (
                <div key={s.label} className="grid grid-cols-[180px_1fr_80px] items-center gap-2">
                  <p className="text-[11px] font-semibold text-gray-600 leading-tight">{s.label}</p>
                  <div className="h-4 rounded-full bg-gray-100 overflow-hidden">
                    <div className={`h-full rounded-full ${s.color} transition-all duration-500`}
                      style={{ width: `${pct}%` }} />
                  </div>
                  <p className="text-[11px] font-bold text-gray-700 text-right">{fmtNum(s.val, 2)} kg</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-3 gap-3">
          <KpiCell label="Annual Volume" value={fmtMT(ctx.historical.quantity_mt)} sub="historical avg" bg="bg-blue-50 border-blue-100" />
          <KpiCell label="PCF Intensity" value={`${fmtNum(ctx.historical.pcf_per_unit_kg_co2e_per_kg, 3)} tCO₂e/ton`} sub="tonne CO₂e per tonne product" />
          <KpiCell label="Est. Distance" value={`${fmtNum(pcf.estate_to_mill_km, 0)} + ${fmtNum(pcf.mill_to_refinery_km, 0)} km`} sub="Estate→Mill + Mill→Refinery" />
        </div>

        {/* Frequency analysis from shipping history */}
        {(topEstates.length > 0 || topMills.length > 0) && (
          <div className="border-t border-gray-100 pt-4">
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">
              📊 Most Frequent Supply Sources ({history.length} historical shipments)
            </p>
            <div className="grid grid-cols-2 gap-4">
              {topEstates.length > 0 && (
                <div>
                  <p className="text-[9px] font-bold uppercase text-gray-400 mb-2">Top Estates 🌴</p>
                  <div className="space-y-1.5">
                    {topEstates.map(([name, count]) => (
                      <div key={name} className="flex items-center justify-between gap-2">
                        <p className="text-[10px] font-semibold text-gray-700 leading-tight truncate">{name}</p>
                        <span className="shrink-0 rounded-full bg-emerald-100 border border-emerald-200 text-emerald-700 px-2 py-0.5 text-[9px] font-bold">
                          {count}×
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {topMills.length > 0 && (
                <div>
                  <p className="text-[9px] font-bold uppercase text-gray-400 mb-2">Top Mills 🏭</p>
                  <div className="space-y-1.5">
                    {topMills.map(([name, count]) => (
                      <div key={name} className="flex items-center justify-between gap-2">
                        <p className="text-[10px] font-semibold text-gray-700 leading-tight truncate">{name}</p>
                        <span className="shrink-0 rounded-full bg-amber-100 border border-amber-200 text-amber-700 px-2 py-0.5 text-[9px] font-bold">
                          {count}×
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Widget B — Forecast & Gap Verdict
   ───────────────────────────────────────────────────────────────── */
function ForecastGapCard({ ctx }) {
  const fc = ctx.forecast
  const filled = Math.min(Number(fc.fulfillment_pct || 0), 100)
  const gap = Math.min(Number(fc.unmet_demand_pct || 0), 100)

  const STATUS = {
    FULFILLED: { bg: "bg-green-50  border-green-200", pill: "bg-green-100  text-green-700", icon: "✅" },
    MINOR: { bg: "bg-yellow-50 border-yellow-200", pill: "bg-yellow-100 text-yellow-700", icon: "⚠️" },
    MODERATE: { bg: "bg-orange-50 border-orange-200", pill: "bg-orange-100 text-orange-700", icon: "⚠️" },
    CRITICAL: { bg: "bg-red-50    border-red-200", pill: "bg-red-100    text-red-700", icon: "🚨" },
  }
  const s = STATUS[fc.gap_status] || STATUS.MODERATE

  return (
    <Card>
      <CardHeader icon="📈" title="Forecast & Gap Verdict"
        subtitle="Current-year refinery capacity vs projected demand"
        right={<span className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${s.pill}`}>{fc.gap_status}</span>}
      />
      <div className="p-5 space-y-4">
        {/* Status banner */}
        <div className={`rounded-xl border px-4 py-3 ${s.bg}`}>
          <p className="text-sm font-bold text-gray-800">
            {s.icon}&nbsp;
            {fc.has_gap
              ? `${fmtPct(fc.unmet_demand_pct)} Unmet Demand Detected (${fmtMT(fc.unmet_demand_mt)})`
              : "Historical route fully covers projected demand"}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            Headroom: {fmtMT(fc.current_capacity_mt)} · Demand: {fmtMT(fc.projected_demand_mt)}
          </p>
        </div>

        {/* Dual progress bar */}
        <div>
          <div className="flex justify-between mb-1.5">
            <span className="text-xs font-semibold text-gray-600">Supply Fulfillment</span>
            <span className="text-xs font-semibold text-gray-600">{fmtPct(filled)} met</span>
          </div>
          <div className="flex h-8 rounded-lg overflow-hidden border border-gray-100 bg-gray-100">
            <div className="flex items-center justify-end px-2 text-xs font-bold text-white transition-all duration-700"
              style={{ width: `${filled}%`, background: "linear-gradient(90deg,#16a34a,#22c55e)", minWidth: filled > 8 ? undefined : 0 }}>
              {filled > 15 && fmtPct(filled)}
            </div>
            <div className="flex items-center px-2 text-xs font-bold text-white transition-all duration-700"
              style={{ width: `${gap}%`, background: "linear-gradient(90deg,#dc2626,#ef4444)", minWidth: gap > 5 ? undefined : 0 }}>
              {gap > 12 && fmtPct(gap)}
            </div>
          </div>
          <div className="flex justify-between mt-1.5">
            <span className="flex items-center gap-1 text-[10px] text-gray-500">
              <span className="w-2.5 h-2.5 rounded-sm bg-green-500 inline-block" />Baseline Met
            </span>
            <span className="flex items-center gap-1 text-[10px] text-gray-500">
              Shortfall<span className="w-2.5 h-2.5 rounded-sm bg-red-500 inline-block" />
            </span>
          </div>
        </div>

        {/* KPI grid */}
        <div className="grid grid-cols-2 gap-3">
          <KpiCell label="Projected Demand" value={fmtMT(fc.projected_demand_mt)} bg="bg-blue-50 border-blue-100" />
          <KpiCell label="Available Capacity" value={fmtMT(fc.current_capacity_mt)} bg="bg-green-50 border-green-100" />
          <KpiCell label="Fulfillment Rate" value={fmtPct(fc.fulfillment_pct)} />
          <KpiCell label="Unmet Demand" value={fmtMT(fc.unmet_demand_mt)}
            bg={fc.has_gap ? "bg-red-50 border-red-100" : "bg-green-50 border-green-100"} />
        </div>
      </div>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Widget C — Historical Shipping Timeline (clickable)
   ───────────────────────────────────────────────────────────────── */
function CertBadge({ label, certNumber, color }) {
  if (!certNumber) return null
  const cls = {
    green: "bg-green-50  border-green-300  text-green-700",
    blue: "bg-blue-50   border-blue-300   text-blue-700",
    purple: "bg-purple-50 border-purple-300 text-purple-700",
    amber: "bg-amber-50  border-amber-300  text-amber-700",
  }[color] || "bg-gray-50 border-gray-300 text-gray-600"
  return (
    <div className={`rounded-lg border px-2.5 py-1.5 ${cls}`}>
      <p className="text-[9px] font-bold uppercase tracking-wide">{label}</p>
      <p className="text-[10px] font-semibold mt-0.5 break-all">{certNumber}</p>
    </div>
  )
}

function ShipmentDetailPanel({ shipment, buyerMaxPcf, onClose, onUseAsTemplate }) {
  const pcf = shipment.pcf_breakdown || {}
  const route = shipment.route || {}
  const certs = shipment.certificates || {}
  const chain = shipment.supply_chain || []
  const stages = [
    { label: "Stage 1 · Harvest", val: pcf.stage1_harvest_emission_kg_co2e },
    { label: "Stage 2 · Transport E→M", val: pcf.stage2_transport_estate_to_mill_kg_co2e },
    { label: "Stage 3 · Mill Processing", val: pcf.stage3_mill_processing_emission_kg_co2e },
    { label: "Stage 4 · Transport M→R", val: pcf.stage4_transport_mill_to_refinery_kg_co2e },
    { label: "Stage 5 · Refinery Process", val: pcf.stage5_refinery_processing_emission_kg_co2e },
  ]
  const totalPcf = pcf.total_kg_co2e || 0
  const pcfOk = (pcf.pcf_per_unit_kg_co2e_per_kg || 0) <= buyerMaxPcf
  const isTemplate = shipment.recommended_as_template
  const activeCerts = ['eudr', 'rspo', 'iscc', 'mspo', 'ispo'].filter(k => certs[k])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 w-full max-w-3xl max-h-[92vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-100 flex items-start justify-between gap-4 sticky top-0 bg-white z-10 rounded-t-2xl">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className="text-lg">📦</span>
              <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                {shipment.bl_number || shipment.shipment_id}
              </p>
              {isTemplate && <Badge color="green">Recommended Template</Badge>}
              {activeCerts.length > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-700 text-[9px] font-bold">
                  {activeCerts.length} certs
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold text-gray-900">
              {fmtMT(shipment.volume_mt)} {shipment.product_label || shipment.product || ""} · {fmtDate(shipment.date)}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {shipment.vessel_name || "—"} &middot; {shipment.loading_port || "—"} → {shipment.discharge_port || "—"}
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50 shrink-0">✕ Close</button>
        </div>

        <div className="p-6 space-y-5">
          {/* Shipment KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCell label="Bill of Lading" value={shipment.bl_number || "—"} bg="bg-blue-50 border-blue-100" />
            <KpiCell label="Volume" value={fmtMT(shipment.volume_mt)} />
            <KpiCell label="Grade" value={shipment.grade || shipment.product || "—"} />
            <KpiCell label="FFA Content" value={shipment.moisture_ffa_pct ? shipment.moisture_ffa_pct + "%" : "—"} sub="Free fatty acid"
              bg={Number(shipment.moisture_ffa_pct || 0) > 0.15 ? "bg-orange-50 border-orange-100" : "bg-gray-50 border-gray-100"} />
          </div>

          {/* Supply Chain — trace nodes or static 3-hop */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">
              Supply Chain Path
              {shipment.supply_chain_source === "trace_engine" && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-blue-100 border border-blue-200 text-blue-700 text-[9px] font-bold">Live Trace</span>
              )}
            </p>
            {chain.length > 0 ? (
              <div className="rounded-xl border border-gray-100 bg-gray-50 overflow-auto max-h-52">
                <table className="min-w-full text-xs">
                  <thead className="bg-gray-100 border-b border-gray-200">
                    <tr>{["Lvl", "Supplier", "Type", "Product", "Qty (kg)", "Days"].map(h => (
                      <th key={h} className="px-3 py-2 text-left text-[10px] font-bold uppercase text-gray-500">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {chain.map((node, ni) => {
                      const TC = { ESTATE: "bg-emerald-50 text-emerald-700 border-emerald-200", MILL: "bg-amber-50 text-amber-700 border-amber-200", REFINERY: "bg-blue-50 text-blue-700 border-blue-200" }[node.supplier_type] || "bg-gray-50 text-gray-600 border-gray-200"
                      return (
                        <tr key={ni} className="hover:bg-gray-100">
                          <td className="px-3 py-2 font-bold text-gray-500">{node.level ?? ni}</td>
                          <td className="px-3 py-2 font-semibold text-gray-800">{node.supplier_name || node.supplier_id || "—"}</td>
                          <td className="px-3 py-2"><span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${TC}`}>{node.supplier_type || "—"}</span></td>
                          <td className="px-3 py-2 text-gray-600">{node.product || "—"}</td>
                          <td className="px-3 py-2 text-right font-semibold text-gray-800">{Number(node.quantity || 0).toLocaleString("id-ID")}</td>
                          <td className="px-3 py-2 text-right text-gray-600">{node.estimated_days ?? "—"}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex items-start gap-2 justify-between">
                {[{ node: route.estate, icon: "🌴", bg: "bg-emerald-50 border-emerald-200" }, { node: route.mill, icon: "🏭", bg: "bg-amber-50 border-amber-200" }, { node: route.refinery, icon: "⛽", bg: "bg-blue-50 border-blue-200" }].map(({ node, icon, bg }, i) => (
                  <div key={i} className="flex items-start gap-1 flex-1">
                    <div className="flex-1">
                      <div className={`rounded-xl border ${bg} p-3 flex flex-col items-center text-center`}>
                        <span className="text-lg mb-0.5">{icon}</span>
                        <p className="text-[9px] font-bold uppercase text-gray-400">{node?.type}</p>
                        <p className="text-[11px] font-semibold text-gray-800 mt-0.5 leading-tight">{node?.name || "—"}</p>
                        {node?.spec === "EUDR" && <span className="mt-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-green-100 text-green-700">EUDR</span>}
                      </div>
                    </div>
                    {i < 2 && <div className="flex items-center pt-7 px-0.5 shrink-0"><svg width="16" height="10" viewBox="0 0 16 10" fill="none"><path d="M0 5h12" stroke="#d1d5db" strokeWidth="1.5" /><path d="M9 1l4 4-4 4" stroke="#d1d5db" strokeWidth="1.5" strokeLinecap="round" /></svg></div>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* PCF Breakdown */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">
              PCF Breakdown — {fmtNum(pcf.pcf_per_unit_kg_co2e_per_kg, 4)} tCO₂e/ton
              <span className={`ml-2 px-2 py-0.5 rounded-full text-[9px] font-bold border ${pcfOk ? "bg-green-100 border-green-200 text-green-700" : "bg-red-100 border-red-200 text-red-700"}`}>
                {pcfOk ? "Within Buyer Limit" : "Exceeds Buyer Limit"}
              </span>
            </p>
            <div className="space-y-2">
              {stages.map((st, i) => {
                const pct = totalPcf > 0 ? Number(st.val) / totalPcf * 100 : 0
                const colors = ["bg-emerald-500", "bg-yellow-500", "bg-amber-500", "bg-orange-500", "bg-blue-500"]
                return (
                  <div key={i} className="grid grid-cols-[160px_1fr_72px] items-center gap-2">
                    <p className="text-[10px] font-semibold text-gray-600 leading-tight">{st.label}</p>
                    <div className="h-3.5 rounded-full bg-gray-100 overflow-hidden"><div className={`h-full rounded-full ${colors[i]}`} style={{ width: `${pct}%` }} /></div>
                    <p className="text-[10px] font-bold text-gray-700 text-right">{fmtNum(st.val, 2)} kg</p>
                  </div>
                )
              })}
              <div className="grid grid-cols-[160px_1fr_72px] items-center gap-2 border-t border-gray-100 pt-2">
                <p className="text-[10px] font-bold text-gray-700">Total PCF</p>
                <div className="h-3.5 rounded-full bg-rose-500" style={{ width: "100%" }} />
                <p className="text-[10px] font-bold text-gray-900 text-right">{fmtNum(totalPcf / 1000, 4)} tCO₂e</p>
              </div>
            </div>
          </div>

          {/* Certificates */}
          {Object.keys(certs).length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">
                Compliance Certificates ({activeCerts.length} active)
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <CertBadge label="EUDR DDS" certNumber={certs.eudr_dds_reference} color="green" />
                <CertBadge label="RSPO" certNumber={certs.rspo_certificate_number} color="green" />
                <CertBadge label="ISCC-EU" certNumber={certs.iscc_certificate_number} color="blue" />
                <CertBadge label="MSPO" certNumber={certs.mspo_certificate_number} color="purple" />
                <CertBadge label="ISPO" certNumber={certs.ispo_certificate_number} color="amber" />
              </div>
              {certs.audit_date && (
                <div className="mt-2 flex gap-4 text-[10px] text-gray-500">
                  <span>Last audit: <strong className="text-gray-700">{fmtDate(certs.audit_date)}</strong></span>
                  <span>Next due: <strong className="text-gray-700">{fmtDate(certs.next_audit_due)}</strong></span>
                </div>
              )}
            </div>
          )}

          {/* Logistics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCell label="Vessel" value={shipment.vessel_name || "—"} />
            <KpiCell label="Loading Port" value={shipment.loading_port || "—"} />
            <KpiCell label="Discharge Port" value={shipment.discharge_port || "—"} />
            <KpiCell label="Est. Transit" value={shipment.estimated_days ? shipment.estimated_days + " days" : "—"} />
          </div>

          <div className={`rounded-xl border px-4 py-3 ${isTemplate ? "bg-green-50 border-green-200" : "bg-gray-50 border-gray-100"}`}>
            <p className="text-sm font-semibold text-gray-700">
              {isTemplate ? "✅ Recommended template — EUDR certified and within buyer PCF limit." : "ℹ️ Reference shipment. Verify PCF and certification validity before replicating."}
            </p>
          </div>

          {onUseAsTemplate && (
            <button onClick={() => onUseAsTemplate(shipment)} className="w-full bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition">
              Use This Route as Recommendation Template →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function ShippingTimeline({ shippingHistory = [], buyerMaxPcf, onSelectTemplate }) {
  const [selected, setSelected] = useState(null)

  if (!shippingHistory.length) return null

  const byYear = shippingHistory.reduce((acc, s) => {
    const y = s.year || new Date(s.date).getFullYear()
    if (!acc[y]) acc[y] = []
    acc[y].push(s)
    return acc
  }, {})

  const years = Object.keys(byYear).sort().reverse()

  return (
    <>
      <Card>
        <CardHeader icon="📅" title="Historical Shipping Timeline"
          subtitle="Click any shipment to inspect route details and PCF breakdown"
          right={<Badge color="blue">{shippingHistory.length} shipments · 2 years</Badge>}
        />
        <div className="p-5 space-y-5">
          {years.map(year => (
            <div key={year}>
              <p className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-3">{year}</p>
              <div className="space-y-2">
                {byYear[year].map((s, i) => {
                  const pcfOk = (s.pcf_breakdown?.pcf_per_unit_kg_co2e_per_kg || 0) <= buyerMaxPcf
                  return (
                    <button key={s.shipment_id} onClick={() => setSelected(s)}
                      className="w-full rounded-xl border border-gray-100 bg-gray-50 hover:border-rose-200 hover:bg-rose-50/40 hover:shadow-sm px-4 py-3 text-left transition-all flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${pcfOk ? "bg-green-500" : "bg-orange-400"}`} />
                        <div className="truncate">
                          <p className="text-sm font-bold text-gray-900 truncate">{s.bl_number || `BL-000${i+1}-DUMMY`}</p>
                          <p className="text-[11px] text-gray-500 mt-0.5 truncate">
                            {s.route?.estate?.name || "—"} → {s.route?.mill?.name || "—"} → {s.route?.refinery?.name || "—"}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-6 shrink-0">
                        <div className="text-right hidden sm:block w-24">
                           <p className="text-xs font-semibold text-gray-600">{fmtDate(s.date)}</p>
                        </div>
                        <div className="text-right w-28">
                          <p className="text-sm font-bold text-gray-900">{fmtMT(s.volume_mt)}</p>
                          <p className={`text-[11px] font-bold mt-0.5 ${pcfOk ? "text-green-600" : "text-orange-600"}`}>
                            PCF {fmtNum(s.pcf_breakdown?.pcf_per_unit_kg_co2e_per_kg, 3)}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 w-auto justify-end">
                          {s.recommended_as_template && <Badge color="green">Template</Badge>}
                          <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {selected && (
        <ShipmentDetailPanel
          shipment={selected}
          buyerMaxPcf={buyerMaxPcf}
          onClose={() => setSelected(null)}
          onUseAsTemplate={onSelectTemplate ? (s) => { onSelectTemplate(s); setSelected(null) } : null}
        />
      )}
    </>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Widget D — Capacity Heatmap (mini)
   ───────────────────────────────────────────────────────────────── */
function CapacityHeatmap({ heatmapData }) {
  if (!heatmapData?.refineries?.length) return null
  return (
    <Card>
      <CardHeader icon="🏭" title="Refinery Capacity Heatmap"
        subtitle="Current-year utilization across all refineries"
      />
      <div className="p-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {heatmapData.refineries.map(r => {
            const color = r.status === "CRITICAL" ? "bg-red-500" : r.status === "WARNING" ? "bg-yellow-500" : "bg-green-500"
            const textColor = r.status === "CRITICAL" ? "text-red-700" : r.status === "WARNING" ? "text-yellow-700" : "text-green-700"
            const bgColor = r.status === "CRITICAL" ? "bg-red-50 border-red-100" : r.status === "WARNING" ? "bg-yellow-50 border-yellow-100" : "bg-green-50 border-green-100"
            return (
              <div key={r.refinery} className={`rounded-xl border px-3 py-2.5 ${bgColor}`}>
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-[11px] font-bold text-gray-800 leading-tight">{r.refinery}</p>
                  <span className={`text-[10px] font-bold ${textColor}`}>{r.status}</span>
                </div>
                <div className="h-2 rounded-full bg-gray-200 overflow-hidden mb-1.5">
                  <div className={`h-full rounded-full ${color} transition-all duration-500`}
                    style={{ width: `${Math.min(r.utilization_pct, 100)}%` }} />
                </div>
                <div className="flex justify-between">
                  <span className="text-[10px] text-gray-500">{fmtMT(r.committed_mt)} committed</span>
                  <span className="text-[10px] font-bold text-gray-700">{fmtNum(r.utilization_pct, 1)}%</span>
                </div>
                <p className="text-[10px] text-gray-400 mt-0.5">{fmtMT(r.available_mt)} available</p>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Widget E — Resolution Route Card (with real trace tree or dummy)
   ───────────────────────────────────────────────────────────────── */
function PcfStageBar({ breakdown }) {
  if (!breakdown) return null
  const total = breakdown.total_kg_co2e || 0
  const stages = [
    { key: "stage1_harvest_emission_kg_co2e", label: "Harvest", color: "bg-emerald-500" },
    { key: "stage2_transport_estate_to_mill_kg_co2e", label: "E→M Transp", color: "bg-yellow-500" },
    { key: "stage3_mill_processing_emission_kg_co2e", label: "Mill", color: "bg-amber-500" },
    { key: "stage4_transport_mill_to_refinery_kg_co2e", label: "M→R Transp", color: "bg-orange-500" },
    { key: "stage5_refinery_processing_emission_kg_co2e", label: "Refinery", color: "bg-blue-500" },
  ]
  return (
    <div className="space-y-1">
      {stages.map(s => {
        const val = breakdown[s.key] || 0
        const pct = total > 0 ? val / total * 100 : 0
        return (
          <div key={s.key} className="grid grid-cols-[68px_1fr_52px] items-center gap-1.5">
            <p className="text-[9px] text-gray-500 font-medium leading-tight">{s.label}</p>
            <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
              <div className={`h-full rounded-full ${s.color}`} style={{ width: `${pct}%` }} />
            </div>
            <p className="text-[9px] font-bold text-gray-600 text-right">{fmtNum(val, 1)}</p>
          </div>
        )
      })}
    </div>
  )
}

function RouteNodeFlow({ path = [] }) {
  const estate = path.find(n => (n.supplier_type || "").toUpperCase() === "ESTATE") || path[0]
  const mill = path.find(n => (n.supplier_type || "").toUpperCase() === "MILL") || path[1]
  const refinery = path.find(n => (n.supplier_type || "").toUpperCase() === "REFINERY") || path[path.length - 1]

  const nodes = [
    { node: estate, icon: "🌴", bg: "bg-emerald-50 border-emerald-200" },
    { node: mill, icon: "🏭", bg: "bg-amber-50   border-amber-200" },
    { node: refinery, icon: "⛽", bg: "bg-blue-50    border-blue-200" },
  ]

  return (
    <div className="flex items-start gap-1 justify-between">
      {nodes.map(({ node, icon, bg }, i) => (
        <div key={i} className="flex items-start gap-1 flex-1">
          <div className="flex-1">
            <div className={`rounded-xl border ${bg} p-2.5 flex flex-col items-center text-center`}>
              <span className="text-base mb-0.5">{icon}</span>
              <p className="text-[9px] font-bold uppercase text-gray-400">
                {node?.supplier_type || node?.node_type || ["ESTATE", "MILL", "REFINERY"][i]}
              </p>
              <p className="text-[10px] font-semibold text-gray-800 mt-0.5 leading-tight">
                {node?.supplier_name || "—"}
              </p>
              {(node?.quantity_mt || node?.quantity) && (
                <p className="text-[9px] text-gray-400 mt-0.5">
                  {node?.quantity_mt ? fmtMT(node.quantity_mt) : fmtKg(node.quantity)}
                </p>
              )}
            </div>
            {(node?.estimated_days || 0) > 0 && (
              <p className="text-[9px] text-gray-400 text-center mt-1">⏱ {node.estimated_days}d</p>
            )}
          </div>
          {i < 2 && (
            <div className="flex items-center pt-6 px-0.5 shrink-0">
              <svg width="14" height="9" viewBox="0 0 14 9" fill="none">
                <path d="M0 4.5h10" stroke="#d1d5db" strokeWidth="1.5" />
                <path d="M7 1l4 3.5-4 3.5" stroke="#d1d5db" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ResolutionRouteCard({ route, buyerMaxPcf, index }) {
  const [showTree, setShowTree] = useState(false)
  const em = route.enterprise_metrics || {}
  const pcf = em.pcf_score || {}
  const cap = em.capacity_constraints || {}
  const dist = em.route_distance || {}
  const vol = em.volume_similarity || {}
  const isReal = route.source === "trace_engine"

  const REC = {
    OPTIMAL: { bar: "bg-green-500", pill: "bg-green-100  text-green-700", label: "✓ Optimal" },
    ACCEPTABLE: { bar: "bg-yellow-500", pill: "bg-yellow-100 text-yellow-700", label: "~ Acceptable" },
    RISKY: { bar: "bg-red-500", pill: "bg-red-100    text-red-700", label: "⚠ Risky" },
  }
  const rec = REC[em.recommendation] || REC.ACCEPTABLE

  const FOCUS_BG = {
    VOLUME: "from-blue-50 to-cyan-50",
    PCF: "from-green-50 to-emerald-50",
    DISTANCE: "from-purple-50 to-indigo-50",
  }
  const focusBg = FOCUS_BG[route.optimization_focus] || "from-gray-50 to-slate-50"
  const focusIcon = { VOLUME: "🚀", PCF: "🌱", DISTANCE: "🗺️" }[route.optimization_focus] || "📌"

  const pcfCompliant = (pcf.pcf_per_unit_kg_co2e_per_kg || 0) <= buyerMaxPcf
  const stageBreakdown = pcf.stage_breakdown || null

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      {/* Header */}
      <div className={`bg-gradient-to-r ${focusBg} border-b border-gray-100 px-5 py-4`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span>{focusIcon}</span>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{route.route_id}</span>
              <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${rec.pill}`}>{rec.label}</span>
              {isReal && <Badge color="blue">Live Trace</Badge>}
              {!isReal && <Badge color="gray">Modelled</Badge>}
            </div>
            <p className="text-base font-bold text-gray-900">{route.route_label}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {fmtMT(route.routed_volume_mt)} · {fmtPct(route.fulfillment_share_pct)} of gap · Est. {route.estimated_days}d
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-[10px] font-bold text-gray-400 uppercase">Score</p>
            <p className="text-3xl font-black text-gray-900 leading-none">{fmtNum(em.overall_score, 1)}</p>
          </div>
        </div>
      </div>

      {/* 3-hop path */}
      <div className="px-5 pt-4">
        <p className="text-[9px] font-bold uppercase tracking-widest text-gray-400 mb-3">Supply Chain Path</p>
        <RouteNodeFlow path={route.supply_chain_path || []} />
      </div>

      {/* 4 Enterprise Metrics grid */}
      <div className="px-5 pt-4 pb-1 grid grid-cols-2 gap-2">
        <KpiCell icon="🌱" label="Total PCF" value={`${fmtNum(pcf.pcf_total_kg_co2e / 1000, 3)} tCO₂e`}
          sub={`${fmtNum(pcf.pcf_per_unit_kg_co2e_per_kg, 4)} tCO₂e/ton`}
          bg={pcfCompliant ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"} />
        <KpiCell icon="⚙️" label="Capacity Load" value={`${fmtNum(cap.capacity_load_pct, 1)}%`}
          sub={cap.warning_state}
          bg={cap.warning_state === "NORMAL" ? "bg-green-50 border-green-200" : cap.warning_state === "WARNING" ? "bg-yellow-50 border-yellow-200" : "bg-red-50 border-red-200"} />
        <KpiCell icon="🗺️" label="Route Dist" value={`${fmtNum(dist.total_distance_km, 1)} km`}
          sub={`Eff: ${fmtNum(dist.efficiency_score_percent, 1)}%`}
          bg={dist.efficiency_level === "HIGH" ? "bg-green-50 border-green-200" : dist.efficiency_level === "MEDIUM" ? "bg-yellow-50 border-yellow-200" : "bg-red-50 border-red-200"} />
        <KpiCell icon="📊" label="Vol. Similarity" value={`${fmtNum(vol.similarity_pct, 1)}%`}
          sub={`${vol.risk_level} risk`}
          bg={vol.risk_level === "LOW" ? "bg-green-50 border-green-200" : vol.risk_level === "MEDIUM" ? "bg-yellow-50 border-yellow-200" : "bg-red-50 border-red-200"} />
      </div>

      {/* PCF per-stage breakdown (inline) */}
      {stageBreakdown && (
        <div className="px-5 pt-3 pb-1">
          <p className="text-[9px] font-bold uppercase tracking-widest text-gray-400 mb-2">PCF Stages (tCO₂e)</p>
          <PcfStageBar breakdown={stageBreakdown} />
        </div>
      )}

      {/* Buyer PCF compliance */}
      <div className={`mx-5 mt-3 mb-1 rounded-xl border px-3 py-2 flex items-center gap-2 ${pcfCompliant ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
        }`}>
        <span>{pcfCompliant ? "✅" : "❌"}</span>
        <p className="text-xs font-semibold text-gray-700">
          Buyer PCF:&nbsp;<strong>{pcf.buyer_compliance === "WITHIN_LIMIT" ? "Within limit" : "Exceeds limit"}</strong>
          &nbsp;(limit {fmtNum(buyerMaxPcf, 2)} vs actual {fmtNum(pcf.pcf_per_unit_kg_co2e_per_kg, 4)} tCO₂e/ton)
        </p>
      </div>

      {/* Expandable real tree (for Live Trace routes) */}
      {isReal && (route.supply_chain_path || []).length > 3 && (
        <div className="px-5 pb-4 mt-2">
          <button onClick={() => setShowTree(t => !t)}
            className="text-xs font-bold text-rose-600 hover:text-rose-500 flex items-center gap-1">
            {showTree ? "▾ Hide full route tree" : "▸ Show full route tree"}
            <span className="text-gray-400 font-normal">({route.supply_chain_path.length} nodes)</span>
          </button>
          {showTree && (
            <div className="mt-3 rounded-xl border border-gray-100 bg-gray-50 overflow-auto max-h-64">
              <table className="min-w-full text-xs">
                <thead className="bg-gray-100 border-b border-gray-200">
                  <tr>
                    {["Lvl", "Supplier", "Type", "Product", "Qty (kg)", "Days", "PCF/unit"].map(h => (
                      <th key={h} className="px-3 py-2 text-left text-[10px] font-bold uppercase text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {route.supply_chain_path.map((node, ni) => (
                    <tr key={ni} className="hover:bg-gray-100">
                      <td className="px-3 py-2 font-bold text-gray-600">{node.level ?? ni}</td>
                      <td className="px-3 py-2 font-semibold text-gray-800">{node.supplier_name || node.supplier_id || "—"}</td>
                      <td className="px-3 py-2">
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${node.supplier_type === "ESTATE" ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : node.supplier_type === "MILL" ? "bg-amber-50 text-amber-700 border-amber-200"
                            : "bg-blue-50 text-blue-700 border-blue-200"
                          }`}>{node.supplier_type || "—"}</span>
                      </td>
                      <td className="px-3 py-2 text-gray-600">{node.product || "—"}</td>
                      <td className="px-3 py-2 text-right font-semibold text-gray-800">{Number(node.quantity || 0).toLocaleString("id-ID")}</td>
                      <td className="px-3 py-2 text-right text-gray-600">{node.estimated_days ?? "—"}</td>
                      <td className="px-3 py-2 text-right font-bold text-gray-700">
                        {node.pcf_per_unit_kg_co2e_per_kg ? fmtNum(node.pcf_per_unit_kg_co2e_per_kg, 4) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Score bar footer */}
      <div className="h-2 w-full bg-gray-100 mt-auto">
        <div className={`h-full ${rec.bar} transition-all duration-500`}
          style={{ width: `${Math.min(em.overall_score || 0, 100)}%` }} />
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Main export — DrilldownDashboard
   ───────────────────────────────────────────────────────────────── */
export default function DrilldownDashboard() {
  const [buyers, setBuyers] = useState([])
  const [selectedBuyer, setSelectedBuyer] = useState(null)
  const [selectedProd, setSelectedProd] = useState(null)
  const [context, setContext] = useState(null)
  const [resolution, setResolution] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [loadingCtx, setLoadingCtx] = useState(false)
    const [loadingRes, setLoadingRes] = useState(false)
  const [error, setError] = useState(null)
  
  // ✅ NEW: State for Blast Radius feature
  const [selectedNode, setSelectedNode] = useState(null)

  const searchParams = useSearchParams()
  const initBuyerName = searchParams.get("buyer")
  const initProduct = searchParams.get("product")

  // Load buyers + heatmap on mount
  useEffect(() => {
    fetch("/api/backend/api/drilldown/buyers")
      .then(r => r.json())
      .then(d => {
        const fetchedBuyers = d.buyers || []
        setBuyers(fetchedBuyers)
        if (initBuyerName && initProduct) {
          const matchedBuyer = fetchedBuyers.find(b => b.name === initBuyerName)
          if (matchedBuyer) {
            setSelectedBuyer(matchedBuyer)
            setSelectedProd(initProduct)
          }
        }
      })
      .catch(() => setError("Could not load buyers. Ensure the backend is running."))
  }, [initBuyerName, initProduct])

  // Fetch context whenever buyer + product change
  useEffect(() => {
    if (!selectedBuyer || !selectedProd) return
    setContext(null)
    setResolution(null)
    setError(null)
    setLoadingCtx(true)

    fetch("/api/backend/api/drilldown/product-context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buyer_id: selectedBuyer.id, product_code: selectedProd }),
    })
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail || "Error")))
      .then(data => {
        setContext(data)
        if (data.forecast?.has_gap) {
          setLoadingRes(true)
          fetch("/api/backend/api/drilldown/resolve-gap", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ buyer_id: selectedBuyer.id, product_code: selectedProd }),
          })
            .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail || "Error")))
            .then(setResolution)
            .catch(e => setError(String(e)))
            .finally(() => setLoadingRes(false))
        }
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoadingCtx(false))
  }, [selectedBuyer, selectedProd])

  const handleBuyerSelect = (b) => {
    setSelectedBuyer(b)
    setSelectedProd(null)
    setContext(null)
    setResolution(null)
  }

  const handleUseTemplate = (shipment) => {
    // Scroll to resolution section — user just selected a template
    document.getElementById("resolution-section")?.scrollIntoView({ behavior: "smooth" })
  }

  return (
    <div className="min-h-screen bg-gray-50">


      <main className="w-full max-w-[98vw] mx-auto px-3 md:px-6 py-6 flex flex-col gap-5">
        {/* Page title */}
        <div>
          <h1 className="text-xl font-bold text-gray-900">Supply Chain Drill-Down Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">
            Select a buyer → click a product → inspect historical routes, shipping timeline, gap verdict, and live fulfillment options.
          </p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 flex items-center gap-2">
            <span>⚠️</span>{error}
            <button onClick={() => setError(null)} className="ml-auto text-red-400 font-bold">✕</button>
          </div>
        )}

        {/* Step 1 & 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5" style={{ overflow: "visible" }}>
          <BuyerSelector buyers={buyers} selectedBuyer={selectedBuyer} onSelect={handleBuyerSelect} />
          <ProductGrid buyer={selectedBuyer} selected={selectedProd} onSelect={setSelectedProd} />
        </div>

        {/* Loading */}
        {loadingCtx && (
          <Card className="p-6">
            <Spinner label="Analysing historical route and capacity…" />
          </Card>
        )}

        {/* Step 3 — Bento grid */}
        {!loadingCtx && context && (
          <div className="flex flex-col gap-5" style={{ animation: "fadeSlideIn .35s ease both" }}>
            {/* Row 1: Route + Gap side by side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <HistoricalRouteCard ctx={context} />
              <ForecastGapCard ctx={context} />
            </div>

            {/* Row 2: Shipping Timeline (full-width) */}
            <ShippingTimeline
              shippingHistory={context.shipping_history || []}
              buyerMaxPcf={context.max_pcf_limit}
              onSelectTemplate={handleUseTemplate}
            />

                        {/* Row 3: Capacity Heatmap (if loaded) */}
            {heatmap && <CapacityHeatmap heatmapData={heatmap} />}

            {/* ✅ NEW: Blast Radius Impact Analysis Panel */}
            {(() => {
              // ✅ DUMMY: Auto-select first node for demonstration
              const demoNode = selectedNode || {
                id: "ESTATE_001",
                name: "Sumatra Estate Alpha",
                type: "ESTATE",
                supplier_type: "ESTATE"
              }

              return (
                <BlastRadiusPanel
                  selectedNode={demoNode}
                  supplyChainData={context}
                  onMitigationRequest={(node) => {
                    console.log('Mitigation requested for:', node)
                    // Navigate to recommendations with mitigation context
                    const params = new URLSearchParams({
                      mitigation_for: node.node_id,
                      facility: context?.historical?.route?.refinery?.name || ''
                    })
                    window.location.href = `/?${params.toString()}`
                  }}
                />
              )
            })()}
          </div>
        )}

        {/* Step 4 — Resolution routes */}
        {!loadingCtx && context?.forecast?.has_gap && (
          <div id="resolution-section" style={{ animation: "fadeSlideIn .45s ease both" }}>
            {/* Section header */}
            <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
              <div>
                <h2 className="text-lg font-bold text-gray-900">
                  Alternative Routes to Fulfill Unmet Demand
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  {fmtMT(context.forecast.unmet_demand_mt)} unmet ·{" "}
                  {fmtPct(context.forecast.unmet_demand_pct)} shortfall ·{" "}
                  Buyer PCF limit: <strong>{context.max_pcf_limit} tCO₂e/ton</strong>
                </p>
              </div>
              {resolution && (
                <div className="flex flex-wrap items-center gap-2">
                  {resolution.source && (
                    <Badge color={resolution.source === "trace_engine" ? "blue" : "gray"}>
                      {resolution.source === "trace_engine" ? "🔴 Live Trace Engine" : "📊 Modelled Data"}
                    </Badge>
                  )}
                  <Badge color="green">{fmtMT(resolution.total_routed_mt)} total routed</Badge>
                  <Badge color="blue">{fmtPct(resolution.combined_coverage_pct)} gap covered</Badge>
                </div>
              )}
            </div>

            {loadingRes && (
              <Card className="p-6">
                <Spinner label="Generating fulfillment routes via trace engine…" />
              </Card>
            )}

            {!loadingRes && resolution?.recommendation_options?.length > 0 && (
              <div className="mt-4">
                <SupplyGraph orderResult={{
                  ...resolution,
                  tree: resolution.recommendation_options[0].tree,
                  forecast_summary: resolution.recommendation_options[0].forecast_summary,
                  option_type: resolution.recommendation_options[0].option_type
                }} />
              </div>
            )}
          </div>
        )}

        {/* Fulfilled — no gap */}
        {!loadingCtx && context && !context.forecast.has_gap && (
          <div className="bg-green-50 border border-green-200 rounded-2xl px-5 py-4 flex items-center gap-3"
            style={{ animation: "fadeSlideIn .4s ease both" }}>
            <span className="text-2xl">✅</span>
            <div>
              <p className="text-sm font-bold text-green-800">No Gap — Demand Fully Covered</p>
              <p className="text-xs text-green-600 mt-0.5">
                The historical route via <strong>{context.historical.route.refinery.name}</strong> covers
                the full projected {fmtMT(context.forecast.projected_demand_mt)} demand.
                No alternative routes needed.
              </p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!loadingCtx && !context && !selectedProd && (
          <div className="rounded-2xl border border-dashed border-gray-200 bg-white px-6 py-14 text-center">
            <p className="text-3xl mb-3">🔍</p>
            <h3 className="text-base font-bold text-gray-900">No analysis yet</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
              Select a global buyer and click a product to trigger deep supply chain intelligence.
            </p>
          </div>
        )}
      </main>

      <style jsx global>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
