import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse
from app.limiter import limiter

from app.schemas_gap import GapAnalysisRequest
from app.utils import require_api_key
from app.config import facility_groups, buyer_blacklist, process_map
from app.services.gap_analysis_service import get_gap_analysis_service, HistoricalBuyerData
from app.services.enterprise_metrics_service import get_enterprise_metrics_calculator
from app.services.pcf_service import get_pcf_service
from app.job_manager import start_background_task, get_job_status

logger = logging.getLogger(__name__)

def _run_gap_analysis(buyer_name: str, facility: str) -> Dict[str, Any]:
    service = get_gap_analysis_service()
    result = service.analyze_buyer_gap(buyer_name, facility)
    if "error" in result:
        raise ValueError(result["error"])
    return result

def _run_gap_fulfillment(buyer_name: str, facility: str) -> Dict[str, Any]:
    gap_service = get_gap_analysis_service()
    metrics_calc = get_enterprise_metrics_calculator()
    pcf_service = get_pcf_service()

    gap_analysis = gap_service.analyze_buyer_gap(buyer_name, facility)
    if "error" in gap_analysis:
        raise ValueError(gap_analysis["error"])

    return gap_service.generate_fulfillment_routes(
        gap_analysis=gap_analysis,
        buyer_name=buyer_name,
        facility=facility,
        metrics_calc=metrics_calc,
        pcf_service=pcf_service,
    )

router = APIRouter(
    prefix="/api",
    tags=["gap"],
    dependencies=[Depends(require_api_key)],
)

@router.get("/options")
@limiter.limit("100/minute")
def get_options(request: Request) -> Dict[str, Any]:
    return {
        "refineries": list(facility_groups.keys()),
        "buyers": list(buyer_blacklist.keys()),
        "products": list(process_map.keys()),
        "recommendation_metrics": ["VOLUME", "LOWEST_PCF"],
    }

@router.get("/buyers")
@limiter.limit("100/minute")
def get_available_buyers(request: Request) -> Dict[str, Any]:
    """
    Get list of available buyers with enriched profile data for dropdown.
    Returns name, country, segment, max_pcf_limit, and preferred_products.
    """
    profiles = HistoricalBuyerData.get_buyer_profiles()
    return {"buyers": profiles}

@router.post("/gap-analysis", response_class=ORJSONResponse)
@limiter.limit("30/minute")
async def analyze_gap(request: Request, body: GapAnalysisRequest) -> Dict[str, Any]:
    """
    Analyze supply-demand gap for a specific buyer and facility.
    """
    job_id = start_background_task(_run_gap_analysis, body.buyer_name, body.facility)
    return {"job_id": job_id}

@router.post("/gap-fulfillment", response_class=ORJSONResponse)
@limiter.limit("30/minute")
async def gap_fulfillment(request: Request, body: GapAnalysisRequest) -> Dict[str, Any]:
    """
    Generate optimized 3-hop routes (Estate -> Mill -> Refinery) designed
    specifically to fulfill the identified supply gap.
    """
    job_id = start_background_task(_run_gap_fulfillment, body.buyer_name, body.facility)
    return {"job_id": job_id}

@router.get("/status/{job_id}", response_class=ORJSONResponse)
def get_job_status_endpoint(job_id: str) -> Dict[str, Any]:
    status = get_job_status(job_id)
    if status.get("status") == "UNKNOWN":
        raise HTTPException(status_code=404, detail="Job not found")
    return status
