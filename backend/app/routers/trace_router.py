from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse
from app.limiter import limiter

from app.schemas import TraceRequest
from app.utils import require_api_key
from app.services.trace_service import trace_orders_service
from app.services.recommendation_engine import get_recommendation_engine
from app.job_manager import start_background_task, get_job_status

def _run_trace_orders(body: TraceRequest) -> Dict[str, Any]:
    trace_response = trace_orders_service(body)
    engine = get_recommendation_engine()
    
    order_results = trace_response.get("orders", [])
    batch_summary = trace_response.get("batch_summary", {})
    
    enriched_results = []
    for i, result in enumerate(order_results):
        order = body.orders[i]
        metric = getattr(order, "recommendation_metric", "VOLUME")
        
        if not engine.validate_metric_request(metric):
            raise ValueError(f"Invalid recommendation_metric: {metric}")
        
        facility = order.facility
        enriched_result = engine.apply_recommendation_metric(result, metric, facility)
        enriched_results.append(enriched_result)
    
    return {"results": enriched_results, "batch_summary": batch_summary}

router = APIRouter(
    prefix="/api",
    tags=["trace"],
    dependencies=[Depends(require_api_key)],
)

@router.post("/trace", response_class=ORJSONResponse)
@limiter.limit("30/minute")
async def trace_orders(request: Request, body: TraceRequest) -> Dict[str, Any]:
    """
    Trace orders and apply recommendation filtering.
    """
    job_id = start_background_task(_run_trace_orders, body)
    return {"job_id": job_id}

@router.get("/status/{job_id}", response_class=ORJSONResponse)
def get_trace_job_status(job_id: str) -> Dict[str, Any]:
    status = get_job_status(job_id)
    if status.get("status") == "UNKNOWN":
        raise HTTPException(status_code=404, detail="Job not found")
    return status
