import React, { useState, useEffect, useMemo } from "react"
import { toDisplayNumber, toDisplayDays } from "./utils"

export function QuantityWithBasis({ row, align = "right" }) {
  const product = String(row?.product || "").toUpperCase()
  const actualQty = Number(row?.quantity || 0)

  const basisProduct = String(
    row?.allocation_basis_product || product
  ).toUpperCase()

  const basisQty = Number(
    row?.allocation_basis_quantity ?? actualQty
  )

  const showBasis =
    basisProduct &&
    product &&
    basisProduct !== product &&
    Number.isFinite(basisQty) &&
    basisQty > 0

  return (
    <div className={align === "right" ? "text-right" : "text-left"}>
      <p className="font-semibold text-gray-800 whitespace-nowrap">
        {toDisplayNumber(actualQty)} Kg
      </p>

      {showBasis && (
        <p className="mt-1 text-[11px] font-medium text-gray-400 whitespace-nowrap">
          ≈ {toDisplayNumber(basisQty)} Kg {basisProduct} basis
        </p>
      )}
    </div>
  )
}

export function InfoChip({ label, value, className = "" }) {
  return (
    <div
      className={`flex flex-col items-center border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 min-w-[80px] ${className}`}
    >
      <span className="text-[10px] text-gray-700 uppercase tracking-wide font-medium">
        {label}
      </span>
      <span className="text-xs font-semibold text-gray-700 mt-0.5">
        {value}
      </span>
    </div>
  )
}

export function EmptyState({ message = "No supply chain recommendation." }) {
  return (
    <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
      {message}
    </div>
  )
}

export function MiniTooltip({ text }) {
  return (
    <span className="relative inline-flex items-center group">
      <span className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-blue-200 bg-blue-50 text-[10px] font-bold text-blue-600 cursor-help">
        i
      </span>

      <span className="pointer-events-none absolute left-1/2 bottom-full mb-2 z-[9999] hidden w-max max-w-[220px] -translate-x-1/2 rounded-xl border border-gray-100 bg-white px-3 py-2 text-left text-xs font-normal leading-relaxed text-gray-600 shadow-xl group-hover:block">
        <span className="absolute -bottom-1 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-b border-r border-gray-100 bg-white" />
        {text}
      </span>
    </span>
  )
}

export function CalculationMetricCard({ label, value, tooltip }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
      <p className="text-[10px] font-bold tracking-wide text-gray-400 inline-flex items-center">
        {label}
        <MiniTooltip text={tooltip} />
      </p>

      <p className="mt-1 text-sm font-bold text-gray-800">
        {value}
      </p>
    </div>
  )
}

export function SearchableFilterDropdown({
  label,
  value,
  onChange,
  options = [],
  placeholder = "All",
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(value || "")

  useEffect(() => {
    setQuery(value || "")
  }, [value])

  const filteredOptions = useMemo(() => {
    const keyword = String(query || "").trim().toLowerCase()

    if (!keyword) return options.slice(0, 50)

    return options
      .filter((item) => String(item).toLowerCase().includes(keyword))
      .slice(0, 50)
  }, [options, query])

  const handlePick = (item) => {
    setQuery(item)
    onChange(item)
    setOpen(false)
  }

  const handleClear = () => {
    setQuery("")
    onChange("")
    setOpen(false)
  }

  return (
    <div className="relative flex flex-col gap-1">
      <label className="text-[10px] font-bold uppercase tracking-wide text-gray-400">
        {label}
      </label>

      <div
        className={`flex h-10 items-center rounded-lg border bg-white px-3 transition ${open ? "border-red-300 ring-2 ring-red-50" : "border-gray-200"
          }`}
      >
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-white text-xs font-semibold text-gray-700 placeholder:text-gray-300 focus:outline-none"
        />

        {query ? (
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={handleClear}
            className="ml-2 shrink-0 text-xs font-bold text-gray-400 hover:text-gray-700"
          >
            ×
          </button>
        ) : (
          <span className="ml-2 shrink-0 text-xs text-gray-400">⌄</span>
        )}
      </div>

      {open && (
        <div className="tree-scrollbar absolute left-0 right-0 top-[58px] z-[9999] max-h-56 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-xl">
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={handleClear}
            className="block w-full px-3 py-2 text-left text-xs font-semibold text-gray-400 hover:bg-gray-50"
          >
            All
          </button>

          {filteredOptions.length > 0 ? (
            filteredOptions.map((item) => (
              <button
                key={item}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => handlePick(item)}
                className="block w-full px-3 py-2 text-left text-xs font-semibold text-gray-700 hover:bg-red-50"
              >
                {item}
              </button>
            ))
          ) : (
            <div className="px-3 py-3 text-xs text-gray-400">
              No options found
            </div>
          )}
        </div>
      )}
    </div>
  )
}
