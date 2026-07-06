"use client"

import { useState } from "react"
import PcfPieChart from "../charts/PcfPieChart"
import Card, { CardHeader, CardBody, CardFooter } from "../shared/Card"
import Badge from "../shared/Badge"
import { formatCO2, formatCurrency } from "@/utils/formatters"
import { getOffsetCostEstimate } from "@/services/recommendationService"

/**
 * PCF Analysis Panel for Recommendation Page
 * Comprehensive carbon footprint analysis with offset cost estimation
 * 
 * USER STORY:
 * As a Sustainability Manager, I want to see detailed PCF breakdown with stage-by-stage emissions
 * and offset cost estimates, so that I can make informed decisions about carbon-neutral product offerings
 * and understand the true cost of achieving carbon neutrality.
 */

const OFFSET_TYPES = [
  { 
    value: 'reforestation', 
    label: 'Reforestation', 
    icon: '🌳',
    description: 'Tree planting projects',
    avgCostPerTon: 15
  },
  { 
    value: 'renewable_energy', 
    label: 'Renewable Energy', 
    icon: '⚡',
    description: 'Wind/solar energy credits',
    avgCostPerTon: 25
  },
  { 
    value: 'direct_air_capture', 
    label: 'Direct Air Capture', 
    icon: '🏭',
    description: 'Carbon removal technology',
    avgCostPerTon: 100
  },
  { 
    value: 'mixed', 
    label: 'Mixed Portfolio', 
    icon: '🌍',
    description: 'Balanced approach',
    avgCostPerTon: 35
  }
]

