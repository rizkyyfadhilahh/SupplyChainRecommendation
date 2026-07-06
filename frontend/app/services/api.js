/**
 * Centralized API service layer
 * Handles all HTTP requests with error handling, validation, and security
 */

import { sanitizeObject, validateUrl } from '../utils/security'
import { rateLimit } from '../utils/security'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/backend'

/**
 * Custom error class for API errors
 */
export class APIError extends Error {
  constructor(message, status, details = null) {
    super(message)
    this.name = 'APIError'
    this.status = status
    this.details = details
  }
}

/**
 * Fetch wrapper with error handling and timeout
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @param {number} timeout - Request timeout in ms
 * @returns {Promise<any>} - Response data
 */
async function fetchWithTimeout(url, options = {}, timeout = 30000) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
    
    clearTimeout(timeoutId)
    
    // Handle non-2xx responses
    if (!response.ok) {
      let errorData
      try {
        errorData = await response.json()
      } catch {
        errorData = { detail: response.statusText }
      }
      
      throw new APIError(
        errorData.detail || errorData.message || 'API request failed',
        response.status,
        errorData
      )
    }
    
    // Parse JSON response
    const data = await response.json()
    return data
    
  } catch (error) {
    clearTimeout(timeoutId)
    
    if (error.name === 'AbortError') {
      throw new APIError('Request timeout', 408)
    }
    
    if (error instanceof APIError) {
      throw error
    }
    
    // Network errors
    throw new APIError(
      error.message || 'Network error occurred',
      0,
      { originalError: error }
    )
  }
}

/**
 * GET request
 * @param {string} endpoint - API endpoint path
 * @param {object} params - Query parameters
 * @returns {Promise<any>} - Response data
 */
export async function get(endpoint, params = {}) {
  const url = new URL(`${API_BASE_URL}${endpoint}`, window.location.origin)
  
  // Add query parameters
  Object.keys(params).forEach(key => {
    if (params[key] !== undefined && params[key] !== null) {
      url.searchParams.append(key, params[key])
    }
  })
  
  return fetchWithTimeout(url.toString(), {
    method: 'GET',
  })
}

/**
 * POST request
 * @param {string} endpoint - API endpoint path
 * @param {object} data - Request body data
 * @returns {Promise<any>} - Response data
 */
export async function post(endpoint, data = {}) {
  const url = `${API_BASE_URL}${endpoint}`
  
  // Sanitize request data
  const sanitizedData = sanitizeObject(data)
  
  return fetchWithTimeout(url, {
    method: 'POST',
    body: JSON.stringify(sanitizedData),
  })
}

/**
 * PUT request
 * @param {string} endpoint - API endpoint path
 * @param {object} data - Request body data
 * @returns {Promise<any>} - Response data
 */
export async function put(endpoint, data = {}) {
  const url = `${API_BASE_URL}${endpoint}`
  const sanitizedData = sanitizeObject(data)
  
  return fetchWithTimeout(url, {
    method: 'PUT',
    body: JSON.stringify(sanitizedData),
  })
}

/**
 * DELETE request
 * @param {string} endpoint - API endpoint path
 * @returns {Promise<any>} - Response data
 */
export async function del(endpoint) {
  const url = `${API_BASE_URL}${endpoint}`
  
  return fetchWithTimeout(url, {
    method: 'DELETE',
  })
}

/**
 * Poll for job status
 * @param {string} jobId - Job ID to poll
 * @param {number} maxAttempts - Maximum polling attempts
 * @param {number} interval - Polling interval in ms
 * @returns {Promise<any>} - Final job result
 */
export async function pollJobStatus(jobId, maxAttempts = 60, interval = 2000) {
  let attempts = 0
  
  while (attempts < maxAttempts) {
    const statusData = await get(`/api/status/${jobId}`)
    
    if (statusData.status === 'COMPLETED') {
      return statusData.result
    }
    
    if (statusData.status === 'FAILED') {
      throw new APIError(
        statusData.error || 'Job failed',
        500,
        { jobId, status: statusData }
      )
    }
    
    if (statusData.status === 'UNKNOWN') {
      throw new APIError('Job not found', 404, { jobId })
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, interval))
    attempts++
  }
  
  throw new APIError('Job polling timeout', 408, { jobId, attempts })
}

/**
 * Handle long-running requests with job polling
 * @param {string} endpoint - API endpoint
 * @param {object} data - Request data
 * @returns {Promise<any>} - Final result
 */
export async function postWithPolling(endpoint, data = {}) {
  const response = await post(endpoint, data)
  
  // If response has job_id, poll for completion
  if (response.job_id) {
    return pollJobStatus(response.job_id)
  }
  
  // Otherwise return direct result
  return response
}

/**
 * Rate-limited API call wrapper
 * Prevents excessive API calls from client
 */
export const rateLimitedGet = rateLimit(get, 500)
export const rateLimitedPost = rateLimit(post, 1000)

/**
 * Batch multiple GET requests
 * @param {Array<{endpoint: string, params?: object}>} requests - Array of requests
 * @returns {Promise<Array>} - Array of results
 */
export async function batchGet(requests) {
  const promises = requests.map(({ endpoint, params }) => 
    get(endpoint, params).catch(error => ({ error }))
  )
  
  return Promise.all(promises)
}

/**
 * Health check endpoint
 * @returns {Promise<boolean>} - API health status
 */
export async function healthCheck() {
  try {
    await get('/api/health')
    return true
  } catch {
    return false
  }
}

export default {
  get,
  post,
  put,
  del,
  pollJobStatus,
  postWithPolling,
  batchGet,
  healthCheck,
  APIError
}