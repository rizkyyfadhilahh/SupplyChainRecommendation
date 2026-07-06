"use client"

import { useState, useEffect } from "react"
import Card, { CardHeader, CardBody } from "../shared/Card"
import Badge from "../shared/Badge"
import { formatCurrency, formatDays } from "@/utils/formatters"
import { getBlastRadiusImpact } from "@/services/drilldownService"
import { validateBlastRadiusImpact } from "@/utils/validators"

/**
 * Blast Radius Impact Panel
 * Shows downstream impact analysis when a node experiences disruption
 * 
 * USER STORY:
 * As a Supply Chain Manager, I want to see the blast radius impact of a disruption
 * so that I can quickly assess affected customers and take proactive action
 * to minimize revenue loss and maintain customer relationships.
 */

const SEVERITY_CONFIG = {
  critical: {
    color: "red",
    icon: "🔴",
    bgClass: "bg-red-50 border-red-200",
    textClass: "text-red-700",
    label: "Critical"
  },
  moderate: {
    color: "orange",
    icon: "🟠",
    bgClass: "bg-orange-50 border-orange-200",
    textClass: "text-orange-700",
    label: "Moderate"
  },
  minor: {
    color: "yellow",
    icon: "🟡",
    bgClass: "bg-yellow-50 border-yellow-200",
    textClass: "text-yellow-700",
    label: "Minor"
  }
}

const IMPACT_TYPES = {
  inventory_depletion: "Inventory Depletion",
  delivery_delay: "Delivery Delay",
  quality_risk: "Quality Risk",
  capacity_overflow: "Capacity Overflow",
  revenue_loss: "Revenue Loss"
}

