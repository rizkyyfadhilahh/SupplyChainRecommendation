"use client"

import { useMemo } from "react"
import { formatCO2, formatPercentage } from "@/utils/formatters"
import { validatePCFBreakdown } from "@/utils/validators"
import Card, { CardHeader, CardBody } from "../shared/Card"
import Badge from "../shared/Badge"

/**
 * Interactive PCF Pie Chart with stage breakdown
 * Shows carbon footprint distribution across supply chain stages
 */

const STAGE_CONFIG = [
  {
    key: "stage1_harvest_emission_kg_co2e",
    label: "Harvest",
    shortLabel: "Harvest",
    color: "#10b981", // emerald-500
    icon: "🌱"
  },
  {
    key: "stage2_transport_estate_to_mill_kg_co2e",
    label: "Estate → Mill Transport",
    shortLabel: "E→M Trans",
    color: "#eab308", // yellow-500
    icon: "🚚"
  },
  {
    key: "stage3_mill_processing_emission_kg_co2e",
    label: "Mill Processing",
    shortLabel: "Mill",
    color: "#f59e0b", // amber-500
    icon: "🏭"
  },
  {
    key: "stage4_transport_mill_to_refinery_kg_co2e",
    label: "Mill → Refinery Transport",
    shortLabel: "M→R Trans",
    color: "#f97316", // orange-500
    icon: "🚛"
  },
  {
    key: "stage5_refinery_processing_emission_kg_co2e",
    label: "Refinery Processing",
    shortLabel: "Refinery",
    color: "#3b82f6", // blue-500
    icon: "⛽"
  }
]

