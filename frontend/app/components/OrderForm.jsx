"use client"

import { useMemo, useState } from "react"

function InfoTooltip({ title, description, position = "top" }) {
  const positionClass =
    position === "bottom"
      ? "top-7 left-1/2 -translate-x-1/2"
      : "bottom-7 left-1/2 -translate-x-1/2"

  const arrowClass =
    position === "bottom"
      ? "-top-1 left-1/2 -translate-x-1/2"
      : "-bottom-1 left-1/2 -translate-x-1/2"

  return (
    <span className="relative inline-flex items-center group">
      <span className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-rose-50 border border-rose-300 text-[10px] font-bold text-rose-500 cursor-help">
        i
      </span>

      <span
        className={`pointer-events-none absolute ${positionClass} z-[9999] hidden w-72 rounded-xl border border-gray-100 bg-white px-4 py-3 text-left shadow-xl group-hover:block`}
      >
        <span
          className={`absolute ${arrowClass} h-3 w-3 rotate-45 border border-gray-100 bg-white`}
        />

        <span className="relative flex items-start gap-3">
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500 text-[11px] font-bold text-white">
            i
          </span>

          <span className="flex flex-col gap-1">
            <span className="text-xs font-bold text-gray-800">
              {title}
            </span>

            <span className="text-xs font-normal leading-relaxed text-gray-600">
              {description}
            </span>
          </span>
        </span>
      </span>
    </span>
  )
}

