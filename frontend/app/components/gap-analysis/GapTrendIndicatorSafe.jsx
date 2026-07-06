"use client"

import { useMemo } from "react"
import Card, { CardHeader, CardBody } from "../shared/Card"
import Badge, { TrendBadge } from "../shared/Badge"

/**
 * Gap Trend Indicator Component - SAFE VERSION
 * Shows week-over-week trends and predictive forecasts for supply gaps
 * 
 * This version includes comprehensive error handling and fallbacks
 */

// Safe formatters with fallbacks
const safeFormatPercentage = (value, decimals = 1) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0%"
  return num.toFixed(decimals) + "%"
}

const safeTrendArrow = (direction) => {
  const arrows = {
    improving: "↘",
    worsening: "↗",
    stable: "→",
    up: "↗",
    down: "↘"
  }
  return arrows[direction] || "→"
}

// Safe validator
const isValidTrendData = (data) => {
  if (!data || typeof data !== 'object') return false
  if (!data.direction || typeof data.direction !== 'string') return false
  if (data.change_pct === undefined || !Number.isFinite(Number(data.change_pct))) return false
  return true
}

const TREND_CONFIG = {
  improving: {
    color: "green",
    icon: "📉",
    bgClass: "bg-green-50 border-green-200",
    textClass: "text-green-700",
    label: "Improving",
    description: "Gap is shrinking compared to previous periods"
  },
  worsening: {
    color: "red",
    icon: "📈",
    bgClass: "bg-red-50 border-red-200",
    textClass: "text-red-700",
    label: "Worsening",
    description: "Gap is widening and requires immediate attention"
  },
  stable: {
    color: "gray",
    icon: "➡️",
    bgClass: "bg-gray-50 border-gray-200",
    textClass: "text-gray-700",
    label: "Stable",
    description: "Gap remains relatively constant"
  }
}