export default function PcfPieChart({ pcfBreakdown, title = "PCF Stage Breakdown", buyerMaxPcf }) {
  // Validate data
  const isValid = useMemo(() => validatePCFBreakdown(pcfBreakdown), [pcfBreakdown])
  
  // Calculate stage percentages and prepare chart data
  const chartData = useMemo(() => {
    if (!isValid) return []
    
    const total = pcfBreakdown.total_kg_co2e || 0
    if (total === 0) return []
    
    return STAGE_CONFIG.map(stage => {
      const value = pcfBreakdown[stage.key] || 0
      const percentage = (value / total) * 100
      
      return {
        ...stage,
        value,
        percentage,
        formattedValue: formatCO2(value, 'kg'),
        formattedPercentage: formatPercentage(percentage, false, 1)
      }
    }).filter(item => item.value > 0)
  }, [pcfBreakdown, isValid])
  
  // SVG Pie chart generation
  const pieSegments = useMemo(() => {
    let cumulativePercent = 0
    
    return chartData.map((item, index) => {
      const startAngle = (cumulativePercent / 100) * 360
      const endAngle = ((cumulativePercent + item.percentage) / 100) * 360
      
      cumulativePercent += item.percentage
      
      // Convert to radians
      const startRad = (startAngle - 90) * (Math.PI / 180)
      const endRad = (endAngle - 90) * (Math.PI / 180)
      
      // Calculate arc path
      const x1 = 100 + 80 * Math.cos(startRad)
      const y1 = 100 + 80 * Math.sin(startRad)
      const x2 = 100 + 80 * Math.cos(endRad)
      const y2 = 100 + 80 * Math.sin(endRad)
      
      const largeArc = item.percentage > 50 ? 1 : 0
      
      const pathData = [
        `M 100 100`,
        `L ${x1} ${y1}`,
        `A 80 80 0 ${largeArc} 1 ${x2} ${y2}`,
        `Z`
      ].join(' ')
      
      return {
        ...item,
        path: pathData,
        midAngle: (startAngle + endAngle) / 2
      }
    })
  }, [chartData])
  
  // Calculate compliance status
  const pcfIntensity = pcfBreakdown?.pcf_per_unit_kg_co2e_per_kg || 0
  const isCompliant = buyerMaxPcf ? pcfIntensity <= buyerMaxPcf : null
  
  if (!isValid || chartData.length === 0) {
    return (
      <Card>
        <CardHeader 
          icon="📊" 
          title={title}
          subtitle="No PCF data available"
        />
        <CardBody>
          <div className="flex items-center justify-center py-12 text-gray-400">
            <p className="text-sm">PCF breakdown data is not available for this recommendation</p>
          </div>
        </CardBody>
      </Card>
    )
  }
  
  const total = pcfBreakdown.total_kg_co2e || 0
  const topContributor = chartData.reduce((max, item) => 
    item.percentage > max.percentage ? item : max
  , chartData[0])
  
  return (
    <Card>
      <CardHeader 
        icon="📊" 
        title={title}
        subtitle={`Total: ${formatCO2(total, 't')} across ${chartData.length} stages`}
        badge={
          isCompliant !== null && (
            <Badge color={isCompliant ? "green" : "red"} size="sm">
              {isCompliant ? "✓ Compliant" : "⚠ Exceeds Limit"}
            </Badge>
          )
        }
      />
      
      <CardBody>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pie Chart Visualization */}
          <div className="flex flex-col items-center justify-center">
            <svg 
              viewBox="0 0 200 200" 
              className="w-full max-w-[280px] h-auto"
              role="img"
              aria-label="PCF stage breakdown pie chart"
            >
              {pieSegments.map((segment, index) => (
                <g key={segment.key}>
                  <path
                    d={segment.path}
                    fill={segment.color}
                    stroke="white"
                    strokeWidth="2"
                    className="transition-all duration-300 hover:opacity-80 cursor-pointer"
                    role="img"
                    aria-label={`${segment.label}: ${segment.formattedPercentage}`}
                  >
                    <title>{`${segment.label}: ${segment.formattedValue} (${segment.formattedPercentage})`}</title>
                  </path>
                </g>
              ))}
              
              {/* Center circle with total */}
              <circle cx="100" cy="100" r="50" fill="white" stroke="#e5e7eb" strokeWidth="2" />
              <text 
                x="100" 
                y="95" 
                textAnchor="middle" 
                className="text-xs font-bold fill-gray-400"
              >
                Total PCF
              </text>
              <text 
                x="100" 
                y="110" 
                textAnchor="middle" 
                className="text-sm font-black fill-gray-900"
              >
                {formatCO2(total, 't')}
              </text>
            </svg>
            
            {/* Intensity indicator */}
            <div className="mt-4 text-center">
              <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">PCF Intensity</p>
              <p className={`text-lg font-black mt-1 ${
                isCompliant === null ? "text-gray-900" :
                isCompliant ? "text-green-600" : "text-red-600"
              }`}>
                {pcfIntensity.toFixed(4)} tCO₂e/ton
              </p>
              {buyerMaxPcf && (
                <p className="text-xs text-gray-500 mt-0.5">
                  Buyer limit: {buyerMaxPcf.toFixed(4)} tCO₂e/ton
                </p>
              )}
            </div>
          </div>
          
          {/* Stage Legend & Details */}
          <div className="flex flex-col justify-center space-y-2">
            {chartData.map((item, index) => (
              <div 
                key={item.key}
                className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3 hover:bg-gray-100 transition-colors cursor-pointer group"
                role="button"
                tabIndex={0}
                aria-label={`${item.label}: ${item.formattedValue}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span 
                      className="w-3 h-3 rounded-sm shrink-0" 
                      style={{ backgroundColor: item.color }}
                      aria-hidden="true"
                    />
                    <span className="text-xs shrink-0" aria-hidden="true">{item.icon}</span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-gray-700 truncate">
                        {item.label}
                      </p>
                      <p className="text-[10px] text-gray-500 mt-0.5">
                        Stage {index + 1}
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-gray-900">
                      {item.formattedPercentage}
                    </p>
                    <p className="text-[10px] text-gray-500 mt-0.5">
                      {item.formattedValue}
                    </p>
                  </div>
                </div>
                
                {/* Progress bar */}
                <div className="mt-2 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-500 group-hover:opacity-80"
                    style={{ 
                      width: `${item.percentage}%`,
                      backgroundColor: item.color
                    }}
                    aria-hidden="true"
                  />
                </div>
              </div>
            ))}
            
            {/* Insight Card */}
            <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 mt-2">
              <p className="text-xs font-bold text-blue-800 flex items-center gap-1">
                <span aria-hidden="true">💡</span>
                Top Contributor
              </p>
              <p className="text-xs text-blue-600 mt-1">
                <strong>{topContributor.label}</strong> accounts for{" "}
                <strong>{topContributor.formattedPercentage}</strong> of total emissions.
                Focus reduction efforts here for maximum impact.
              </p>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}