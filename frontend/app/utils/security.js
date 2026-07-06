/**
 * Security utilities for safe data handling
 * Prevents XSS, injection attacks, and validates user inputs
 */

/**
 * Sanitize string input to prevent XSS attacks
 * @param {string} str - Input string
 * @returns {string} - Sanitized string
 */
export function sanitizeString(str) {
  if (typeof str !== 'string') return ''
  
  return str
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;')
}

/**
 * Validate and sanitize numeric input
 * @param {any} value - Input value
 * @param {number} min - Minimum allowed value
 * @param {number} max - Maximum allowed value
 * @param {number} defaultValue - Default value if invalid
 * @returns {number} - Validated number
 */
export function sanitizeNumber(value, min = 0, max = Infinity, defaultValue = 0) {
  const num = Number(value)
  
  if (!Number.isFinite(num)) return defaultValue
  if (num < min) return min
  if (num > max) return max
  
  return num
}

/**
 * Validate percentage value (0-100)
 * @param {any} value - Input value
 * @returns {number} - Valid percentage
 */
export function sanitizePercentage(value) {
  return sanitizeNumber(value, 0, 100, 0)
}

/**
 * Safely parse JSON with error handling
 * @param {string} jsonString - JSON string to parse
 * @param {any} defaultValue - Default value on parse error
 * @returns {any} - Parsed object or default value
 */
export function safeJsonParse(jsonString, defaultValue = null) {
  try {
    return JSON.parse(jsonString)
  } catch (error) {
    console.error('JSON parse error:', error)
    return defaultValue
  }
}

/**
 * Validate object structure against schema
 * @param {object} data - Data to validate
 * @param {object} schema - Expected schema
 * @returns {boolean} - Validation result
 */
export function validateSchema(data, schema) {
  if (!data || typeof data !== 'object') return false
  
  for (const [key, type] of Object.entries(schema)) {
    if (!(key in data)) return false
    if (typeof data[key] !== type && data[key] !== null) return false
  }
  
  return true
}

/**
 * Rate limiter for API calls (client-side)
 * @param {Function} fn - Function to rate limit
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} - Rate limited function
 */
export function rateLimit(fn, delay = 1000) {
  let timeoutId = null
  
  return function(...args) {
    if (timeoutId) clearTimeout(timeoutId)
    
    timeoutId = setTimeout(() => {
      fn.apply(this, args)
      timeoutId = null
    }, delay)
  }
}

/**
 * Debounce function for input handlers
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} - Debounced function
 */
export function debounce(fn, delay = 300) {
  let timeoutId = null
  
  return function(...args) {
    if (timeoutId) clearTimeout(timeoutId)
    
    timeoutId = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

/**
 * Generate secure random ID for client-side tracking
 * @returns {string} - Random ID
 */
export function generateSecureId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Validate URL to prevent open redirect vulnerabilities
 * @param {string} url - URL to validate
 * @param {string[]} allowedDomains - List of allowed domains
 * @returns {boolean} - Validation result
 */
export function validateUrl(url, allowedDomains = []) {
  try {
    const urlObj = new URL(url, window.location.origin)
    
    // Only allow relative URLs or allowed domains
    if (urlObj.origin === window.location.origin) return true
    
    return allowedDomains.some(domain => 
      urlObj.hostname === domain || urlObj.hostname.endsWith(`.${domain}`)
    )
  } catch {
    return false
  }
}

/**
 * Sanitize object recursively
 * @param {any} obj - Object to sanitize
 * @param {number} maxDepth - Maximum recursion depth
 * @returns {any} - Sanitized object
 */
export function sanitizeObject(obj, maxDepth = 10) {
  if (maxDepth <= 0) return null
  
  if (typeof obj === 'string') return sanitizeString(obj)
  if (typeof obj === 'number') return sanitizeNumber(obj)
  if (typeof obj === 'boolean') return obj
  if (obj === null || obj === undefined) return obj
  
  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item, maxDepth - 1))
  }
  
  if (typeof obj === 'object') {
    const sanitized = {}
    for (const [key, value] of Object.entries(obj)) {
      sanitized[sanitizeString(key)] = sanitizeObject(value, maxDepth - 1)
    }
    return sanitized
  }
  
  return obj
}