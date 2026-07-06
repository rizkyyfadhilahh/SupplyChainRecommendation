"use client"

import { useMemo, useState } from "react"
import { formatCO2, formatPercentage } from "@/utils/formatters"
import { validatePCFBreakdown } from "@/utils/validators"
import Card, { CardHeader, CardBody } from "../shared/Card"
import Badge from "../shared/Badge"
import DummyDataBadge from "../shared/DummyDataBadge"

const STAGE_CONFIG = [
  {
    key: "stage1_harvest_emission_kg_co2e",
    label: "Harvest",
    shortLabel: "Harvest",
    color: "#10b981",
    hoverColor: "#059669",
    bgClass: "bg-emerald-50 border-emerald-200",
    textClass: "text-emerald-700",
    icon: "🌱",
    description: "Field harvesting operations",
  },
  {
    key: "stage2_transport_estate_to_mill_kg_co2e",
    label: "Estate → Mill Transport",
    shortLabel: "E→M Transport",
    color: "#eab308",
    hoverColor: "#ca8a04",
    bgClass: "bg-yellow-50 border-yellow-200",
    textClass: "text-yellow-700",
    icon: "🚚",
    description: "Transport from estate to mill",
  },
  {
    key: "stage3_mill_processing_emission_kg_co2e",
    label: "Mill Processing",
    shortLabel: "Mill",
    color: "#f59e0b",
    hoverColor: "#d97706",
    bgClass: "bg-amber-50 border-amber-200",
    textClass: "text-amber-700",
    icon: "🏭",
    description: "Palm oil mill processing",
  },
  {
    key: "stage4_transport_mill_to_refinery_kg_co2e",
    label: "Mill → Refinery Transport",
    shortLabel: "M→R Transport",
    color: "#f97316",
    hoverColor: "#ea580c",
    bgClass: "bg-orange-50 border-orange-200",
    textClass: "text-orange-700",
    icon: "🚛",
    description: "Transport from mill to refinery",
  },
  {
    key: "stage5_refinery_processing_emission_kg_co2e",
    label: "Refinery Processing",
    shortLabel: "Refinery",
    color: "#3b82f6",
    hoverColor: "#2563eb",
    bgClass: "bg-blue-50 border-blue-200",
    textClass: "text-blue-700",
    icon: "⛽",
    description: "Refinery processing stage",
  },
]

