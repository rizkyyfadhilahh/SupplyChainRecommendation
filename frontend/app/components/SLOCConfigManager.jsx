"use client"

import { useEffect, useMemo, useState } from "react"

const EMPTY_FILTER = "__ALL__"

function toDateInput(value) {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  return date.toISOString().slice(0, 10)
}

function normalizeRow(row) {
  return {
    plant: String(row.plant ?? ""),
    name1: String(row.name1 ?? ""),
    storagelocation: String(row.storagelocation ?? ""),
    material: String(row.material ?? ""),
    material_type: String(row.material_type ?? ""),
    materialdescription: String(row.materialdescription ?? ""),
    refinery_group: row.refinery_group ?? "",
    product_code: row.product_code ?? "",
    current_stock: Number(row.current_stock ?? 0),
    eudr: Boolean(row.eudr),
    eudr_valid_from: toDateInput(row.eudr_valid_from),
    eudr_valid_to: toDateInput(row.eudr_valid_to),
  }
}

function rowKey(row) {
  return `${row.plant}__${row.storagelocation}__${row.material}`
}

export default function SLOCConfigManager({ options }) {
  const [facility, setFacility] = useState(EMPTY_FILTER)
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [search, setSearch] = useState("")
  const [productFilter, setProductFilter] = useState(EMPTY_FILTER)
  const [statusFilter, setStatusFilter] = useState(EMPTY_FILTER)
  const [dirtyMap, setDirtyMap] = useState({})
  const [maxDate, setMaxDate] = useState("-")

  const loadRows = async (selectedFacility = facility) => {
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const query = selectedFacility && selectedFacility !== EMPTY_FILTER
        ? `?facility=${encodeURIComponent(selectedFacility)}`
        : ""

      const res = await fetch(`/api/backend/api/sloc-master${query}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || "Failed to load SLOC master.")
      }

      const data = await res.json()
      const nextRows = (data.rows || []).map(normalizeRow)
      setRows(nextRows)
      setDirtyMap({})
      setMaxDate(data.max_date || "-")
    } catch (err) {
      setError(err.message || "Failed to load SLOC master.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRows(EMPTY_FILTER)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const productOptions = useMemo(() => {
    const uniq = Array.from(
      new Set(rows.map((row) => row.product_code || row.material_type).filter(Boolean))
    )
    return uniq.sort((a, b) => a.localeCompare(b))
  }, [rows])

  const filteredRows = useMemo(() => {
    const keyword = search.trim().toLowerCase()

    return rows.filter((row) => {
      const matchesKeyword = !keyword || [
        row.plant,
        row.name1,
        row.storagelocation,
        row.material,
        row.material_type,
        row.materialdescription,
        row.product_code,
        row.refinery_group,
      ].some((value) => String(value || "").toLowerCase().includes(keyword))

      const effectiveProduct = row.product_code || row.material_type || ""
      const matchesProduct = productFilter === EMPTY_FILTER || effectiveProduct === productFilter

      const matchesStatus =
        statusFilter === EMPTY_FILTER ||
        (statusFilter === "EUDR" && row.eudr) ||
        (statusFilter === "NON_EUDR" && !row.eudr)

      return matchesKeyword && matchesProduct && matchesStatus
    })
  }, [rows, search, productFilter, statusFilter])

  const dirtyCount = Object.keys(dirtyMap).length

  const handleFacilityChange = async (value) => {
    setFacility(value)
    await loadRows(value)
  }

  const updateRow = (key, patch) => {
    setRows((prev) =>
      prev.map((row) => (rowKey(row) === key ? { ...row, ...patch } : row))
    )
    setDirtyMap((prev) => ({ ...prev, [key]: true }))
  }

  const handleToggleEudr = (row) => {
    const key = rowKey(row)
    const nextEudr = !row.eudr
    const today = new Date().toISOString().slice(0, 10)
    const nextPatch = nextEudr
      ? {
          eudr: true,
          eudr_valid_from: row.eudr_valid_from || today,
          eudr_valid_to: row.eudr_valid_to || "2099-12-31",
        }
      : {
          eudr: false,
        }

    updateRow(key, nextPatch)
  }

  const handleDateChange = (row, field, value) => {
    updateRow(rowKey(row), { [field]: value })
  }

  const handleSave = async () => {
    const changedRows = rows.filter((row) => dirtyMap[rowKey(row)])
    if (!changedRows.length) return

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const payload = {
        items: changedRows.map((row) => ({
          plant: row.plant,
          storagelocation: row.storagelocation,
          material: row.material,
          eudr: Boolean(row.eudr),
          eudr_valid_from: row.eudr_valid_from || null,
          eudr_valid_to: row.eudr_valid_to || null,
        })),
      }

      const res = await fetch("/api/backend/api/sloc-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || "Failed to save SLOC config.")
      }

      setSuccess(`${changedRows.length} SLOC row(s) updated successfully.`)
      await loadRows(facility)
    } catch (err) {
      setError(err.message || "Failed to save SLOC config.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">SLOC Configuration</h2>
          <p className="text-sm text-gray-500 mt-1">
            Update EUDR status per SLOC row. This affects stock eligibility, not upstream facility trace logic.
          </p>
          <p className="text-xs text-gray-400 mt-2">Current stock snapshot date: {maxDate}</p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => loadRows(facility)}
            disabled={loading || saving}
            className="px-4 py-2 text-sm rounded-xl border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !dirtyCount}
            className="px-4 py-2 text-sm rounded-xl bg-gray-900 text-white hover:bg-gray-700 disabled:opacity-60"
          >
            {saving ? "Saving..." : `Save Changes${dirtyCount ? ` (${dirtyCount})` : ""}`}
          </button>
        </div>
      </div>

      <div className="px-6 py-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 border-b border-gray-100 bg-gray-50">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide">Refinery Group</label>
          <select
            value={facility}
            onChange={(e) => handleFacilityChange(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm bg-white"
          >
            <option value={EMPTY_FILTER}>All Refinery Groups</option>
            {(options?.refineries || []).map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide">Search</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Plant, SLOC, material, product..."
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm bg-white"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide">Product</label>
          <select
            value={productFilter}
            onChange={(e) => setProductFilter(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm bg-white"
          >
            <option value={EMPTY_FILTER}>All Products</option>
            {productOptions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-gray-600 tracking-wide">EUDR Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm bg-white"
          >
            <option value={EMPTY_FILTER}>All</option>
            <option value="EUDR">EUDR Only</option>
            <option value="NON_EUDR">Non-EUDR Only</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="mx-6 mt-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {success}
        </div>
      )}

      <div className="px-6 py-4 text-sm text-gray-500">
        {loading ? "Loading SLOC master..." : `${filteredRows.length.toLocaleString()} row(s) shown`}
      </div>

      <div className="overflow-x-auto border-t border-gray-100">
        <table className="min-w-full text-xs">
          <thead className="bg-gray-50 text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3 text-left">Plant</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">SLOC</th>
              <th className="px-4 py-3 text-left">Material</th>
              <th className="px-4 py-3 text-left">Product</th>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-right">Current Stock</th>
              <th className="px-4 py-3 text-left">EUDR</th>
              <th className="px-4 py-3 text-left">Valid From</th>
              <th className="px-4 py-3 text-left">Valid To</th>
            </tr>
          </thead>
          <tbody>
            {!loading && !filteredRows.length && (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-sm text-gray-400">
                  No SLOC rows found for the current filter.
                </td>
              </tr>
            )}

            {filteredRows.map((row) => {
              const key = rowKey(row)
              const isDirty = Boolean(dirtyMap[key])
              const effectiveProduct = row.product_code || row.material_type || "-"

              return (
                <tr key={key} className={`border-t border-gray-100 text-gray-700 ${isDirty ? "bg-yellow-50" : "bg-white"}`}>
                  <td className="px-4 py-3 whitespace-nowrap">{row.plant}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{row.name1 || "-"}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{row.storagelocation}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{row.material}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{effectiveProduct}</td>
                  <td className="px-4 py-3 min-w-[220px]">{row.materialdescription || "-"}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">{row.current_stock.toLocaleString()}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => handleToggleEudr(row)}
                      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                        row.eudr ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-600"
                      }`}
                    >
                      {row.eudr ? "EUDR" : "NON-EUDR"}
                    </button>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <input
                      type="date"
                      value={row.eudr_valid_from || ""}
                      onChange={(e) => handleDateChange(row, "eudr_valid_from", e.target.value)}
                      className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs bg-white"
                    />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <input
                      type="date"
                      value={row.eudr_valid_to || ""}
                      onChange={(e) => handleDateChange(row, "eudr_valid_to", e.target.value)}
                      className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs bg-white"
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
