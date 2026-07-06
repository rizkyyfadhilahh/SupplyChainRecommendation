/**
 * Recommendation service layer
 * Handles all recommendation-related API calls
 */

import { get, post, postWithPolling } from './api'
import { validateRecommendationOption, validateScenarioParams } from '../utils/validators'

/**
 * Generate recommendations for orders
 * @param {Array<object>} orders - List of orders
 * @returns {Promise<object>} - Recommendation results
 */
export async function generateRecommendations(orders) {
  if (!Array.isArray(orders) || orders.length === 0) {
    throw new Error('Orders array is required')
  }
  
  const response = await postWithPolling('/api/trace-bulk', { orders })
  
  // Validate response structure
  if (!response.results || !Array.isArray(response.results)) {
    throw new Error('Invalid recommendation response format')
  }
  
  return response
}

/**
 * Get confidence metrics for recommendations
 * @param {string} recommendationId - Recommendation ID
 * @returns {Promise<object>} - Confidence metrics
 */
export async function getConfidenceMetrics(recommendationId) {
  if (!recommendationId) {
    throw new Error('Recommendation ID is required')
  }
  
  return get(`/api/recommendation/${recommendationId}/confidence`)
}

/**
 * Simulate what-if scenario
 * @param {object} baseRecommendation - Base recommendation data
 * @param {object} scenarioParams - Scenario parameters
 * @returns {Promise<object>} - Simulated results
 */
export async function simulateScenario(baseRecommendation, scenarioParams) {
  // Validate scenario parameters
  const validation = validateScenarioParams(scenarioParams)
  if (!validation.valid) {
    throw new Error(`Invalid scenario parameters: ${validation.errors.join(', ')}`)
  }
  
  const payload = {
    base_recommendation: baseRecommendation,
    scenario: {
      demand_volume_pct: scenarioParams.demandVolume || 100,
      fuel_price_pct: scenarioParams.fuelPrice || 100,
      carbon_cap_pct: scenarioParams.carbonCap || 100,
    }
  }
  
  return postWithPolling('/api/recommendation/simulate-scenario', payload)
}

/**
 * Get PCF breakdown with stage details
 * @param {string} routeId - Route ID
 * @returns {Promise<object>} - PCF breakdown data
 */
export async function getPCFBreakdown(routeId) {
  if (!routeId) {
    throw new Error('Route ID is required')
  }
  
  return get(`/api/route/${routeId}/pcf-breakdown`)
}

/**
 * Get trend data for recommendation metrics
 * @param {string} facility - Facility name
 * @param {string} product - Product code
 * @param {number} weeks - Number of weeks to look back
 * @returns {Promise<object>} - Trend data
 */
export async function getRecommendationTrends(facility, product, weeks = 4) {
  return get('/api/recommendation/trends', {
    facility,
    product,
    lookback_weeks: weeks
  })
}

/**
 * Compare multiple recommendation options
 * @param {Array<object>} options - Recommendation options to compare
 * @returns {Promise<object>} - Comparison analysis
 */
export async function compareRecommendations(options) {
  if (!Array.isArray(options) || options.length < 2) {
    throw new Error('At least 2 options required for comparison')
  }
  
  // Validate each option
  const invalidOptions = options.filter(opt => !validateRecommendationOption(opt))
  if (invalidOptions.length > 0) {
    throw new Error(`Invalid recommendation options: ${invalidOptions.length} invalid`)
  }
  
  return post('/api/recommendation/compare', { options })
}

/**
 * Get carbon offset cost estimation
 * @param {number} totalPCF - Total PCF in kg CO2e
 * @param {string} offsetType - Type of offset (reforestation, renewable, etc)
 * @returns {Promise<object>} - Offset cost estimation
 */
export async function getOffsetCostEstimate(totalPCF, offsetType = 'mixed') {
  if (typeof totalPCF !== 'number' || totalPCF <= 0) {
    throw new Error('Valid total PCF is required')
  }
  
  return get('/api/carbon/offset-estimate', {
    pcf_kg: totalPCF,
    offset_type: offsetType
  })
}

/**
 * Save recommendation as template
 * @param {object} recommendation - Recommendation data
 * @param {string} templateName - Template name
 * @returns {Promise<object>} - Saved template
 */
export async function saveAsTemplate(recommendation, templateName) {
  if (!recommendation || !templateName) {
    throw new Error('Recommendation and template name are required')
  }
  
  return post('/api/recommendation/save-template', {
    recommendation,
    template_name: templateName
  })
}

/**
 * Load recommendation templates
 * @param {string} facility - Optional facility filter
 * @returns {Promise<Array>} - List of templates
 */
export async function getTemplates(facility = null) {
  return get('/api/recommendation/templates', { facility })
}

/**
 * Apply template to new order
 * @param {string} templateId - Template ID
 * @param {object} orderData - New order data
 * @returns {Promise<object>} - Applied recommendation
 */
export async function applyTemplate(templateId, orderData) {
  if (!templateId || !orderData) {
    throw new Error('Template ID and order data are required')
  }
  
  return post(`/api/recommendation/apply-template/${templateId}`, orderData)
}

export default {
  generateRecommendations,
  getConfidenceMetrics,
  simulateScenario,
  getPCFBreakdown,
  getRecommendationTrends,
  compareRecommendations,
  getOffsetCostEstimate,
  saveAsTemplate,
  getTemplates,
  applyTemplate
}