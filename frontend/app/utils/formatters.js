/**
 * Formatting utilities for consistent data display
 * All formatters handle edge cases and null/undefined safely
 */

/**
 * Format number as kilogram
 * @param {number} value - Value in kg
 * @returns {string} - Formatted string
 */
export function formatKg(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0 Kg"
  return num.toLocaleString("id-ID", { maximumFractionDigits: 0 }) + " Kg"
}

/**
 * Format number as metric ton
 * @param {number} value - Value in MT
 * @returns {string} - Formatted string
 */
export function formatMT(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0 MT"
  return num.toLocaleString("id-ID", { maximumFractionDigits: 2 }) + " MT"
}

/**
 * Format number as kiloton
 * @param {number} value - Value in kg
 * @returns {string} - Formatted string in kton
 */
export function formatKton(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0 kton"
  return (num / 1000).toLocaleString("id-ID", { maximumFractionDigits: 1 }) + " kton"
}

/**
 * Format number as percentage
 * @param {number} value - Decimal value (0-1) or percentage (0-100)
 * @param {boolean} isDecimal - True if value is 0-1, false if 0-100
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted percentage
 */
export function formatPercentage(value, isDecimal = false, decimals = 1) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0%"
  
  const pct = isDecimal ? num * 100 : num
  return pct.toFixed(decimals) + "%"
}

/**
 * Format number with specified decimals
 * @param {number} value - Number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted number
 */
export function formatNumber(value, decimals = 2) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0"
  return num.toFixed(decimals)
}

/**
 * Format date to readable string
 * @param {string|Date} dateStr - Date string or Date object
 * @param {string} format - Format type: 'short', 'long', 'iso'
 * @returns {string} - Formatted date
 */
export function formatDate(dateStr, format = 'short') {
  if (!dateStr) return "—"
  
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return dateStr
    
    switch (format) {
      case 'short':
        return date.toLocaleDateString("en-GB", { 
          day: "2-digit", 
          month: "short", 
          year: "numeric" 
        })
      case 'long':
        return date.toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "long",
          year: "numeric"
        })
      case 'iso':
        return date.toISOString().split('T')[0]
      default:
        return date.toLocaleDateString()
    }
  } catch (error) {
    console.error('Date format error:', error)
    return dateStr
  }
}

/**
 * Format currency (USD)
 * @param {number} value - Amount in USD
 * @param {boolean} compact - Use compact notation (K, M)
 * @returns {string} - Formatted currency
 */
export function formatCurrency(value, compact = false) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "$0"
  
  if (compact) {
    if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`
  }
  
  return "$" + num.toLocaleString("en-US", { 
    minimumFractionDigits: 0,
    maximumFractionDigits: 0 
  })
}

/**
 * Format CO2 emissions
 * @param {number} value - Value in kg CO2e
 * @param {string} unit - Output unit: 'kg', 't', 'auto'
 * @returns {string} - Formatted emissions
 */
export function formatCO2(value, unit = 'auto') {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0 kg CO₂e"
  
  if (unit === 'auto') {
    if (num >= 1000) {
      return (num / 1000).toFixed(3) + " tCO₂e"
    }
    return num.toFixed(2) + " kg CO₂e"
  }
  
  if (unit === 't') {
    return (num / 1000).toFixed(3) + " tCO₂e"
  }
  
  return num.toFixed(2) + " kg CO₂e"
}

/**
 * Format PCF intensity
 * @param {number} value - PCF per unit (kg CO2e / kg product)
 * @returns {string} - Formatted intensity
 */
export function formatPCFIntensity(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0 tCO₂e/ton"
  return num.toFixed(4) + " tCO₂e/ton"
}

/**
 * Format duration in days
 * @param {number} days - Number of days
 * @returns {string} - Formatted duration
 */
export function formatDays(days) {
  const num = Number(days)
  if (!Number.isFinite(num)) return "—"
  if (num === 1) return "1 day"
  return `${num} days`
}

/**
 * Format distance
 * @param {number} km - Distance in kilometers
 * @returns {string} - Formatted distance
 */
export function formatDistance(km) {
  const num = Number(km)
  if (!Number.isFinite(num)) return "0 km"
  return num.toLocaleString("id-ID", { maximumFractionDigits: 1 }) + " km"
}

/**
 * Format large numbers with compact notation
 * @param {number} value - Number to format
 * @returns {string} - Formatted number
 */
export function formatCompactNumber(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0"
  
  if (num >= 1000000000) return (num / 1000000000).toFixed(1) + "B"
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M"
  if (num >= 1000) return (num / 1000).toFixed(1) + "K"
  
  return num.toFixed(0)
}

/**
 * Format change with +/- sign
 * @param {number} value - Change value
 * @param {string} suffix - Suffix (%, Kg, etc)
 * @returns {string} - Formatted change
 */
export function formatChange(value, suffix = "%") {
  const num = Number(value)
  if (!Number.isFinite(num)) return "—"
  
  const sign = num > 0 ? "+" : ""
  return `${sign}${num.toFixed(1)}${suffix}`
}

/**
 * Get trend arrow based on direction
 * @param {string} direction - "up", "down", "stable"
 * @returns {string} - Arrow emoji
 */
export function getTrendArrow(direction) {
  const arrows = {
    up: "↗",
    down: "↘",
    stable: "→",
    improving: "↘",
    worsening: "↗"
  }
  return arrows[direction] || "→"
}

/**
 * Truncate string with ellipsis
 * @param {string} str - String to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} - Truncated string
 */
export function truncate(str, maxLength = 50) {
  if (!str || typeof str !== 'string') return ""
  if (str.length <= maxLength) return str
  return str.substring(0, maxLength - 3) + "..."
}