function DonutChart({ segments, activeIndex, onHover, onLeave }) {
  const SIZE = 220
  const CENTER = SIZE / 2
  const OUTER_R = 88
  const INNER_R = 52
  const GAP_DEG = 1.5

  const paths = useMemo(() => {
    let cumulative = 0
    return segments.map((seg, i) => {
      const startDeg = cumulative
      const spanDeg = Math.max((seg.percentage / 100) * 360 - GAP_DEG, 0.1)
      const endDeg = startDeg + spanDeg
      cumulative += (seg.percentage / 100) * 360

      const toRad = (d) => ((d - 90) * Math.PI) / 180
      const s = toRad(startDeg)
      const e = toRad(endDeg)
      const r = activeIndex === i ? OUTER_R + 7 : OUTER_R

      const x1 = CENTER + r * Math.cos(s)
      const y1 = CENTER + r * Math.sin(s)
      const x2 = CENTER + r * Math.cos(e)
      const y2 = CENTER + r * Math.sin(e)
      const ix1 = CENTER + INNER_R * Math.cos(s)
      const iy1 = CENTER + INNER_R * Math.sin(s)
      const ix2 = CENTER + INNER_R * Math.cos(e)
      const iy2 = CENTER + INNER_R * Math.sin(e)
      const large = spanDeg > 180 ? 1 : 0

      const d = [
        `M ${x1} ${y1}`,
        `A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`,
        `L ${ix2} ${iy2}`,
        `A ${INNER_R} ${INNER_R} 0 ${large} 0 ${ix1} ${iy1}`,
        "Z",
      ].join(" ")

      return { ...seg, d, index: i }
    })
  }, [segments, activeIndex])

  const active = activeIndex !== null ? segments[activeIndex] : null
  const totalValue = segments.reduce((s, r) => s + r.value, 0)

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="w-full max-w-[260px] h-auto drop-shadow-sm"
      role="img"
      aria-label="PCF stage breakdown donut chart"
    >
      <circle
        cx={CENTER}
        cy={CENTER}
        r={(OUTER_R + INNER_R) / 2}
        fill="none"
        stroke="#f3f4f6"
        strokeWidth={OUTER_R - INNER_R}
      />

      {paths.map((seg) => (
        <path
          key={seg.key}
          d={seg.d}
          fill={activeIndex === seg.index ? seg.hoverColor : seg.color}
          className="transition-all duration-200 cursor-pointer"
          onMouseEnter={() => onHover(seg.index)}
          onMouseLeave={onLeave}
          role="img"
          aria-label={`${seg.label}: ${seg.formattedPercentage}`}
        >
          <title>{`${seg.label}: ${seg.formattedValue} (${seg.formattedPercentage})`}</title>
        </path>
      ))}

      {active ? (
        <>
          <text x={CENTER} y={CENTER - 20} textAnchor="middle" fontSize="22" dominantBaseline="middle">
            {active.icon}
          </text>
          <text
            x={CENTER}
            y={CENTER + 4}
            textAnchor="middle"
            fontSize="14"
            fontWeight="800"
            fill="#111827"
            dominantBaseline="middle"
          >
            {active.formattedPercentage}
          </text>
          <text
            x={CENTER}
            y={CENTER + 20}
            textAnchor="middle"
            fontSize="8"
            fill="#6b7280"
            dominantBaseline="middle"
          >
            {active.shortLabel}
          </text>
        </>
      ) : (
        <>
          <text
            x={CENTER}
            y={CENTER - 10}
            textAnchor="middle"
            fontSize="8"
            fontWeight="600"
            fill="#9ca3af"
            dominantBaseline="middle"
          >
            TOTAL PCF
          </text>
          <text
            x={CENTER}
            y={CENTER + 8}
            textAnchor="middle"
            fontSize="13"
            fontWeight="800"
            fill="#111827"
            dominantBaseline="middle"
          >
            {totalValue > 0 ? formatCO2(totalValue, "t") : "—"}
          </text>
        </>
      )}
    </svg>
  )
}

