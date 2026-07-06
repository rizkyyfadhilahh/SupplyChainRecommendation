export function formatKg(value) {
  const num = Number(value || 0)

  if (!Number.isFinite(num)) return "0"

  return num.toLocaleString("id-ID", {
    maximumFractionDigits: 0,
  })
}

export function detectConflicts(results) {
  const conflicts = new Set()
  if (!results || results.length <= 1) return conflicts

  for (let i = 0; i < results.length; i++) {
    const slocsI = results[i]?.stock_overview?.selected_slocs || []
    for (let j = i + 1; j < results.length; j++) {
      const slocsJ = results[j]?.stock_overview?.selected_slocs || []
      
      let hasOverlap = false
      for (const s1 of slocsI) {
        for (const s2 of slocsJ) {
          if (s1.plant === s2.plant && s1.storagelocation === s2.storagelocation) {
            hasOverlap = true
            break
          }
        }
        if (hasOverlap) break
      }
      
      if (hasOverlap) {
        conflicts.add(i)
        conflicts.add(j)
      }
    }
  }
  return conflicts
}

export function getIncomingAllocationInfo(orderResult) {
  const summary = orderResult?.forecast_summary || {}
  const tree = orderResult?.tree || []

  const facility = String(orderResult?.facility || "").trim()

  const incomingRows = tree.filter((row) => {
    const isRootLevel = Number(row?.level || 0) === 0
    const isIncomingToFacility =
      facility && String(row?.receiver_id || "").trim() === facility

    return isRootLevel || isIncomingToFacility
  })

  const incomingQtyFromRows = incomingRows.reduce(
    (sum, row) => sum + Number(row?.quantity || 0),
    0
  )

  const incomingQty = Number(
    summary?.allocated_root_qty ??
      summary?.total_incoming_allocation ??
      incomingQtyFromRows
  )

  const materialTypes = Array.from(
    new Set(
      incomingRows
        .map((row) => String(row?.product || "").trim().toUpperCase())
        .filter(Boolean)
    )
  )

  const fallbackProduct = String(orderResult?.product || "").trim().toUpperCase()

  const materialLabel =
    materialTypes.length === 1
      ? materialTypes[0]
      : materialTypes.length > 1
      ? `Mixed: ${materialTypes.join(", ")}`
      : fallbackProduct || "Material"

  return {
    quantity: Number.isFinite(incomingQty) ? incomingQty : 0,
    materialLabel,
  }
}
