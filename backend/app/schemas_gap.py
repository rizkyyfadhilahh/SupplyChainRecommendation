from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class GapAnalysisRequest(BaseModel):
    """Request payload for /api/gap-analysis and /api/gap-fulfillment."""
    buyer_name: str = Field(min_length=1, description="Exact buyer name (see GET /api/buyers)")
    facility: str = Field(min_length=1, description="Destination refinery facility name")


# ---------------------------------------------------------------------------
# Buyer Profiles
# ---------------------------------------------------------------------------

class BuyerProfile(BaseModel):
    """Enriched buyer profile for the frontend dropdown."""
    name: str
    country: str
    segment: str
    max_pcf_limit: float
    preferred_products: List[str]


class BuyersListResponse(BaseModel):
    """Response for GET /api/buyers."""
    buyers: List[BuyerProfile]


# ---------------------------------------------------------------------------
# Gap Analysis Response
# ---------------------------------------------------------------------------

class ProjectionData(BaseModel):
    """Projected demand data for the target year."""
    annual_kg: float
    monthly_average_kg: float
    product_breakdown: Dict[str, float]
    projection_year: int
    confidence_score: float


class SupplyBaselineData(BaseModel):
    """Supply baseline data for the selected facility."""
    available_supply_kg: float
    monthly_capacity_kg: float
    utilization_rate: float


class GapData(BaseModel):
    """Gap (shortfall) analysis result."""
    fulfillment_rate_percent: float
    shortfall_kg: float
    shortfall_percentage: float
    gap_status: str  # FULFILLED | MINOR | MODERATE | CRITICAL


class GapAnalysisResponse(BaseModel):
    """Full gap analysis response."""
    buyer_name: str
    facility: str
    max_pcf_limit: float
    segment: str
    country: str
    preferred_products: List[str]
    projected_demand: ProjectionData
    supply_baseline: SupplyBaselineData
    gap_analysis: GapData


# ---------------------------------------------------------------------------
# Enterprise Metrics (per-route)
# ---------------------------------------------------------------------------

class PCFScoreMetric(BaseModel):
    """Metric 1: Universal PCF score."""
    metric_name: str
    pcf_total_kg_co2e: float
    pcf_per_unit_kg_co2e_per_kg: float
    benchmark_compliance: str       # COMPLIANT | AT_RISK | NON_COMPLIANT
    buyer_pcf_limit: Optional[float] = None
    buyer_compliance: Optional[str] = None   # WITHIN_LIMIT | EXCEEDS_LIMIT


class CapacityMetric(BaseModel):
    """Metric 2: Capacity constraints."""
    facility: str
    current_capacity_percent: float
    additional_load_percent: float
    projected_utilization_percent: float
    warning_state: str              # NORMAL | WARNING | CRITICAL
    can_fulfill: bool


class DistanceMetric(BaseModel):
    """Metric 3: Route Distance."""
    total_distance_km: float
    efficiency_score_percent: float
    efficiency_level: str           # HIGH | MEDIUM | LOW


class VolumeSimilarityMetric(BaseModel):
    """Metric 4: Historical volume similarity."""
    volume_similarity_percent: float
    routed_volume_kg: float
    historical_average_kg: float
    deviation_percent: float
    risk_level: str                 # LOW | MEDIUM | HIGH


class AllEnterpriseMetrics(BaseModel):
    """
    All 4 enterprise metrics bundled for a single route option.
    Matches the dict returned by EnterpriseMetricsCalculator.calculate_all_metrics().
    """
    metrics: Dict[str, Any]         # keyed: pcf_score, capacity_constraints, route_distance, volume_similarity
    overall_score: float
    recommendation: str             # OPTIMAL | ACCEPTABLE | RISKY


# ---------------------------------------------------------------------------
# Gap Fulfillment Routes
# ---------------------------------------------------------------------------

class GapFulfillmentRoute(BaseModel):
    """A single recommended route designed to fill the supply gap."""
    route_id: str
    route_label: str                # e.g. "Volume-Optimized"
    facility: str
    routed_volume_kg: float
    supply_chain_path: List[Dict[str, Any]]
    enterprise_metrics: AllEnterpriseMetrics
    estimated_days: int
    fulfillment_share_percent: float
    optimization_focus: str         # VOLUME | PCF | DISTANCE


class GapFulfillmentResponse(BaseModel):
    """Full gap fulfillment response: gap analysis + recommended routes."""
    gap_analysis: GapAnalysisResponse
    recommended_routes: List[GapFulfillmentRoute]
    total_routed_volume_kg: float
    combined_fulfillment_percent: float
