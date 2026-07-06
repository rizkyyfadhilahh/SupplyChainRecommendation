import React, { Fragment } from "react"
import { getTypeColor, toDisplayNumber, toDisplayDays, hasQueueSchedule, toDisplayDate } from "./utils"
import CalculationDetailCard from "./CalculationDetailCard"

const MemoizedRouteRow = React.memo(({
  row,
  routeKey,
  fromType,
  toType,
  isDirectToRefinery,
  getDestinationName,
  isExpanded,
  onToggle
}) => {
  return (
    <Fragment>
      <tr className="hover:bg-gray-50 align-top">
        <td className="px-5 py-4">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600">
            {Number(row.level || 0) + 1}
          </span>
        </td>

        <td className="px-5 py-4">
          <div className="flex items-start gap-2">
            <span
              className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: getTypeColor(fromType) }}
            />
            <div className="min-w-0">
              <p className="font-semibold text-gray-800 leading-snug break-words">
                {row.supplier_name || row.supplier_id || "-"}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                ID: {row.supplier_id || "-"} • {fromType}
              </p>
            </div>
          </div>
        </td>

        <td className="px-5 py-4">
          <div className="flex items-start gap-2">
            <span
              className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: getTypeColor(toType) }}
            />
            <div className="min-w-0">
              <p className="font-semibold text-gray-800 leading-snug break-words">
                {row.receiver_name || getDestinationName(row.receiver_id)}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                ID: {row.receiver_id || "-"} • {toType}
              </p>
            </div>
          </div>
        </td>

        <td className="px-5 py-4">
          <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-1 text-xs font-bold text-gray-700">
            {row.product || "-"}
          </span>
        </td>

        <td className="px-5 py-4 text-right font-semibold text-gray-800 whitespace-nowrap">
          {toDisplayNumber(row.quantity)} Kg
        </td>

        <td className="px-5 py-4 text-right font-semibold text-gray-700 whitespace-nowrap">
          {toDisplayDays(row.estimated_days)} days
        </td>

        <td className="px-5 py-4 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
          {hasQueueSchedule(row) ? toDisplayDate(row.start_date) : "-"}
        </td>

        <td className="px-5 py-4 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
          {hasQueueSchedule(row) ? toDisplayDate(row.arrival_date) : "-"}
        </td>

        <td className="px-5 py-4 text-right whitespace-nowrap">
          {Number(row?.pcf_per_unit || 0) > 0 ? (
            <span className="inline-flex flex-col items-end">
              <span className="text-xs font-bold text-green-700">
                {Number(row.pcf_per_unit).toFixed(4)}
              </span>
              <span className="text-[9px] text-gray-400">kg CO₂e/kg</span>
            </span>
          ) : (
            <span className="text-xs text-gray-300">—</span>
          )}
        </td>

        <td className="px-5 py-4 text-right">
          <button
            type="button"
            onClick={() => onToggle(routeKey)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50"
          >
            {isExpanded ? "Hide" : "Details"}
          </button>
        </td>
      </tr>

      {isExpanded && (
        <tr className="w-full">
          <td colSpan={100} className="w-full bg-gray-50 px-5 py-4">
            <CalculationDetailCard
              row={row}
              isRefinerySelected={isDirectToRefinery}
              getDestinationName={getDestinationName}
            />
          </td>
        </tr>
      )}
    </Fragment>
  )
})

export default MemoizedRouteRow