export default function BlastRadiusPanel({ 
  selectedNode, 
  supplyChainData,
  onMitigationRequest 
}) {
  const [blastRadiusData, setBlastRadiusData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedScenario, setSelectedScenario] = useState('delay_3days')
  
  // Load blast radius data when node is selected
  useEffect(() => {
    if (!selectedNode) {
      setBlastRadiusData(null)
      return
    }
    
    loadBlastRadius()
  }, [selectedNode, selectedScenario])
  
  const loadBlastRadius = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const scenarioMap = {
        'delay_3days': { type: 'delay', durationDays: 3, severity: 'moderate' },
        'delay_7days': { type: 'delay', durationDays: 7, severity: 'critical' },
        'shutdown': { type: 'shutdown', durationDays: 14, severity: 'critical' },
        'capacity_50': { type: 'capacity_reduction', durationDays: 30, severity: 'moderate' }
      }
      
      const scenario = scenarioMap[selectedScenario] || scenarioMap.delay_3days
      
      const data = await getBlastRadiusImpact(
        selectedNode.id || selectedNode.supplier_id,
        selectedNode.type || selectedNode.supplier_type,
        scenario
      )
      
      // Validate impacted nodes
      const validNodes = (data.impacted_nodes || []).filter(validateBlastRadiusImpact)
      
      setBlastRadiusData({
        ...data,
        impacted_nodes: validNodes
      })
      
    } catch (err) {
      console.error('Blast radius error:', err)
      setError(err.message || 'Failed to load blast radius data')
    } finally {
      setLoading(false)
    }
  }
  
  if (!selectedNode) {
    return (
      <Card className="border-dashed">
        <CardBody>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <span className="text-4xl mb-3" role="img" aria-label="target">🎯</span>
            <h3 className="text-base font-bold text-gray-900 mb-2">
              Select a Node to Analyze Impact
            </h3>
            <p className="text-sm text-gray-500 max-w-md">
              Click any node in the supply chain to see its blast radius impact
              and understand downstream dependencies.
            </p>
          </div>
        </CardBody>
      </Card>
    )
  }
  
  const impactedNodes = blastRadiusData?.impacted_nodes || []
  const totalRevenueAtRisk = impactedNodes.reduce((sum, n) => sum + (n.revenue_at_risk || 0), 0)
  const criticalCount = impactedNodes.filter(n => n.severity === 'critical').length
  const moderateCount = impactedNodes.filter(n => n.severity === 'moderate').length
  
  return (
    <Card>
      <CardHeader
        icon="💥"
        title="Blast Radius Impact Analysis"
        subtitle={`Analyzing impact from: ${selectedNode.name || selectedNode.supplier_name}`}
        badge={
          impactedNodes.length > 0 && (
            <Badge color="blue" size="sm">
              {impactedNodes.length} nodes affected
            </Badge>
          )
        }
      />
      
      <CardBody className="space-y-4">
        {/* Disruption Scenario Selector */}
        <div>
          <label className="text-xs font-semibold text-gray-600 block mb-2">
            Disruption Scenario
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { value: 'delay_3days', label: '3-Day Delay', icon: '⏱️' },
              { value: 'delay_7days', label: '7-Day Delay', icon: '⏰' },
              { value: 'shutdown', label: 'Full Shutdown', icon: '🚫' },
              { value: 'capacity_50', label: '50% Capacity', icon: '📉' }
            ].map(scenario => (
              <button
                key={scenario.value}
                onClick={() => setSelectedScenario(scenario.value)}
                className={`rounded-lg border px-3 py-2 text-xs font-semibold transition-all ${
                  selectedScenario === scenario.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-blue-200 hover:bg-blue-50'
                }`}
                aria-pressed={selectedScenario === scenario.value}
              >
                <span className="mr-1" aria-hidden="true">{scenario.icon}</span>
                {scenario.label}
              </button>
            ))}
          </div>
        </div>
        
        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            <p className="ml-3 text-sm text-gray-600">Calculating blast radius...</p>
          </div>
        )}
        
        {/* Error State */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 flex items-center gap-2">
            <span className="text-red-500" aria-hidden="true">⚠️</span>
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={loadBlastRadius}
              className="ml-auto text-xs font-bold text-red-600 hover:text-red-500"
            >
              Retry
            </button>
          </div>
        )}
        
        {/* Impact Summary */}
        {!loading && !error && blastRadiusData && (
          <>
            <div className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <p className="text-sm font-bold text-orange-800 flex items-center gap-1">
                    <span aria-hidden="true">⚠️</span>
                    {impactedNodes.length} Downstream Node{impactedNodes.length !== 1 ? 's' : ''} Affected
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {criticalCount > 0 && (
                      <span className="text-xs text-orange-600">
                        <strong>{criticalCount}</strong> Critical
                      </span>
                    )}
                    {moderateCount > 0 && (
                      <span className="text-xs text-orange-600">
                        <strong>{moderateCount}</strong> Moderate
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="text-xs text-orange-600 font-semibold">Revenue at Risk</p>
                  <p className="text-lg font-black text-orange-900">
                    {formatCurrency(totalRevenueAtRisk, true)}
                  </p>
                </div>
              </div>
            </div>
            
            {/* Impacted Nodes List */}
            {impactedNodes.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-400">
                  Affected Nodes
                </p>
                
                {impactedNodes.map((node, index) => {
                  const severityConfig = SEVERITY_CONFIG[node.severity] || SEVERITY_CONFIG.moderate
                  
                  return (
                    <div
                      key={node.node_id || index}
                      className={`rounded-xl border px-4 py-3 ${severityConfig.bgClass} transition-all hover:shadow-sm`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span aria-hidden="true">{severityConfig.icon}</span>
                            <p className="text-sm font-bold text-gray-900 truncate">
                              {node.node_name}
                            </p>
                            <Badge color={severityConfig.color} size="xs">
                              {severityConfig.label}
                            </Badge>
                          </div>
                          
                          <p className="text-xs text-gray-600 mb-2">
                            {IMPACT_TYPES[node.impact_type] || node.impact_type}
                          </p>
                          
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <span className="text-gray-500">Impact in:</span>
                              <span className={`ml-1 font-bold ${severityConfig.textClass}`}>
                                {formatDays(node.days_until_impact)}
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-500">Revenue risk:</span>
                              <span className={`ml-1 font-bold ${severityConfig.textClass}`}>
                                {formatCurrency(node.revenue_at_risk || 0, true)}
                              </span>
                            </div>
                          </div>
                        </div>
                        
                        {node.mitigation_available && (
                          <button
                            onClick={() => onMitigationRequest?.(node)}
                            className="shrink-0 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 px-3 py-1.5 text-xs font-bold text-gray-700 transition"
                            aria-label={`View mitigation options for ${node.node_name}`}
                          >
                            Mitigate
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-center">
                <p className="text-sm font-semibold text-green-800">
                  ✅ No downstream impact detected for this scenario
                </p>
                <p className="text-xs text-green-600 mt-1">
                  The selected node has sufficient redundancy or buffer capacity.
                </p>
              </div>
            )}
            
            {/* Action Buttons */}
            {impactedNodes.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  onClick={() => {
                    const params = new URLSearchParams({
                      node_id: selectedNode.id || selectedNode.supplier_id,
                      mitigation_mode: 'true'
                    })
                    window.location.href = `/?${params.toString()}`
                  }}
                  className="flex-1 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-sm font-bold px-4 py-2.5 transition flex items-center justify-center gap-2"
                >
                  <span aria-hidden="true">🛡️</span>
                  View All Mitigation Options
                </button>
                
                <button
                  onClick={() => {
                    // Export blast radius report
                    const reportData = {
                      node: selectedNode,
                      scenario: selectedScenario,
                      impacted_nodes: impactedNodes,
                      total_revenue_at_risk: totalRevenueAtRisk
                    }
                    
                    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
                      type: 'application/json'
                    })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `blast-radius-${selectedNode.id}-${Date.now()}.json`
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                  className="rounded-xl border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 text-sm font-bold px-4 py-2.5 transition"
                  aria-label="Export blast radius report"
                >
                  📥 Export Report
                </button>
              </div>
            )}
          </>
        )}
      </CardBody>
    </Card>
  )
}