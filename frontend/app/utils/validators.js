/**
 * Validation utilities for data integrity
 * Provides type-safe validation for API responses and user inputs
 */

import { sanitizeNumber, validateSchema } from './security'

/**
 * Validate recommendation option data structure
 * @param {object} option - Recommendation option to validate
 * @returns {boolean} - Validation result
 */
export function validateRecommendationOption(option) {
  if (!option || typeof option !== 'object') return false
  
  const requiredFields = {
    option_type: 'string',
    pcf_per_unit_kg_co2e: 'number',
    forecast_summary: 'object'
  }
  
  return validateSchema(option, requiredFields)
}

/**
 * Validate PCF breakdown structure
 * @param {object} pcfData - PCF breakdown data
 * @returns {boolean} - Validation result
 */
export function validatePCFBreakdown(pcfData) {
  if (!pcfData || typeof pcfData !== 'object') return false
  
  const requiredStages = [
    'stage1_harvest_emission_kg_co2e',
    'stage2_transport_estate_to_mill_kg_co2e',
    'stage3_mill_processing_emission_kg_co2e',
    'stage4_transport_mill_to_refinery_kg_co2e',
    'stage5_refinery_processing_emission_kg_co2e',
    'total_kg_co2e'
  ]
  
  return requiredStages.every(stage => 
    typeof pcfData[stage] === 'number' && Number.isFinite(pcfData[stage])
  )
}

/**
 * Validate confidence score (0-100)
 * @param {number} score - Confidence score
 * @returns {boolean} - Validation result
 */
export function validateConfidenceScore(score) {
  const num = Number(score)
  return Number.isFinite(num) && num >= 0 && num <= 100
}

/**
 * Validate trend data structure
 * @param {object} trendData - Trend data
 * @returns {boolean} - Validation result
 */
export function validateTrendData(trendData) {
  if (!trendData || typeof trendData !== 'object') return false
  
  const validDirections = ['improving', 'worsening', 'stable', 'up', 'down']
  
  return (
    validDirections.includes(trendData.direction) &&
    typeof trendData.change_pct === 'number' &&
    Number.isFinite(trendData.change_pct)
  )
}

/**
 * Validate supply chain node
 * @param {object} node - Supply chain node data
 * @returns {boolean} - Validation result
 */
export function validateSupplyChainNode(node) {
  if (!node || typeof node !== 'object') return false
  
  const validTypes = ['ESTATE', 'MILL', 'REFINERY', 'FACTORY', 'WAREHOUSE']
  
  return (
    typeof node.supplier_id === 'string' &&
    validTypes.includes(node.supplier_type) &&
    typeof node.quantity === 'number' &&
    Number.isFinite(node.quantity) &&
    node.quantity >= 0
  )
}

/**
 * Validate date string
 * @param {string} dateStr - Date string to validate
 * @returns {boolean} - Validation result
 */
export function validateDate(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return false
  
  const date = new Date(dateStr)
  return !isNaN(date.getTime())
}

/**
 * Validate percentage value
 * @param {number} value - Percentage to validate
 * @param {boolean} isDecimal - True if 0-1, false if 0-100
 * @returns {boolean} - Validation result
 */
export function validatePercentage(value, isDecimal = false) {
  const num = Number(value)
  if (!Number.isFinite(num)) return false
  
  if (isDecimal) {
    return num >= 0 && num <= 1
  }
  
  return num >= 0 && num <= 100
}

/**
 * Validate scenario parameters for What-If simulator
 * @param {object} params - Scenario parameters
 * @returns {object} - { valid: boolean, errors: string[] }
 */
export function validateScenarioParams(params) {
  const errors = []
  
  if (!params || typeof params !== 'object') {
    return { valid: false, errors: ['Invalid parameters object'] }
  }
  
  // Demand volume: 50-200%
  if (params.demandVolume !== undefined) {
    const demand = Number(params.demandVolume)
    if (!Number.isFinite(demand) || demand < 50 || demand > 200) {
      errors.push('Demand volume must be between 50% and 200%')
    }
  }
  
  // Fuel price: 80-150%
  if (params.fuelPrice !== undefined) {
    const fuel = Number(params.fuelPrice)
    if (!Number.isFinite(fuel) || fuel < 80 || fuel > 150) {
      errors.push('Fuel price must be between 80% and 150%')
    }
  }
  
  // Carbon cap: 70-120%
  if (params.carbonCap !== undefined) {
    const carbon = Number(params.carbonCap)
    if (!Number.isFinite(carbon) || carbon < 70 || carbon > 120) {
      errors.push('Carbon cap must be between 70% and 120%')
    }
  }
  
  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * Validate blast radius impact data
 * @param {object} impactData - Impact data
 * @returns {boolean} - Validation result
 */
export function validateBlastRadiusImpact(impactData) {
  if (!impactData || typeof impactData !== 'object') return false
  
  const validSeverities = ['critical', 'moderate', 'minor']
  
  return (
    typeof impactData.node_id === 'string' &&
    validSeverities.includes(impactData.severity) &&
    typeof impactData.days_until_impact === 'number' &&
    Number.isFinite(impactData.days_until_impact)
  )
}

/**
 * Validate enterprise metrics
 * @param {object} metrics - Enterprise metrics data
 * @returns {boolean} - Validation result
 */
export function validateEnterpriseMetrics(metrics) {
  if (!metrics || typeof metrics !== 'object') return false
  
  const validRecommendations = ['OPTIMAL', 'ACCEPTABLE', 'RISKY']
  
  return (
    validRecommendations.includes(metrics.recommendation) &&
    typeof metrics.overall_score === 'number' &&
    Number.isFinite(metrics.overall_score) &&
    metrics.overall_score >= 0 &&
    metrics.overall_score <= 100
  )
}

/**
 * Safe number extraction with bounds
 * @param {any} value - Value to extract
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @param {number} defaultValue - Default if invalid
 * @returns {number} - Safe number
 */
export function safeNumber(value, min = 0, max = Infinity, defaultValue = 0) {
  return sanitizeNumber(value, min, max, defaultValue)
}

/**
 * Validate and sanitize array of objects
 * @param {Array} arr - Array to validate
 * @param {Function} validator - Validator function for each item
 * @returns {Array} - Validated array
 */
export function validateArray(arr, validator) {
  if (!Array.isArray(arr)) return []
  return arr.filter(item => validator(item))
}