import React from "react"

export default function PcfNodePanel({ row }) {
  const pcfPerUnit = Number(row?.pcf_per_unit || 0)
  const pcfTotal = Number(row?.pcf_total || 0)
  const breakdown = row?.pcf_stage_breakdown || null

  if (pcfPerUnit <= 0 && pcfTotal <= 0) return null

  const PCF_BENCHMARK = 2.5
  const aboveBenchmark = pcfPerUnit > PCF_BENCHMARK

  const STAGES = breakdown ? [
    {
      key: "stage1_harvest_emission_kg_co2e",
      label: "Stage 1 — Harvest",
      icon: "🌴",
      desc: "CO₂e from harvesting fresh fruit bunches (FFB) at estate",
      color: "bg-emerald-500",
      textColor: "text-emerald-700",
      bg: "bg-emerald-50 border-emerald-100",
    },
    {
      key: "stage2_transport_estate_to_mill_kg_co2e",
      label: "Stage 2 — Transport Estate → Mill",
      icon: "🚛",
      desc: `Truck transport from estate to mill (~${breakdown.estate_to_mill_km ?? 85} km)`,
      color: "bg-yellow-500",
      textColor: "text-yellow-700",
      bg: "bg-yellow-50 border-yellow-100",
    },
    {
      key: "stage3_mill_processing_emission_kg_co2e",
      label: "Stage 3 — Mill Processing",
      icon: "🏭",
      desc: "CO₂e from CPO extraction and processing operations at the mill",
      color: "bg-amber-500",
      textColor: "text-amber-700",
      bg: "bg-amber-50 border-amber-100",
    },
    {
      key: "stage4_transport_mill_to_refinery_kg_co2e",
      label: "Stage 4 — Transport Mill → Refinery",
      icon: "🚢",
      desc: `Vessel / truck transport from mill to refinery (~${breakdown.mill_to_refinery_km ?? 420} km)`,
      color: "bg-orange-500",
      textColor: "text-orange-700",
      bg: "bg-orange-50 border-orange-100",
    },
    {
      key: "stage5_refinery_processing_emission_kg_co2e",
      label: "Stage 5 — Refinery Processing",
      icon: "⛽",
      desc: "CO₂e from refining, fractionation, and storage operations",
      color: "bg-blue-500",
      textColor: "text-blue-700",
      bg: "bg-blue-50 border-blue-100",
    },
  ] : []

  const totalBreakdown = breakdown?.total_pcf_kg_co2e || pcfTotal

  return (
    <div className="mt-5 rounded-xl border border-green-100 bg-gradient-to-br from-green-50/60 to-white overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-green-100">
        <div className="flex items-center gap-2">
          <span className="text-base">🌱</span>
          <div>
            <p className="text-xs font-bold text-green-800 uppercase tracking-wide">
              Carbon Footprint (PCF) — This Node
            </p>
            <p className="text-[10px] text-green-600 mt-0.5">
              {breakdown?.node_type || "Node"} · {breakdown?.product || row?.product || "—"}
              {breakdown?.quantity_kg ? ` · ${Number(breakdown.quantity_kg).toLocaleString("id-ID")} Kg` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-right">
            <p className="text-[9px] font-bold uppercase text-green-600">PCF Per Unit</p>
            <p className="text-base font-black text-green-900 leading-none">
              {pcfPerUnit.toFixed(4)} <span className="text-xs font-semibold">kg CO₂e/kg</span>
            </p>
          </div>
          <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold ${aboveBenchmark
              ? "bg-orange-100 border-orange-200 text-orange-700"
              : "bg-green-100 border-green-200 text-green-700"
            }`}>
            {aboveBenchmark ? "⚠ Above 2.5 benchmark" : "✓ Below 2.5 benchmark"}
          </span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Summary KPIs */}
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-green-100 bg-white px-3 py-2.5">
            <p className="text-[9px] font-bold uppercase tracking-wide text-gray-400">PCF Total (this node)</p>
            <p className="text-sm font-bold text-gray-900 mt-0.5">{pcfTotal.toFixed(2)} kg CO₂e</p>
          </div>
          <div className="rounded-xl border border-green-100 bg-white px-3 py-2.5">
            <p className="text-[9px] font-bold uppercase tracking-wide text-gray-400">PCF Per Unit</p>
            <p className="text-sm font-bold text-gray-900 mt-0.5">{pcfPerUnit.toFixed(4)} kg CO₂e/kg</p>
          </div>
        </div>

        {/* Per-stage breakdown */}
        {breakdown && (
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">
              Emission Breakdown by Stage
            </p>
            <div className="space-y-2">
              {STAGES.map(stage => {
                const val = Number(breakdown[stage.key] || 0)
                const pct = totalBreakdown > 0 ? (val / totalBreakdown * 100) : 0
                const isActive = val > 0
                return (
                  <div key={stage.key} className={`rounded-xl border px-3 py-2.5 ${isActive ? stage.bg : "bg-gray-50 border-gray-100 opacity-50"}`}>
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm">{stage.icon}</span>
                        <div>
                          <p className={`text-[10px] font-bold uppercase tracking-wide ${isActive ? stage.textColor : "text-gray-400"}`}>
                            {stage.label}
                          </p>
                          <p className="text-[9px] text-gray-400 leading-tight">{stage.desc}</p>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <p className={`text-sm font-black ${isActive ? "text-gray-900" : "text-gray-300"}`}>
                          {val.toFixed(2)} kg
                        </p>
                        {isActive && (
                          <p className="text-[9px] text-gray-400">{pct.toFixed(1)}% of total</p>
                        )}
                      </div>
                    </div>
                    {isActive && (
                      <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${stage.color} transition-all duration-500`}
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                    )}
                  </div>
                )
              })}

              {/* Total row */}
              <div className="rounded-xl border border-green-200 bg-green-50 px-3 py-2.5">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-green-800">⚡ Total Emission (this node)</p>
                  <p className="text-sm font-black text-green-900">{totalBreakdown.toFixed(2)} kg CO₂e</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Note */}
        <p className="text-[10px] text-gray-400 leading-relaxed">
          PCF is calculated using the 5-stage lifecycle emission model (harvest → transport → mill → transport → refinery).
          Stages showing 0 are not applicable for this node type.
        </p>
      </div>
    </div>
  )
}
