/**
 * Drilldown service layer
 * Handles all supply chain drilldown and traceability API calls
 */

import { get, post, postWithPolling } from './api'

/**
 * Get list of buyers for drilldown
 * @returns {Promise<object>} - Buyers list
 */
export async function getBuyers() {
  return get('/api/drilldown/buyers')
}

/**
 * Get product context for buyer
 * @param {number} buyerId - Buyer ID
 * @param {string} productCode - Product code
 * @returns {Promise<object>} - Product context data
 */
export async function getProductContext(buyerId, productCode) {
  if (!buyerId || !productCode) {
    throw new Error('Buyer ID and product code are required')
  }
  
  return post('/api/drilldown/product-context', {
    buyer_id: buyerId,
    product_code: productCode
  })
}

/**
 * Resolve supply gap with alternative routes
 * @param {number} buyerId - Buyer ID
 * @param {string} productCode - Product code
 * @returns {Promise<object>} - Gap resolution routes
 */
export async function resolveGap(buyerId, productCode) {
  if (!buyerId || !productCode) {
    throw new Error('Buyer ID and product code are required')
  }
  
  return postWithPolling('/api/drilldown/resolve-gap', {
    buyer_id: buyerId,
    product_code: productCode
  })
}

/**
 * Get blast radius analysis for a node
 * @param {string} nodeId - Supply chain node ID
 * @param {string} nodeType - Node type (ESTATE, MILL, REFINERY)
 * @param {object} disruptionScenario - Disruption scenario details
 * @returns {Promise<object>} - Blast radius impact data
 */
export async function getBlastRadiusImpact(nodeId, nodeType, disruptionScenario = {}) {
  if (!nodeId || !nodeType) {
    throw new Error('Node ID and type are required')
  }
  
  const payload = {
    node_id: nodeId,
    node_type: nodeType,
    disruption: {
      type: disruptionScenario.type || 'delay',
      duration_days: disruptionScenario.durationDays || 3,
      severity: disruptionScenario.severity || 'moderate'
    }
  }
  
  return post('/api/drilldown/blast-radius', payload)
}

/**
 * Get historical shipment details
 * @param {string} shipmentId - Shipment ID or BL number
 * @returns {Promise<object>} - Shipment details
 */
export async function getShipmentDetails(shipmentId) {
  if (!shipmentId) {
    throw new Error('Shipment ID is required')
  }
  
  return get(`/api/drilldown/shipment/${shipmentId}`)
}

/**
 * Get capacity heatmap for refineries
 * @param {number} year - Year for capacity data
 * @returns {Promise<object>} - Capacity heatmap data
 */
export async function getCapacityHeatmap(year = new Date().getFullYear()) {
  return get('/api/drilldown/capacity-heatmap', { year })
}

/**
 * Trace complete supply chain for a product
 * @param {string} productId - Product ID
 * @param {string} facility - Facility name
 * @returns {Promise<object>} - Complete supply chain trace
 */
export async function traceSupplyChain(productId, facility) {
  if (!productId || !facility) {
    throw new Error('Product ID and facility are required')
  }
  
  return postWithPolling('/api/drilldown/trace-supply-chain', {
    product_id: productId,
    facility
  })
}

/**
 * Get node dependencies (upstream and downstream)
 * @param {string} nodeId - Node ID
 * @param {string} direction - 'upstream', 'downstream', or 'both'
 * @returns {Promise<object>} - Node dependencies
 */
export async function getNodeDependencies(nodeId, direction = 'both') {
  if (!nodeId) {
    throw new Error('Node ID is required')
  }
  
  return get(`/api/drilldown/node/${nodeId}/dependencies`, { direction })
}

/**
 * Get historical performance metrics for a route
 * @param {string} routeId - Route ID
 * @param {number} months - Number of months to look back
 * @returns {Promise<object>} - Performance metrics
 */
export async function getRoutePerformance(routeId, months = 6) {
  if (!routeId) {
    throw new Error('Route ID is required')
  }
  
  return get(`/api/drilldown/route/${routeId}/performance`, {
    lookback_months: months
  })
}

/**
 * Get alternative routes for a given node
 * @param {string} nodeId - Current node ID
 * @param {string} targetNodeType - Target node type to find alternatives for
 * @returns {Promise<Array>} - List of alternative routes
 */
export async function getAlternativeRoutes(nodeId, targetNodeType) {
  if (!nodeId || !targetNodeType) {
    throw new Error('Node ID and target node type are required')
  }
  
  return get('/api/drilldown/alternative-routes', {
    node_id: nodeId,
    target_type: targetNodeType
  })
}

/**
 * Export shipment details to CSV/Excel
 * @param {Array<string>} shipmentIds - List of shipment IDs
 * @param {string} format - Export format ('csv' or 'excel')
 * @returns {Promise<Blob>} - Export file blob
 */
export async function exportShipments(shipmentIds, format = 'csv') {
  if (!Array.isArray(shipmentIds) || shipmentIds.length === 0) {
    throw new Error('Shipment IDs array is required')
  }
  
  const response = await fetch('/api/backend/api/drilldown/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ shipment_ids: shipmentIds, format })
  })
  
  if (!response.ok) {
    throw new Error('Export failed')
  }
  
  return response.blob()
}

/**
 * Get risk assessment for a supply chain path
 * @param {Array<object>} supplyChainPath - Supply chain path nodes
 * @returns {Promise<object>} - Risk assessment
 */
export async function assessSupplyChainRisk(supplyChainPath) {
  if (!Array.isArray(supplyChainPath) || supplyChainPath.length === 0) {
    throw new Error('Supply chain path is required')
  }
  
  return post('/api/drilldown/risk-assessment', {
    supply_chain_path: supplyChainPath
  })
}

export default {
  getBuyers,
  getProductContext,
  resolveGap,
  getBlastRadiusImpact,
  getShipmentDetails,
  getCapacityHeatmap,
  traceSupplyChain,
  getNodeDependencies,
  getRoutePerformance,
  getAlternativeRoutes,
  exportShipments,
  assessSupplyChainRisk
}