export default function PcfAnalysisPanel({ 
  recommendationOption,
  buyerMaxPcf,
  productVolume = 1000, // in kg
  onOffsetPurchase
}) {
  const [selectedOffsetType, setSelectedOffsetType] = useState('mixed')
  const [offsetEstimate, setOffsetEstimate] = useState(null)
  const [loadingEstimate, setLoadingEstimate] = useState(false)
  const [showOffsetCalculator, setShowOffsetCalculator] = useState(false)
  
  if (!recommendationOption) {
    return null
  }
  
  const pcfBreakdown = recommendationOption.pcf_breakdown || {}
  const totalPcfKg = pcfBreakdown.total_kg_co2e || 0
  const pcfIntensity = recommendationOption.pcf_per_unit_kg_co2e || 0
  const isCompliant = buyerMaxPcf ? pcfIntensity <= buyerMaxPcf : null
  
  // Calculate offset cost estimate
  const handleCalculateOffset = async () => {
    setLoadingEstimate(true)
    
    try {
      const estimate = await getOffsetCostEstimate(totalPcfKg, selectedOffsetType)
      setOffsetEstimate(estimate)
    } catch (error) {
      console.error('Offset estimate error:', error)
      
      // Fallback to client-side calculation
      const offsetType = OFFSET_TYPES.find(t => t.value === selectedOffsetType)
      const costPerTon = offsetType?.avgCostPerTon || 35
      const totalTons = totalPcfKg / 1000
      const totalCost = totalTons * costPerTon
      const costPerUnit = (totalCost / productVolume) * 1000 // per kg of product
      
      setOffsetEstimate({
        total_cost: totalCost,
        cost_per_unit: costPerUnit,
        offset_type: selectedOffsetType,
        carbon_tons: totalTons,
        providers: []
      })
    } finally {
      setLoadingEstimate(false)
    }
  }
  
  return (
    <div className="space-y-4">
      {/* Main PCF Pie Chart */}
      <PcfPieChart 
        pcfBreakdown={pcfBreakdown}
        title="Product Carbon Footprint Analysis"
        buyerMaxPcf={buyerMaxPcf}
      />
      
      {/* Carbon Offset Calculator */}
      <Card>
        <CardHeader
          icon="💰"
          title="Carbon Offset Cost Estimator"
          subtitle="Calculate the cost to achieve carbon neutrality"
          right={
            <button
              onClick={() => setShowOffsetCalculator(!showOffsetCalculator)}
              className="text-xs font-bold text-blue-600 hover:text-blue-500 transition"
            >
              {showOffsetCalculator ? 'Hide' : 'Show'} Calculator
            </button>
          }
        />
        
        {showOffsetCalculator && (
          <CardBody className="space-y-4">
            {/* Offset Type Selection */}
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-2">
                Select Offset Type
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {OFFSET_TYPES.map(type => (
                  <button
                    key={type.value}
                    onClick={() => setSelectedOffsetType(type.value)}
                    className={`rounded-lg border px-3 py-3 text-left transition-all ${
                      selectedOffsetType === type.value
                        ? 'border-green-500 bg-green-50'
                        : 'border-gray-200 bg-white hover:border-green-200 hover:bg-green-50'
                    }`}
                    title={type.description}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg" aria-hidden="true">{type.icon}</span>
                      <span className={`text-xs font-bold ${
                        selectedOffsetType === type.value ? 'text-green-700' : 'text-gray-700'
                      }`}>
                        {type.label}
                      </span>
                    </div>
                    <p className="text-[9px] text-gray-500 leading-tight">
                      ~${type.avgCostPerTon}/tCO₂e
                    </p>
                  </button>
                ))}
              </div>
            </div>
            
            {/* Calculate Button */}
            <button
              onClick={handleCalculateOffset}
              disabled={loadingEstimate}
              className="w-full rounded-xl bg-green-600 hover:bg-green-500 disabled:bg-gray-300 text-white text-sm font-bold px-4 py-3 transition flex items-center justify-center gap-2"
            >
              {loadingEstimate ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  Calculating...
                </>
              ) : (
                <>
                  <span aria-hidden="true">🧮</span>
                  Calculate Offset Cost
                </>
              )}
            </button>
            
            {/* Offset Estimate Results */}
            {offsetEstimate && (
              <div className="space-y-3 pt-3 border-t border-gray-100">
                <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3">
                  <p className="text-xs font-bold text-green-800 mb-3 flex items-center gap-1">
                    <span aria-hidden="true">✅</span>
                    Offset Cost Estimation
                  </p>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-[9px] font-bold uppercase tracking-wide text-green-600">
                        Total Offset Cost
                      </p>
                      <p className="text-lg font-black text-green-900 mt-0.5">
                        {formatCurrency(offsetEstimate.total_cost)}
                      </p>
                    </div>
                    
                    <div>
                      <p className="text-[9px] font-bold uppercase tracking-wide text-green-600">
                        Cost per Kg Product
                      </p>
                      <p className="text-lg font-black text-green-900 mt-0.5">
                        ${offsetEstimate.cost_per_unit?.toFixed(3)}
                      </p>
                    </div>
                    
                    <div>
                      <p className="text-[9px] font-bold uppercase tracking-wide text-green-600">
                        Carbon to Offset
                      </p>
                      <p className="text-sm font-bold text-green-900 mt-0.5">
                        {formatCO2(totalPcfKg, 't')}
                      </p>
                    </div>
                    
                    <div>
                      <p className="text-[9px] font-bold uppercase tracking-wide text-green-600">
                        Offset Type
                      </p>
                      <p className="text-sm font-bold text-green-900 mt-0.5">
                        {OFFSET_TYPES.find(t => t.value === selectedOffsetType)?.label}
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Business Impact Analysis */}
                <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
                  <p className="text-xs font-bold text-blue-800 mb-2 flex items-center gap-1">
                    <span aria-hidden="true">💡</span>
                    Business Impact
                  </p>
                  
                  <div className="space-y-2 text-xs text-blue-700">
                    <p>
                      • Adding carbon offset increases product cost by{" "}
                      <strong>
                        {((offsetEstimate.cost_per_unit / (productVolume / 1000)) * 100).toFixed(2)}%
                      </strong>
                    </p>
                    <p>
                      • Marketing opportunity: <strong>"Carbon Neutral Product"</strong> certification
                    </p>
                    <p>
                      • Typical market premium for carbon-neutral products: <strong>+5-10%</strong>
                    </p>
                    <p>
                      • Net margin impact: <strong>Potentially positive</strong> if premium exceeds offset cost
                    </p>
                  </div>
                </div>
                
                {/* Recommended Providers (if available) */}
                {offsetEstimate.providers && offsetEstimate.providers.length > 0 && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-gray-400 mb-2">
                      Recommended Offset Providers
                    </p>
                    <div className="space-y-2">
                      {offsetEstimate.providers.map((provider, index) => (
                        <div 
                          key={index}
                          className="rounded-lg border border-gray-200 bg-white px-3 py-2 flex items-center justify-between gap-3"
                        >
                          <div className="flex-1">
                            <p className="text-xs font-semibold text-gray-900">{provider.name}</p>
                            <p className="text-[10px] text-gray-500 mt-0.5">
                              {provider.certification} · {provider.project_type}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs font-bold text-gray-900">
                              ${provider.price_per_ton}/tCO₂e
                            </p>
                            <Badge color="green" size="xs">
                              {provider.quality_rating}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Action Buttons */}
                <div className="flex gap-2">
                  {onOffsetPurchase && (
                    <button
                      onClick={() => onOffsetPurchase(offsetEstimate)}
                      className="flex-1 rounded-lg bg-green-600 hover:bg-green-500 text-white text-xs font-bold px-4 py-2 transition"
                    >
                      Proceed to Purchase
                    </button>
                  )}
                  <button
                    onClick={() => {
                      const report = {
                        recommendation_option: recommendationOption.option_type,
                        total_pcf: totalPcfKg,
                        offset_type: selectedOffsetType,
                        estimate: offsetEstimate,
                        timestamp: new Date().toISOString()
                      }
                      
                      const blob = new Blob([JSON.stringify(report, null, 2)], {
                        type: 'application/json'
                      })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `offset-estimate-${Date.now()}.json`
                      a.click()
                      URL.revokeObjectURL(url)
                    }}
                    className="rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 text-xs font-bold px-4 py-2 transition"
                  >
                    Export Report
                  </button>
                </div>
              </div>
            )}
          </CardBody>
        )}
        
        {!showOffsetCalculator && (
          <CardBody>
            <div className="text-center py-4">
              <p className="text-sm text-gray-500">
                Click "Show Calculator" to estimate carbon offset costs and explore carbon-neutral options
              </p>
            </div>
          </CardBody>
        )}
      </Card>
      
      {/* Compliance Status Card */}
      {isCompliant !== null && (
        <Card>
          <CardBody>
            <div className={`rounded-xl border px-4 py-3 ${
              isCompliant 
                ? 'bg-green-50 border-green-200' 
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center gap-3">
                <span className="text-2xl" aria-hidden="true">
                  {isCompliant ? '✅' : '❌'}
                </span>
                <div className="flex-1">
                  <p className={`text-sm font-bold ${
                    isCompliant ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {isCompliant ? 'Within Buyer PCF Limit' : 'Exceeds Buyer PCF Limit'}
                  </p>
                  <p className={`text-xs mt-1 ${
                    isCompliant ? 'text-green-600' : 'text-red-600'
                  }`}>
                    PCF Intensity: <strong>{pcfIntensity.toFixed(4)} tCO₂e/ton</strong> vs
                    Buyer Limit: <strong>{buyerMaxPcf?.toFixed(4)} tCO₂e/ton</strong>
                  </p>
                </div>
              </div>
              
              {!isCompliant && (
                <div className="mt-3 pt-3 border-t border-red-200">
                  <p className="text-xs font-semibold text-red-700 mb-1">Recommended Actions:</p>
                  <ul className="text-xs text-red-600 space-y-1 ml-4 list-disc">
                    <li>Consider alternative routes with lower PCF</li>
                    <li>Explore carbon offset options to achieve neutrality</li>
                    <li>Optimize transport and processing stages</li>
                  </ul>
                </div>
              )}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}