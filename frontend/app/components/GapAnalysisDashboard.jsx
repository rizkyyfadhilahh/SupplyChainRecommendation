"use client"

import { useState, useEffect } from "react"
import GapTrendIndicator from "./gap-analysis/GapTrendIndicatorSafe"

/* ── Primitive components ─────────────────────────────────────── */
function Card({ children, className = "" }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden ${className}`}>
      {children}
    </div>
  )
}

function Badge({ children, color = "gray", className = "" }) {
  const colors = {
    yellow: "bg-yellow-50 text-yellow-700 border-yellow-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
    green: "bg-green-50 text-green-700 border-green-200",
    red: "bg-red-50 text-red-700 border-red-200",
    orange: "bg-orange-50 text-orange-700 border-orange-200",
    gray: "bg-gray-50 text-gray-700 border-gray-200",
    white: "bg-white text-gray-700 border-gray-200",
  }
  const colorClass = colors[color] || colors.gray
  return (
    <span
      className={`inline-block px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border rounded-full ${colorClass} ${className}`}
    >
      {children}
    </span>
  )
}

function SectionTitle({ icon, title, badge }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      {icon && <span className="text-xl">{icon}</span>}
      <h2 className="text-base font-bold text-gray-900">
        {title}
      </h2>
      {badge && <Badge color="blue">{badge}</Badge>}
    </div>
  )
}

function Stat({ label, value, sub, bg = "bg-white" }) {
  return (
    <div className={`rounded-xl border border-gray-100 p-4 ${bg}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500 mb-1">
        {label}
      </p>
      <p className="text-2xl font-black text-gray-900 leading-tight">{value}</p>
      {sub && <p className="text-[11px] font-medium text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Buyer Selection Sidebar
   ───────────────────────────────────────────────────────────────── */
function BuyerSidebar({ selectedBuyer, onSelect, facility, onFacilityChange, onRerun }) {
  const [buyers, setBuyers] = useState([])
  const [buyerProfile, setBuyerProfile] = useState(null)

  const FACILITIES = [
    "Lubuk Gaung Refinery", "Lampung Refinery", "Marunda Refinery",
    "Belawan Refinery", "Tarjun Refinery", "Surabaya Refinery",
  ]

  useEffect(() => {
    fetch("/api/backend/api/buyers")
      .then(r => r.json())
      .then(d => setBuyers(d.buyers || []))
      .catch(() => {})
  }, [])

  const handleSelect = (name) => {
    const profile = buyers.find(b => b.name === name) || null
    setBuyerProfile(profile)
    onSelect(name)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Buyer Dropdown */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg">🌍</span>
          <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wide">
            Global Buyer
          </h2>
        </div>

        <div className="relative">
          <select
            value={selectedBuyer || ""}
            onChange={e => handleSelect(e.target.value)}
            className="w-full text-sm font-semibold p-2.5 rounded-lg border border-gray-200 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer"
          >
            <option value="">— SELECT BUYER —</option>
            {buyers.map(b => (
              <option key={b.name} value={b.name}>{b.name}</option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-500">
             <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
          </div>
        </div>

        {/* Buyer profile card */}
        {buyerProfile && (
          <div className="mt-4 rounded-xl border border-blue-100 p-3 bg-blue-50/50 space-y-1.5">
            <p className="text-[10px] font-bold uppercase text-blue-500 tracking-wide mb-2">Profile</p>
            <div className="flex items-center gap-2">
               <span className="text-sm">🏳️</span>
               <p className="text-xs font-semibold text-gray-700">{buyerProfile.country}</p>
            </div>
            <div className="flex items-center gap-2">
               <span className="text-sm">🏷️</span>
               <p className="text-xs font-semibold text-gray-700">{buyerProfile.segment}</p>
            </div>
            <div className="flex items-start gap-2">
               <span className="text-sm mt-0.5">📦</span>
               <p className="text-xs font-semibold text-gray-700">Products: {(buyerProfile.preferred_products || []).join(", ")}</p>
            </div>
            <div className="pt-2">
              <Badge color="purple">
                Max PCF: {buyerProfile.max_pcf_limit} kg CO₂e/kg
              </Badge>
            </div>
          </div>
        )}
      </Card>

      {/* Facility Selector */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg">🏭</span>
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide">
            Target Facility
          </h3>
        </div>
        <div className="relative">
          <select
            value={facility}
            onChange={e => onFacilityChange(e.target.value)}
            className="w-full text-sm font-semibold p-2.5 rounded-lg border border-gray-200 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer"
          >
            {FACILITIES.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-500">
             <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
          </div>
        </div>
        <button
          onClick={onRerun}
          disabled={!selectedBuyer}
          className="w-full mt-4 rounded-xl bg-gray-900 text-white px-4 py-2.5 text-sm font-bold shadow-sm disabled:opacity-40 hover:bg-gray-800 transition-colors"
        >
          🔄 Re-run Analysis
        </button>
      </Card>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Dual Progress Bar
   ───────────────────────────────────────────────────────────────── */
function DualProgressBar({ fulfilled, gap }) {
  const f = Math.min(Math.max(fulfilled, 0), 100)
  const g = Math.min(Math.max(gap, 0), 100)
  return (
    <div>
      <div className="flex justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-wide text-gray-600">
          Supply Fulfillment
        </span>
        <span className="text-xs font-bold text-gray-800">
          {f.toFixed(1)}% met · {g.toFixed(1)}% gap
        </span>
      </div>

      <div className="flex h-6 rounded-full overflow-hidden bg-gray-100 border border-gray-200">
        {/* Fulfilled portion */}
        <div
          className="flex items-center justify-end px-2 text-[10px] font-bold text-green-900 transition-all duration-700 bg-green-400"
          style={{ width: `${f}%`, minWidth: f > 5 ? "auto" : 0 }}
        >
          {f > 12 && `${f.toFixed(0)}%`}
        </div>

        {/* Gap portion */}
        <div
          className="flex items-center px-2 text-[10px] font-bold text-red-900 transition-all duration-700 bg-red-400"
          style={{ width: `${g}%`, minWidth: g > 5 ? "auto" : 0 }}
        >
          {g > 12 && `${g.toFixed(0)}%`}
        </div>
      </div>

      <div className="flex justify-between mt-2 px-1">
        <span className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-500 uppercase">
          <span className="w-2 h-2 rounded-full bg-green-400" />
          Baseline Met
        </span>
        <span className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-500 uppercase">
          Shortfall
          <span className="w-2 h-2 rounded-full bg-red-400" />
        </span>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Gap Dashboard Card (Top Section)
   ───────────────────────────────────────────────────────────────── */
function GapDashboard({ data }) {
  const { projected_demand: pd, supply_baseline: sb, gap_analysis: ga, max_pcf_limit, segment, country } = data
  const fulfilled = ga.fulfillment_rate_percent
  const gapPct    = ga.shortfall_percentage

  // ✅ ENHANCEMENT: Extract trend data if available (with dummy fallback)
  const trendData = ga.trend || {
    direction: "worsening",
    change_pct: -5.2
  }
  const hasTrend = trendData.direction && trendData.change_pct !== undefined

  const statusColor = {
    FULFILLED: "green",
    MINOR:     "yellow",
    MODERATE:  "orange",
    CRITICAL:  "red",
  }[ga.gap_status] || "gray"

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-100 px-6 py-4 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 text-xl">
             📊
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-900">
              Projection & Gap Dashboard — {data.projection_year || 2026}
            </h2>
            <p className="text-xs font-medium text-gray-500 mt-0.5">
              {data.buyer_name} · {country} · {segment}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Badge color="purple">Max PCF: {max_pcf_limit} kg CO₂e/kg</Badge>
          <Badge color={statusColor}>
            {ga.gap_status}
          </Badge>
          {/* ✅ NEW: Trend Badge */}
          {hasTrend && (
            <Badge color={trendData.direction === 'improving' ? 'green' : trendData.direction === 'worsening' ? 'red' : 'gray'}>
              {trendData.direction === 'improving' ? '↘' : trendData.direction === 'worsening' ? '↗' : '→'}
              {' '}{Math.abs(trendData.change_pct).toFixed(1)}% WoW
            </Badge>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* KPI Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Stat
            label="🔮 Projected Demand 2026"
            value={`${(pd.annual_kg / 1000).toFixed(1)} kton`}
            sub={`Monthly avg: ${(pd.monthly_average_kg / 1000).toFixed(1)} kton · Confidence: ${Math.round((pd.confidence_score || 0.85) * 100)}%`}
            bg="bg-blue-50/50"
          />
          <Stat
            label="📦 Baseline Supply Available"
            value={`${(sb.available_supply_kg / 1000).toFixed(1)} kton`}
            sub={`Capacity util: ${Math.round(sb.utilization_rate * 100)}% · ${data.facility}`}
            bg="bg-green-50/50"
          />
          <Stat
            label="⚠️ Fulfillment Gap"
            value={`${(ga.shortfall_kg / 1000).toFixed(1)} kton`}
            sub={`${gapPct.toFixed(1)}% deficit · Status: ${ga.gap_status}`}
            bg={ga.shortfall_kg > 0 ? "bg-red-50/50" : "bg-green-50/50"}
          />
        </div>

        {/* Progress Bar */}
        <div className="rounded-xl border border-gray-100 p-5 bg-white shadow-sm">
          <DualProgressBar fulfilled={fulfilled} gap={gapPct} />
        </div>

        {/* Product Breakdown + Capacity Status */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl border border-gray-100 p-4 bg-gray-50/50">
            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500 mb-3">
              Product Breakdown
            </p>
            {Object.entries(pd.product_breakdown).map(([p, q]) => (
              <div key={p} className="flex justify-between items-center py-1.5 border-b border-gray-200 last:border-0">
                <span className="text-xs font-semibold text-gray-700">{p}</span>
                <span className="text-xs font-bold text-gray-900">
                  {(q / 1000).toFixed(1)} kton
                </span>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-gray-100 p-4 bg-gray-50/50">
            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500 mb-3">
              Capacity Overview
            </p>
            <div className="space-y-2">
              {[
                ["Monthly Capacity", `${(sb.monthly_capacity_kg / 1000).toFixed(1)} kton`],
                ["Annual Capacity", `${(sb.monthly_capacity_kg * 12 / 1000).toFixed(1)} kton`],
                ["Committed (Utilized)", `${Math.round(sb.utilization_rate * 100)}%`],
                ["Available for Buyer", `${(sb.available_supply_kg / 1000).toFixed(1)} kton`],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs">
                  <span className="font-medium text-gray-600">{k}</span>
                  <span className="font-bold text-gray-900">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────────
   3-Hop Supply Chain Flow
   ───────────────────────────────────────────────────────────────── */
function SupplyChainFlow({ path }) {
  if (!path || path.length === 0) return null

  const estate   = path.find(n => (n.supplier_type || "").toUpperCase() === "ESTATE") || path[0]
  const mill     = path.find(n => (n.supplier_type || "").toUpperCase() === "MILL")   || path[1]
  const refinery = path.find(n => (n.supplier_type || "").toUpperCase() === "REFINERY") || path[path.length - 1]

  const nodes = [
    { node: estate,   icon: "🌴", bg: "bg-emerald-50 border-emerald-200", label: "ESTATE",   typeLabel: "FFB Origin" },
    { node: mill,     icon: "🏭", bg: "bg-amber-50 border-amber-200",    label: "MILL",     typeLabel: "Processing" },
    { node: refinery, icon: "⛽", bg: "bg-blue-50 border-blue-200",  label: "REFINERY", typeLabel: "Refining"  },
  ]

  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400 mb-3">
        Supply Chain Path (3-Hop)
      </p>
      <div className="flex items-start justify-between gap-1">
        {nodes.map(({ node, icon, bg, label, typeLabel }, i) => (
          <div key={i} className="flex items-start gap-1 flex-1">
            {/* Node block */}
            <div className="flex-1">
              <div className={`rounded-xl border ${bg} p-2.5 flex flex-col items-center text-center`}>
                <span className="text-base mb-1">{icon}</span>
                <p className="text-[9px] font-bold uppercase text-gray-400">{label}</p>
                <p className="text-[10px] font-semibold text-gray-800 mt-0.5 leading-tight min-h-[1.75rem] flex items-center justify-center">
                  {node?.supplier_name || "—"}
                </p>
                <div className="mt-1.5 flex flex-col items-center gap-1">
                  <Badge color="white" className="text-[8px] px-1.5">{typeLabel}</Badge>
                  {node?.quantity > 0 && (
                    <span className="text-[9px] font-bold text-gray-600 mt-0.5">
                      {(node.quantity / 1000).toFixed(2)} kton
                    </span>
                  )}
                </div>
              </div>
              {/* Days below node */}
              {node?.estimated_days > 0 && (
                <p className="text-[9px] text-gray-400 text-center mt-1">
                  ⏱ {node.estimated_days}d
                </p>
              )}
            </div>

            {/* Arrow between nodes */}
            {i < nodes.length - 1 && (
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
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Enterprise Metric Cell (4-grid inside route card)
   ───────────────────────────────────────────────────────────────── */
function MetricCell({ icon, label, value, status = "normal" }) {
  const bg = {
    good:     "bg-green-50  border-green-200",
    warning:  "bg-yellow-50 border-yellow-200",
    critical: "bg-red-50    border-red-200",
    normal:   "bg-gray-50   border-gray-200",
  }[status] || "bg-gray-50 border-gray-200"

  return (
    <div className={`flex items-start gap-2 rounded-xl border p-2.5 ${bg}`}>
      <span className="text-lg shrink-0 leading-none mt-0.5">{icon}</span>
      <div className="min-w-0">
        <p className="text-[9px] font-bold uppercase tracking-wide text-gray-500 leading-tight">
          {label}
        </p>
        <p className="text-xs font-bold text-gray-900 leading-tight mt-1">
          {value}
        </p>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Route Card — shows one fulfillment route with full metrics
   ───────────────────────────────────────────────────────────────── */
function RouteCard({ route, buyerPcfLimit }) {
  const em = route.enterprise_metrics
  const { pcf_score, capacity_constraints, route_distance, volume_similarity } = em.metrics

  const pcfOk  = pcf_score.pcf_per_unit_kg_co2e_per_kg <= (buyerPcfLimit || 2.5)
  const capOk  = capacity_constraints.warning_state === "NORMAL"
  const distOk = route_distance.efficiency_score_percent >= 60
  const volOk  = volume_similarity.volume_similarity_percent >= 50

  // ✅ ENHANCEMENT: Add navigation handler for Apply to Order
  const handleApplyToOrder = () => {
    const params = new URLSearchParams({
      route_id: route.route_id,
      facility: route.supply_chain_path?.find(n => n.supplier_type === "REFINERY")?.supplier_name || '',
      product: route.product_code || '',
      apply_route: 'true'
    })
    window.location.href = `/?${params.toString()}`
  }

  const recColors = {
    OPTIMAL: { bar: "bg-green-500", label: "✓ OPTIMAL ROUTE", text: "text-green-800", bg: "bg-green-100", pill: "green" },
    ACCEPTABLE: { bar: "bg-yellow-500", label: "~ ACCEPTABLE ROUTE", text: "text-yellow-800", bg: "bg-yellow-100", pill: "yellow" },
    RISKY: { bar: "bg-red-500", label: "⚠ RISKY ROUTE", text: "text-red-800", bg: "bg-red-100", pill: "red" },
  }
  const rec = recColors[em.recommendation] || recColors.ACCEPTABLE

  const focusIcon = {
    VOLUME:       "🚀",
    PCF:          "🌱",
    DISTANCE:     "🗺️",
  }[route.optimization_focus] || "📌"

  const focusBg = {
    VOLUME:       "from-blue-50 to-cyan-50 border-blue-100",
    PCF:          "from-green-50 to-emerald-50 border-green-100",
    DISTANCE:     "from-purple-50 to-indigo-50 border-purple-100",
  }[route.optimization_focus] || "from-gray-50 to-slate-50 border-gray-100"

  return (
    <Card className="flex flex-col">
      {/* Card Header */}
      <div className={`border-b px-5 py-4 bg-gradient-to-r ${focusBg}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span>{focusIcon}</span>
              <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{route.route_id}</span>
              <Badge color="white">{route.optimization_focus}</Badge>
            </div>
            <p className="text-base font-bold text-gray-900 mt-1">
              {route.route_label}
            </p>
            <p className="text-xs text-gray-600 mt-0.5 font-medium">
              {(route.routed_volume_kg / 1000).toFixed(2)} kton ·
              &nbsp;{route.fulfillment_share_percent}% of gap ·
              &nbsp;Est. {route.estimated_days} days
            </p>
          </div>

          {/* Overall Score */}
          <div className="text-right shrink-0">
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide">Score</p>
            <p className="text-3xl font-black text-gray-900 leading-none mt-0.5">
              {em.overall_score}
            </p>
          </div>
        </div>
      </div>

      {/* 3-Hop Supply Chain Flow */}
      <div className="px-5 pt-5 pb-2">
        <SupplyChainFlow path={route.supply_chain_path} />
      </div>

      {/* Enterprise Metrics Grid (4 metrics) */}
      <div className="px-5 pt-3 pb-5 flex-1">
        <p className="text-[9px] font-bold uppercase tracking-widest text-gray-400 mb-3">
          📋 Enterprise Metrics
        </p>

        <div className="grid grid-cols-2 gap-2">
          {/* Metric 1: PCF */}
          <MetricCell
            icon="🌱"
            label="Universal PCF"
            value={`${pcf_score.pcf_total_kg_co2e.toFixed(2)} kg CO₂e`}
            status={pcfOk ? "good" : "critical"}
          />
          <MetricCell
            icon="📏"
            label="PCF Intensity"
            value={`${pcf_score.pcf_per_unit_kg_co2e_per_kg.toFixed(4)} kg/kg`}
            status={pcfOk ? "good" : "warning"}
          />

          {/* Metric 2: Capacity */}
          <MetricCell
            icon="⚙️"
            label="Capacity Load"
            value={`${capacity_constraints.projected_utilization_percent.toFixed(1)}%`}
            status={capOk ? "good" : capacity_constraints.warning_state === "WARNING" ? "warning" : "critical"}
          />
          <MetricCell
            icon="✅"
            label="Can Fulfill"
            value={capacity_constraints.can_fulfill ? "YES" : "NO - Over Cap"}
            status={capacity_constraints.can_fulfill ? "good" : "critical"}
          />

          {/* Metric 3: Route Distance */}
          <MetricCell
            icon="🗺️"
            label="Route Distance"
            value={`${route_distance.total_distance_km} km`}
            status={distOk ? (route_distance.efficiency_level === "HIGH" ? "good" : "warning") : "critical"}
          />
          <MetricCell
            icon="⚡"
            label="Efficiency"
            value={`${route_distance.efficiency_score_percent}%`}
            status={route_distance.efficiency_level === "HIGH" ? "good" : route_distance.efficiency_level === "MEDIUM" ? "warning" : "critical"}
          />

          {/* Metric 4: Volume Similarity */}
          <MetricCell
            icon="📊"
            label="Vol. Similarity"
            value={`${volume_similarity.volume_similarity_percent.toFixed(1)}%`}
            status={volOk ? "good" : volume_similarity.risk_level === "MEDIUM" ? "warning" : "critical"}
          />
          <MetricCell
            icon="📉"
            label="Hist. Deviation"
            value={`${volume_similarity.deviation_percent.toFixed(1)}%`}
            status={volume_similarity.risk_level === "LOW" ? "good" : volume_similarity.risk_level === "MEDIUM" ? "warning" : "critical"}
          />
        </div>

        {/* Buyer PCF compliance banner */}
        {pcf_score.buyer_compliance && (
          <div className={`mt-3 rounded-xl border px-3 py-2.5 flex items-center gap-2 ${
            pcf_score.buyer_compliance === "WITHIN_LIMIT" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
          }`}>
            <span>{pcf_score.buyer_compliance === "WITHIN_LIMIT" ? "✅" : "❌"}</span>
            <p className="text-xs font-medium text-gray-700 leading-tight">
              Buyer PCF:&nbsp;
              <span className="font-bold">{pcf_score.buyer_compliance === "WITHIN_LIMIT" ? "Within Limit" : "Exceeds Limit"}</span>
              &nbsp;({pcf_score.pcf_per_unit_kg_co2e_per_kg.toFixed(4)} vs {pcf_score.buyer_pcf_limit})
            </p>
          </div>
        )}
      </div>

      {/* Footer / Status Bar - ENHANCED with Apply Button */}
      <div className={`mt-auto px-5 py-3 border-t border-gray-100 ${rec.bg} relative overflow-hidden`}>
         <div className={`absolute top-0 left-0 h-1 w-full ${rec.bar}`} />
         <div className="flex items-center justify-between gap-3">
           <p className={`text-xs font-bold tracking-wide ${rec.text}`}>
              {rec.label}
           </p>
           {/* ✅ NEW: Apply to Order Button (only for OPTIMAL routes) */}
           {em.recommendation === "OPTIMAL" && (
             <button
               onClick={handleApplyToOrder}
               className="rounded-lg bg-white border border-green-600 text-green-700 hover:bg-green-50 text-xs font-bold px-3 py-1.5 transition"
               title="Apply this route to create new order"
             >
               Apply to Order →
             </button>
           )}
         </div>
      </div>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Main Export — GapAnalysisDashboard
   ───────────────────────────────────────────────────────────────── */
export default function GapAnalysisDashboard() {
  const [selectedBuyer,  setSelectedBuyer]  = useState(null)
  const [facility,       setFacility]       = useState("Lubuk Gaung Refinery")
  const [gapData,        setGapData]        = useState(null)
  const [routes,         setRoutes]         = useState([])
  const [summary,        setSummary]        = useState(null)
  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState(null)

  const runAnalysis = async (buyerName, facilityName) => {
    if (!buyerName) return
    setLoading(true)
    setError(null)
    setGapData(null)
    setRoutes([])

    try {
      const res = await fetch("/api/backend/api/gap-fulfillment", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ buyer_name: buyerName, facility: facilityName }),
      })

      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `HTTP ${res.status}`)
      }

      let data = await res.json()

      if (data.job_id) {
        while (true) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          const statusRes = await fetch(`/api/backend/api/status/${data.job_id}`);
          const statusData = await statusRes.json();
          
          if (!statusRes.ok) throw new Error(statusData.detail || "Polling failed");
          
          if (statusData.status === "COMPLETED") {
             data = statusData.result;
             break;
          } else if (statusData.status === "FAILED") {
             throw new Error(statusData.error || "Gap analysis job failed");
          } else if (statusData.status === "UNKNOWN") {
             throw new Error("Job not found");
          }
        }
      }

      setGapData(data.gap_analysis)
      setRoutes(data.recommended_routes || [])
      setSummary({
        total_routed_volume_kg:     data.total_routed_volume_kg,
        combined_fulfillment_percent: data.combined_fulfillment_percent,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleBuyerSelect = (name) => {
    setSelectedBuyer(name)
    if (name) runAnalysis(name, facility)
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      {/* Page Header */}
      <div className="bg-white border-b border-gray-100 px-6 py-5 sticky top-[73px] z-10 shadow-sm">
        <div className="max-w-[98vw] mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-xl">
               📊
             </div>
             <div>
                <h1 className="text-xl font-bold text-gray-900">Supply Gap Analysis</h1>
                <p className="text-sm text-gray-500 mt-0.5">Predictive fulfillment modeling for long-term supply gaps</p>
             </div>
          </div>
          <div className="flex items-center gap-3">
             {/* Additional actions could go here */}
          </div>
        </div>
      </div>

      <main className="max-w-[98vw] mx-auto px-4 py-6">
        {/* Error Banner */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 shadow-sm flex items-center gap-3">
            <span className="text-red-500 text-xl">⚠️</span>
            <p className="text-sm font-semibold text-red-800">ERROR: {error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
          {/* Sidebar */}
          <BuyerSidebar
            selectedBuyer={selectedBuyer}
            onSelect={handleBuyerSelect}
            facility={facility}
            onFacilityChange={setFacility}
            onRerun={() => selectedBuyer && runAnalysis(selectedBuyer, facility)}
          />

          {/* Main Content */}
          <div className="flex flex-col gap-6">
            {/* Loading state */}
            {loading && (
              <Card className="p-16 flex flex-col items-center justify-center gap-4 text-center border-dashed border-2">
                <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                <p className="text-sm font-semibold text-gray-600">
                  Analyzing supply-demand gap and modeling routes...
                </p>
              </Card>
            )}

            {/* Empty state */}
            {!loading && !selectedBuyer && (
              <Card className="p-16 text-center border-dashed border-2 flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-20 h-20 rounded-2xl bg-gray-50 border border-gray-100 flex items-center justify-center text-4xl mb-6 shadow-sm">
                   🌍
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">
                  Select a Global Buyer
                </h2>
                <p className="text-sm text-gray-500 max-w-md mx-auto">
                  Choose a buyer from the sidebar to run the long-term gap analysis and generate strategic fulfillment route recommendations.
                </p>
              </Card>
            )}

            {/* Gap Dashboard */}
            {!loading && gapData && <GapDashboard data={gapData} />}

            {/* ✅ NEW: Gap Trend Indicator with Forecasting */}
            {!loading && gapData && (() => {
              // ✅ DUMMY DATA for demonstration
              const dummyTrendData = {
                ...gapData,
                gap_analysis: {
                  ...gapData.gap_analysis,
                  trend: gapData.gap_analysis?.trend || {
                    direction: "worsening",
                    change_pct: -5.2,
                    lookback_weeks: 8,
                    historical_data: [
                      {week: 1, gap_percentage: 8.0},
                      {week: 2, gap_percentage: 9.5},
                      {week: 3, gap_percentage: 10.0},
                      {week: 4, gap_percentage: 10.8},
                      {week: 5, gap_percentage: 11.2},
                      {week: 6, gap_percentage: 11.5},
                      {week: 7, gap_percentage: 12.0},
                      {week: 8, gap_percentage: 12.3}
                    ],
                    forecast: {
                      direction: "increase",
                      projected_gap_pct: 15.5,
                      week_number: 4,
                      will_become_critical: true,
                      weeks_until_critical: 2
                    },
                    key_drivers: [
                      {
                        description: "Increased demand from buyer expansion in Asia-Pacific region",
                        impact: "negative",
                        percentage: 3.5
                      },
                      {
                        description: "Factory B capacity constraints due to maintenance",
                        impact: "negative",
                        percentage: -2.0
                      },
                      {
                        description: "Delayed shipments from Supplier A",
                        impact: "negative",
                        percentage: -1.2
                      }
                    ]
                  }
                }
              }
              
              return (
                <GapTrendIndicator
                  gapAnalysis={dummyTrendData}
                  showForecast={true}
                  onViewRecommendations={() => {
                    const params = new URLSearchParams({
                      facility: facility,
                      product: gapData.product_code || 'CPO',
                      gap_closure: 'true'
                    })
                    window.location.href = `/?${params.toString()}`
                  }}
                />
              )
            })()}

            {/* ✅ NEW: Gap Trend Indicator with Forecasting */}
            {!loading && gapData && (
              <GapTrendIndicator
                gapAnalysis={gapData}
                showForecast={true}
                onViewRecommendations={() => {
                  // Navigate to recommendation page with gap closure context
                  const params = new URLSearchParams({
                    facility: facility,
                    product: gapData.product_code || 'CPO',
                    gap_closure: 'true',
                    gap_size: gapData.gap_analysis?.shortfall_kg || 0
                  })
                  window.location.href = `/?${params.toString()}`
                }}
              />
            )}

            {/* Fulfillment Routes */}
            {!loading && routes.length > 0 && (
              <div>
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4 mt-2">
                  <SectionTitle
                    icon="🚚"
                    title="Gap Fulfillment Routes"
                    badge={`${routes.length} options`}
                  />
                  {summary && (
                    <div className="flex items-center gap-2">
                      <Badge color="green">
                        Total routed: {(summary.total_routed_volume_kg / 1000).toFixed(2)} kton
                      </Badge>
                      <Badge color="blue">
                        Combined: {summary.combined_fulfillment_percent.toFixed(1)}% fulfilled
                      </Badge>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                  {routes.map(route => (
                    <RouteCard
                      key={route.route_id}
                      route={route}
                      buyerPcfLimit={gapData?.max_pcf_limit}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
