export default function RecommendationOptionCards({ options, activeIndex, onChange }) {
  if (!options || options.length <= 1) return null

  return (
    <div className="flex flex-wrap gap-4 mt-4">
      {options.map((opt, i) => {
        const isLowestPcf = opt.option_type === "LOWEST_PCF"
        const isActive = activeIndex === i
        const focusIcon = isLowestPcf ? "🌱" : "🚀"
        const focusBg = isLowestPcf ? "bg-green-50" : "bg-blue-50"
        const focusText = isLowestPcf ? "text-green-800" : "text-blue-800"
        const focusBorder = isLowestPcf ? "border-green-200" : "border-blue-200"
        const title = isLowestPcf ? "PCF Priority" : "Volume Priority"

        const totalDays = opt.forecast_summary?.total_estimated_days || 0
        const unmet = opt.forecast_summary?.unmet_demand_qty || 0
        const unmetPct = opt.forecast_summary?.unmet_demand_percent || 0
        const pcfPerTon = opt.pcf_per_unit_kg_co2e || 0

        return (
          <button
            key={i}
            type="button"
            onClick={() => onChange(i)}
            className={`text-left rounded-2xl border-2 p-5 flex-1 min-w-[300px] transition-all duration-200 ${
              isActive 
                ? `ring-2 ring-offset-2 ring-blue-500 border-blue-400 bg-white shadow-md` 
                : `border-gray-100 hover:border-gray-200 bg-white shadow-sm hover:shadow-md`
            }`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{focusIcon}</span>
                <span className={`text-xs font-bold uppercase tracking-wider px-2 py-1 rounded-md border ${focusBg} ${focusText} ${focusBorder}`}>
                  {title}
                </span>
              </div>
              {isActive && (
                <span className="h-6 w-6 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs">✓</span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-y-3 gap-x-2">
              <div>
                <p className="text-[10px] font-bold text-gray-500 uppercase">Est. Days</p>
                <p className="text-lg font-black text-gray-900">{totalDays} days</p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-gray-500 uppercase">Fill Rate</p>
                <p className="text-lg font-black text-gray-900">{(100 - unmetPct).toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-gray-500 uppercase">Unmet Demand</p>
                <p className="text-sm font-bold text-red-600">{(unmet / 1000).toFixed(1)} kton</p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-gray-500 uppercase">PCF Intensity</p>
                <p className="text-sm font-bold text-green-700">{pcfPerTon.toFixed(2)} tCO₂e/t</p>
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}