function SearchableSelect({
  label,
  name,
  value,
  onChange,
  options = [],
  placeholder,
  required = false,
  helperText,
  tooltip,
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(value || "")

  const filteredOptions = useMemo(() => {
    const keyword = String(query || "").trim().toLowerCase()

    if (!keyword) {
      return options.slice(0, 20)
    }

    return options
      .filter((item) => String(item).toLowerCase().includes(keyword))
      .slice(0, 20)
  }, [options, query])

  const handlePick = (item) => {
    const nextValue = String(item)
    setQuery(nextValue)
    onChange(nextValue)
    setOpen(false)
  }

  const handleInputChange = (e) => {
    const nextValue = e.target.value
    setQuery(nextValue)
    onChange(nextValue)
    setOpen(true)
  }

  return (
    <div className="flex flex-col gap-1 relative">
      <label className="text-xs font-semibold text-gray-600 tracking-wide inline-flex items-center">
        {label}
        {helperText ? (
          <span className="text-gray-400 normal-case font-normal ml-1">
            {helperText}
          </span>
        ) : null}

        {tooltip ? (
          <InfoTooltip
            title={tooltip.title}
            description={tooltip.description}
            position={tooltip.position || "top"}
          />
        ) : null}
      </label>

      <input
        name={name}
        value={query}
        onChange={handleInputChange}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        required={required}
        autoComplete="off"
        placeholder={placeholder}
        className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {open && (
        <div className="absolute left-0 right-0 top-[68px] z-30 max-h-60 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-lg">
          {filteredOptions.length > 0 ? (
            filteredOptions.map((item) => (
              <button
                key={item}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => handlePick(item)}
                className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-rose-50"
              >
                {item}
              </button>
            ))
          ) : (
            <div className="px-3 py-3 text-sm text-gray-400">
              No options found
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function OrderForm({ options, onAdd }) {
  const [quantityDisplay, setQuantityDisplay] = useState("")
  const [facility, setFacility] = useState("")
  const [buyer, setBuyer] = useState("")
  const [product, setProduct] = useState("")
  const [spec, setSpec] = useState("ALL")
  const [targetTotalDays, setTargetTotalDays] = useState("")
  const [recommendationMetric, setRecommendationMetric] = useState("VOLUME")
  const [formError, setFormError] = useState(null)
  const [pendingOrder, setPendingOrder] = useState(null)

  const formatThousands = (value) => {
    if (!value) return ""
    return new Intl.NumberFormat("id-ID").format(Number(value))
  }

  const handleQuantityChange = (e) => {
    const raw = e.target.value.replace(/[^\d]/g, "")
    setQuantityDisplay(raw ? formatThousands(raw) : "")
  }

  const isValidOption = (value, optionList) => {
    return optionList.includes(value)
  }

  const resetForm = () => {
    setFacility("")
    setBuyer("")
    setProduct("")
    setSpec("ALL")
    setTargetTotalDays("")
    setQuantityDisplay("")
    setRecommendationMetric("VOLUME")
    setFormError(null)
    setPendingOrder(null)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setFormError(null)

    const rawQuantity = quantityDisplay.replace(/\./g, "").replace(/,/g, "")
    const quantity = rawQuantity ? parseFloat(rawQuantity) : 0

    if (!isValidOption(facility, options.refineries || [])) {
      setFormError("Please select a valid refinery facility from the dropdown list.")
      return
    }

    if (!isValidOption(product, options.products || [])) {
      setFormError("Please select a valid product from the dropdown list.")
      return
    }

    if (buyer && !isValidOption(buyer, options.buyers || [])) {
      setFormError("Please select a valid buyer from the dropdown list or leave it empty.")
      return
    }

    if (!quantity || quantity <= 0) {
      setFormError("Volume must be greater than 0.")
      return
    }

    const order = {
      facility,
      product,
      quantity,
      spec,
      buyer: buyer || null,
      target_total_days: targetTotalDays ? parseInt(targetTotalDays, 10) : null,
      recommendation_metric: recommendationMetric,
    }

    // Show confirmation card instead of directly adding
    setPendingOrder(order)
  }

  const handleConfirm = () => {
    if (!pendingOrder) return
    onAdd(pendingOrder)
    resetForm()
  }

  const handleCancelConfirm = () => {
    setPendingOrder(null)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-gray-100 bg-gray-50/40 p-3"
    >
      <h2 className="text-base font-bold text-gray-900 mb-1">
        Product Specifications
      </h2>

      <p className="text-sm text-gray-500 mb-5">
        Fill the required product details, then add the order to the queue.
      </p>

      {formError && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {formError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SearchableSelect
          label="Refinery Facility"
          name="facility"
          value={facility}
          onChange={setFacility}
          options={options.refineries || []}
          placeholder="Search refinery..."
          required
        />

        <SearchableSelect
          label="Buyer"
          name="buyer"
          value={buyer}
          onChange={setBuyer}
          options={options.buyers || []}
          placeholder="Search buyer or leave empty..."
          helperText="(for No-Buy List Activation)"
          tooltip={{
            title: "Buyer",
            description:
              "Selecting a buyer activates the No-Buy List filter. The system will exclude facilities that are restricted for the selected buyer.",
            position: "top",
          }}
        />

        <SearchableSelect
          label="Product"
          name="product"
          value={product}
          onChange={setProduct}
          options={options.products || []}
          placeholder="Search product..."
          required
        />

        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide">
            Volume (Kg)
          </label>

          <input
            name="quantity"
            type="text"
            inputMode="numeric"
            value={quantityDisplay}
            onChange={handleQuantityChange}
            required
            placeholder="e.g. 1.000.000"
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide inline-flex items-center">
            Specification
            <InfoTooltip
              title="Specification"
              description="Determines whether the order requires EUDR compliance. If EUDR is selected, the system will recommend Facility & SLOC stock that is active and valid for EUDR."
              position="top"
            />
          </label>

          <select
            name="spec"
            value={spec}
            onChange={(e) => setSpec(e.target.value)}
            required
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="ALL">ALL</option>
            <option value="EUDR">EUDR</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide inline-flex items-center">
            Target Total Days
            <span className="text-gray-400 normal-case font-normal ml-1">
              (optional)
            </span>
            <InfoTooltip
              title="Target Total Days"
              description="The generated report will include a status indicator showing if the recommended plan meets this target days or not."
              position="top"
            />
          </label>

          <input
            name="target_total_days"
            type="number"
            min="1"
            value={targetTotalDays}
            onChange={(e) => setTargetTotalDays(e.target.value)}
            placeholder="e.g. 20"
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
         </div>

         <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide inline-flex items-center">
            Recommendation Metric
            <InfoTooltip
              title="Recommendation Metric"
              description="VOLUME: Prioritizes available inventory. LOWEST_PCF: Prioritizes supply chains with lower product carbon footprint (environmental impact)."
              position="top"
            />
          </label>

          <select
            name="recommendation_metric"
            value={recommendationMetric}
            onChange={(e) => setRecommendationMetric(e.target.value)}
            required
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="VOLUME">Volume Priority</option>
            <option value="LOWEST_PCF">Lowest PCF (Carbon Footprint)</option>
          </select>
        </div>
      </div>

      {pendingOrder ? (
        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <p className="text-xs font-bold text-emerald-700 uppercase tracking-wide mb-2">✅ Confirm Order Details</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-emerald-900">
                <span><span className="font-semibold">Refinery:</span> {pendingOrder.facility}</span>
                <span><span className="font-semibold">Product:</span> {pendingOrder.product}</span>
                <span><span className="font-semibold">Volume:</span> {pendingOrder.quantity.toLocaleString("id-ID")} Kg</span>
                <span><span className="font-semibold">Spec:</span> {pendingOrder.spec}</span>
                {pendingOrder.buyer && <span><span className="font-semibold">Buyer:</span> {pendingOrder.buyer}</span>}
                {pendingOrder.target_total_days && <span><span className="font-semibold">Target Days:</span> {pendingOrder.target_total_days}d</span>}
                <span><span className="font-semibold">Metric:</span> {pendingOrder.recommendation_metric}</span>
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-3 justify-end">
            <button
              type="button"
              onClick={handleCancelConfirm}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-50 transition"
            >
              ← Edit
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              className="rounded-lg bg-emerald-600 hover:bg-emerald-500 px-5 py-2 text-xs font-bold text-white transition"
            >
              Add to Queue →
            </button>
          </div>
        </div>
      ) : (
        <div className="flex justify-end mt-6">
          <button
            type="submit"
            className="bg-red-700 hover:bg-red-600 text-white text-sm font-medium px-6 py-2.5 rounded-xl transition"
          >
            + Add Order
          </button>
        </div>
      )}
    </form>
  )
}