export default function PcfPieChart({
  pcfBreakdown,
  title = "PCF Stage Breakdown",
  buyerMaxPcf,
}) {
  const [activeIndex, setActiveIndex] = useState(null)

  const isValid = useMemo(() => validatePCFBreakdown(pcfBreakdown), [pcfBreakdown])

  const chartData = useMemo(() => {
    if (!isValid) return []
    const total = pcfBreakdown.total_kg_co2e || 0
    if (total === 0) return []

        const stages = STAGE_CONFIG.map((stage) => {
      const value = pcfBreakdown[stage.key] || 0
      return { ...stage, value }
    }).filter((item) => item.value > 0)

    // Hitung total dari stages yang benar-benar ditampilkan
    // supaya persentase selalu menjumlah tepat 100%
    const displayedTotal = stages.reduce((sum, s) => sum + s.value, 0)
    if (displayedTotal === 0) return []

    return stages.map((stage) => {
      const percentage = (stage.value / displayedTotal) * 100
      return {
        ...stage,
        percentage,
        formattedValue: formatCO2(stage.value, "kg"),
        formattedPercentage: formatPercentage(percentage, false, 1),
      }
    })
  }, [pcfBreakdown, isValid])

    const displayedTotal = useMemo(
    () => chartData.reduce((sum, s) => sum + s.value, 0),
    [chartData]
  )
  const pcfIntensity = pcfBreakdown?.pcf_per_unit_kg_co2e_per_kg || 0
  const isCompliant = buyerMaxPcf ? pcfIntensity <= buyerMaxPcf : null
  const topContributor = chartData.length
    ? chartData.reduce((m, i) => (i.percentage > m.percentage ? i : m), chartData[0])
    : null

  if (!isValid || chartData.length === 0) {
    return (
      <Card>
        <CardHeader icon="📊" title={title} subtitle="No PCF data available" />
        <CardBody>
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-gray-400">
            <span className="text-4xl">🌿</span>
            <p className="text-sm">PCF breakdown data is not available for this recommendation</p>
          </div>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card>
            <CardHeader
        icon="📊"
        title={title}
        subtitle={`Total: ${formatCO2(displayedTotal, "t")} · ${chartData.length} stage${chartData.length !== 1 ? "s" : ""}`}
        badge={
          <div className="flex items-center gap-2">
            <DummyDataBadge tooltip="PCF values are modelled estimates based on emission factors, not measured operational data." />
            {isCompliant !== null && (
              <Badge color={isCompliant ? "green" : "red"} size="sm">
                {isCompliant ? "✓ Compliant" : "⚠ Exceeds Limit"}
              </Badge>
            )}
          </div>
        }
      />

      <CardBody>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Left — Donut chart + intensity + legend pills */}
          <div className="flex flex-col items-center gap-4">
            <DonutChart
              segments={chartData}
              activeIndex={activeIndex}
              onHover={setActiveIndex}
              onLeave={() => setActiveIndex(null)}
            />

            {/* PCF Intensity */}
            <div className="w-full rounded-xl border border-gray-100 bg-gray-50 px-4 py-3 text-center">
              <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400 mb-1">
                PCF Intensity
              </p>
              <p
                className={`text-2xl font-black ${
                  isCompliant === null
                    ? "text-gray-900"
                    : isCompliant
                    ? "text-emerald-600"
                    : "text-red-600"
                }`}
              >
                {pcfIntensity.toFixed(4)}
                <span className="text-sm font-semibold text-gray-400 ml-1">tCO₂e/ton</span>
              </p>
              {buyerMaxPcf && (
                <p className="text-xs text-gray-500 mt-1">
                  Buyer limit:{" "}
                  <span className="font-bold">{buyerMaxPcf.toFixed(4)} tCO₂e/ton</span>
                </p>
              )}
            </div>

            {/* Legend pills */}
            <div className="flex flex-wrap justify-center gap-1.5">
              {chartData.map((item, i) => (
                <button
                  key={item.key}
                  onMouseEnter={() => setActiveIndex(i)}
                  onMouseLeave={() => setActiveIndex(null)}
                  className={`flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-bold transition-all duration-150 ${
                    activeIndex === i
                      ? `${item.bgClass} scale-105 shadow-sm`
                      : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
                  }`}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  {item.shortLabel}
                </button>
              ))}
            </div>
          </div>

          {/* Right — Stage breakdown rows */}
          <div className="flex flex-col justify-center gap-2">
            {chartData.map((item, i) => (
              <div
                key={item.key}
                onMouseEnter={() => setActiveIndex(i)}
                onMouseLeave={() => setActiveIndex(null)}
                onFocus={() => setActiveIndex(i)}
                onBlur={() => setActiveIndex(null)}
                className={`rounded-xl border px-4 py-3 cursor-pointer transition-all duration-150 ${
                  activeIndex === i
                    ? `${item.bgClass} shadow-sm scale-[1.01]`
                    : "border-gray-100 bg-gray-50 hover:border-gray-200"
                }`}
                role="button"
                tabIndex={0}
                aria-label={`${item.label}: ${item.formattedValue}`}
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span
                      className="w-2.5 h-2.5 rounded-sm shrink-0"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm shrink-0">{item.icon}</span>
                    <div className="min-w-0">
                      <p
                        className={`text-xs font-bold truncate ${
                          activeIndex === i ? item.textClass : "text-gray-700"
                        }`}
                      >
                        {item.label}
                      </p>
                      <p className="text-[10px] text-gray-400">{item.description}</p>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-black text-gray-900">
                      {item.formattedPercentage}
                    </p>
                    <p className="text-[10px] text-gray-400">{item.formattedValue}</p>
                  </div>
                </div>

                <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${item.percentage}%`,
                      backgroundColor: item.color,
                      opacity: activeIndex === null || activeIndex === i ? 1 : 0.35,
                    }}
                  />
                </div>
              </div>
            ))}

            {topContributor && (
              <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 mt-1">
                <p className="text-xs font-bold text-blue-800 flex items-center gap-1 mb-1">
                  <span>💡</span> Top Contributor
                </p>
                <p className="text-xs text-blue-600 leading-relaxed">
                  <strong>{topContributor.label}</strong> accounts for{" "}
                  <strong>{topContributor.formattedPercentage}</strong> of total emissions.
                  Focus reduction here for maximum impact.
                </p>
              </div>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}
