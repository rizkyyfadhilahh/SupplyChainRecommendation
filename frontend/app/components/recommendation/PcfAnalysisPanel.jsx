"use client"

import PcfPieChart from "../charts/PcfPieChart"
import Card, { CardBody } from "../shared/Card"

export default function PcfAnalysisPanel({ 
  recommendationOption,
  buyerMaxPcf,
}) {
  if (!recommendationOption) {
    return null
  }
  
  const pcfBreakdown = recommendationOption.pcf_breakdown || {}
  const pcfIntensity = recommendationOption.pcf_per_unit_kg_co2e || 0
  const isCompliant = buyerMaxPcf ? pcfIntensity <= buyerMaxPcf : null
  
  return (
    <div className="space-y-4">
      {/* Main PCF Pie Chart */}
      <PcfPieChart 
        pcfBreakdown={pcfBreakdown}
        title="Product Carbon Footprint Analysis"
        buyerMaxPcf={buyerMaxPcf}
      />
      
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