export default function GapTrendIndicatorSafe({ 
  gapAnalysis,
  showForecast = true,
  onViewRecommendations 
}) {
  // Safe data extraction
  const trendData = useMemo(() => {
    return gapAnalysis?.trend || gapAnalysis?.gap_analysis?.trend || {}
  }, [gapAnalysis])
  
  // Validate trend data
  const isValid = useMemo(() => isValidTrendData(trendData), [trendData])
  
  // Early return if invalid
  if (!isValid) {
    console.warn('GapTrendIndicator: Invalid or missing trend data', trendData)
    return null
  }
  
  const trendConfig = TREND_CONFIG[trendData.direction] || TREND_CONFIG.stable
  const forecast = trendData.forecast || {}
  const hasWarning = forecast.will_become_critical || trendData.direction === 'worsening'
  
  // Safe sparkline data calculation
  const sparklineData = useMemo(() => {
    if (!trendData.historical_data || !Array.isArray(trendData.historical_data)) {
      return []
    }
    
    return trendData.historical_data
      .filter(point => point && typeof point.gap_percentage === 'number')
      .slice(-8)
  }, [trendData.historical_data])
  
  return (
    <Card>
      <CardHeader
        icon="📊"
        title="Gap Trend Analysis"
        subtitle="Week-over-week gap movement and predictive forecast"
        badge={
          <TrendBadge 
            direction={trendData.direction} 
            value={Math.abs(Number(trendData.change_pct) || 0)}
          />
        }
      />
      
      <CardBody className="space-y-4">
        {/* Current Trend Status */}
        <div className={`rounded-xl border px-4 py-3 ${trendConfig.bgClass}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2 flex-1">
              <span className="text-2xl" aria-hidden="true">{trendConfig.icon}</span>
              <div className="flex-1">
                <p className={`text-sm font-bold ${trendConfig.textClass} flex items-center gap-2`}>
                  {trendConfig.label} Trend
                  <span className="text-base" aria-hidden="true">
                    {safeTrendArrow(trendData.direction)}
                  </span>
                </p>
                <p className={`text-xs mt-1 ${trendConfig.textClass} opacity-90`}>
                  {trendConfig.description}
                </p>
              </div>
            </div>
            
            <div className="text-right shrink-0">
              <p className="text-xs text-gray-500 font-semibold">Change (WoW)</p>
              <p className={`text-xl font-black ${trendConfig.textClass}`}>
                {Number(trendData.change_pct) > 0 ? '+' : ''}
                {Number(trendData.change_pct || 0).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
        
        {/* Sparkline Visualization */}
        {sparklineData.length > 0 && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-gray-400 mb-2">
              Last {trendData.lookback_weeks || sparklineData.length} Weeks
            </p>
            <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
              <div className="flex items-end justify-between gap-1 h-24">
                {sparklineData.map((point, index) => {
                  const allValues = sparklineData.map(p => Number(p.gap_percentage) || 0)
                  const maxValue = Math.max(...allValues, 1) // Prevent division by zero
                  const height = Math.min(((Number(point.gap_percentage) || 0) / maxValue) * 96, 96) // Max 96px (h-24)
                  const isLast = index === sparklineData.length - 1
                  const prevValue = index > 0 ? Number(sparklineData[index - 1].gap_percentage) || 0 : 0
                  const currValue = Number(point.gap_percentage) || 0
                  const isIncreasing = index > 0 && currValue > prevValue
                  
                  return (
                    <div 
                      key={point.week || index}
                      className="flex-1 flex flex-col items-center gap-1 group"
                    >
                      <div className="relative w-full">
                        <div 
                          className={`w-full rounded-t transition-all ${
                            isLast ? 'bg-blue-500' :
                            isIncreasing ? 'bg-red-400' : 'bg-green-400'
                          } group-hover:opacity-75`}
                          style={{ height: `${height}px`, minHeight: '4px' }}
                          title={`Week ${point.week || index + 1}: ${safeFormatPercentage(point.gap_percentage)}`}
                        />
                        
                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                          <div className="bg-gray-900 text-white text-xs rounded-lg px-2 py-1 whitespace-nowrap">
                            W{point.week || index + 1}: {safeFormatPercentage(point.gap_percentage)}
                          </div>
                        </div>
                      </div>
                      
                      <span className="text-[9px] text-gray-400 font-medium">
                        W{point.week || index + 1}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
        
        {/* Predictive Forecast */}
        {showForecast && forecast.projected_gap_pct !== undefined && Number.isFinite(Number(forecast.projected_gap_pct)) && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-gray-400 mb-2">
              📈 Predictive Forecast (Next {forecast.week_number || 4} Weeks)
            </p>
            
            <div className={`rounded-xl border px-4 py-3 ${
              forecast.will_become_critical 
                ? 'bg-red-50 border-red-200' 
                : 'bg-blue-50 border-blue-200'
            }`}>
              <p className={`text-sm font-semibold ${
                forecast.will_become_critical ? 'text-red-800' : 'text-blue-800'
              }`}>
                {forecast.will_become_critical ? '⚠️ Critical Alert' : 'ℹ️ Forecast'}
              </p>
              
              <p className={`text-xs mt-1 ${
                forecast.will_become_critical ? 'text-red-600' : 'text-blue-600'
              }`}>
                If current trend continues, gap will {forecast.direction || 'change'} to{" "}
                <strong>{safeFormatPercentage(forecast.projected_gap_pct)}</strong>{" "}
                by week {forecast.week_number || 4}
              </p>
              
              {forecast.will_become_critical && forecast.weeks_until_critical && (
                <div className="mt-3 pt-3 border-t border-red-200">
                  <p className="text-xs font-bold text-red-800 flex items-center gap-1">
                    <span aria-hidden="true">🚨</span>
                    Will reach CRITICAL status in {forecast.weeks_until_critical} week
                    {Number(forecast.weeks_until_critical) !== 1 ? 's' : ''}
                  </p>
                  <p className="text-xs text-red-600 mt-1">
                    Immediate intervention required to prevent supply chain disruption
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Key Drivers */}
        {trendData.key_drivers && Array.isArray(trendData.key_drivers) && trendData.key_drivers.length > 0 && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-gray-400 mb-2">
              Key Drivers
            </p>
            <div className="space-y-2">
              {trendData.key_drivers.map((driver, index) => (
                <div 
                  key={index}
                  className="rounded-lg border border-gray-100 bg-white px-3 py-2 flex items-center gap-2"
                >
                  <span 
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      driver.impact === 'negative' ? 'bg-red-500' :
                      driver.impact === 'positive' ? 'bg-green-500' : 'bg-gray-400'
                    }`}
                    aria-hidden="true"
                  />
                  <p className="text-xs text-gray-700 flex-1">{driver.description || 'Unknown driver'}</p>
                  {driver.percentage !== undefined && Number.isFinite(Number(driver.percentage)) && (
                    <span className="text-xs font-bold text-gray-900 shrink-0">
                      {Number(driver.percentage) > 0 ? '+' : ''}{Number(driver.percentage).toFixed(1)}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Action Button */}
        {hasWarning && onViewRecommendations && (
          <button
            onClick={onViewRecommendations}
            className="w-full rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-sm font-bold px-4 py-3 transition flex items-center justify-center gap-2"
          >
            <span aria-hidden="true">🔍</span>
            View Gap Closure Recommendations
            <span aria-hidden="true">→</span>
          </button>
        )}
        
        {/* Intervention Scenarios */}
        {trendData.direction === 'worsening' && 
         trendData.intervention_scenarios && 
         Array.isArray(trendData.intervention_scenarios) &&
         trendData.intervention_scenarios.length > 0 && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-gray-400 mb-2">
              💡 Intervention Scenarios
            </p>
            <div className="space-y-2">
              {trendData.intervention_scenarios.map((scenario, index) => (
                <div 
                  key={index}
                  className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className="text-xs font-bold text-blue-800">{scenario.name || 'Unnamed scenario'}</p>
                      <p className="text-xs text-blue-600 mt-1">{scenario.description || 'No description available'}</p>
                    </div>
                    {scenario.expected_improvement && (
                      <Badge color="blue" size="xs">
                        {scenario.expected_improvement}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}