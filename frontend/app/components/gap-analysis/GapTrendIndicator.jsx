"use client"

import { useMemo } from "react"
import Card, { CardHeader, CardBody } from "../shared/Card"
import Badge, { TrendBadge } from "../shared/Badge"
import { formatPercentage, getTrendArrow } from "@/utils/formatters"
import { validateTrendData } from "@/utils/validators"

/**
 * Gap Trend Indicator Component
 * Shows week-over-week trends and predictive forecasts for supply gaps
 * 
 * USER STORY:
 * As a Supply Chain Planner, I want to see gap trends and predictions
 * so that I can take proactive action before gaps become critical
 * and allocate resources to address worsening situations.
 */

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

export default function GapTrendIndicator({ 
  gapAnalysis,
  showForecast = true,
  onViewRecommendations 
}) {
  // Validate trend data
  const trendData = gapAnalysis?.trend || {}
  const isValidTrend = useMemo(() => validateTrendData(trendData), [trendData])
  
  if (!isValidTrend) {
    return null
  }
  
  const trendConfig = TREND_CONFIG[trendData.direction] || TREND_CONFIG.stable
  const forecast = trendData.forecast || {}
  const hasWarning = forecast.will_become_critical || trendData.direction === 'worsening'
  
  // Calculate sparkline data for mini chart
  const sparklineData = useMemo(() => {
    if (!trendData.historical_data || !Array.isArray(trendData.historical_data)) {
      return []
    }
    
    return trendData.historical_data.slice(-8) // Last 8 weeks
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
            value={Math.abs(trendData.change_pct || 0)}
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
                    {getTrendArrow(trendData.direction)}
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
                {trendData.change_pct > 0 ? '+' : ''}{trendData.change_pct?.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
        
        {/* Sparkline Visualization */}
        {sparklineData.length > 0 && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-gray-400 mb-2">
              Last {trendData.lookback_weeks || 4} Weeks
            </p>
            <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
              <div className="flex items-end justify-between gap-1 h-24">
                {sparklineData.map((point, index) => {
                  const maxValue = Math.max(...sparklineData.map(p => p.gap_percentage))
                  const height = (point.gap_percentage / maxValue) * 100
                  const isLast = index === sparklineData.length - 1
                  const isIncreasing = index > 0 && point.gap_percentage > sparklineData[index - 1].gap_percentage
                  
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
                          style={{ height: `${height}px` }}
                          title={`Week ${point.week}: ${formatPercentage(point.gap_percentage, false, 1)}`}
                        />
                        
                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                          <div className="bg-gray-900 text-white text-xs rounded-lg px-2 py-1 whitespace-nowrap">
                            W{point.week}: {formatPercentage(point.gap_percentage, false, 1)}
                          </div>
                        </div>
                      </div>
                      
                      <span className="text-[9px] text-gray-400 font-medium">
                        W{point.week}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
        
        {/* Predictive Forecast */}
        {showForecast && forecast.projected_gap_pct !== undefined && (
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
                If current trend continues, gap will {forecast.direction} to{" "}
                <strong>{formatPercentage(forecast.projected_gap_pct, false, 1)}</strong>{" "}
                by week {forecast.week_number}
              </p>
              
              {forecast.will_become_critical && (
                <div className="mt-3 pt-3 border-t border-red-200">
                  <p className="text-xs font-bold text-red-800 flex items-center gap-1">
                    <span aria-hidden="true">🚨</span>
                    Will reach CRITICAL status in {forecast.weeks_until_critical} week
                    {forecast.weeks_until_critical !== 1 ? 's' : ''}
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
                  <p className="text-xs text-gray-700 flex-1">{driver.description}</p>
                  {driver.percentage && (
                    <span className="text-xs font-bold text-gray-900 shrink-0">
                      {driver.percentage > 0 ? '+' : ''}{driver.percentage}%
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
        
        {/* Intervention Scenarios (if trend is worsening) */}
        {trendData.direction === 'worsening' && trendData.intervention_scenarios && (
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
                      <p className="text-xs font-bold text-blue-800">{scenario.name}</p>
                      <p className="text-xs text-blue-600 mt-1">{scenario.description}</p>
                    </div>
                    <Badge color="blue" size="xs">
                      {scenario.expected_improvement}
                    </Badge>
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