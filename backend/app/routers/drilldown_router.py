import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse
from app.limiter import limiter

from app.schemas_drilldown import ProductContextRequest, ResolutionRequest
from app.utils import require_api_key
from app.services.drilldown_service import (
    get_buyers_list as drilldown_get_buyers,
    get_product_context,
    get_resolution_routes_from_trace,
    get_capacity_heatmap,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/drilldown",
    tags=["drilldown"],
    dependencies=[Depends(require_api_key)],
)

@router.get("/buyers")
@limiter.limit("100/minute")
def drilldown_buyers(request: Request) -> Dict[str, Any]:
    """
    Step 1 — Return all global buyers with their historical product list.
    Used to populate the buyer dropdown in the Drill-Down Dashboard.
    """
    return {"buyers": drilldown_get_buyers()}

@router.post("/product-context", response_class=ORJSONResponse)
@limiter.limit("30/minute")
def drilldown_product_context(request: Request, body: ProductContextRequest) -> Dict[str, Any]:
    """
    Step 2 & 3 — Given a buyer + product, return historical context and gap verdict.
    """
    try:
        result = get_product_context(body.buyer_id, body.product_code)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("drilldown_product_context error")
        raise HTTPException(status_code=500, detail="Internal error computing product context")

@router.post("/resolve-gap", response_class=ORJSONResponse)
@limiter.limit("30/minute")
async def drilldown_resolve_gap(request: Request, body: ResolutionRequest) -> Dict[str, Any]:
    """
    Step 4 — ONLY activates when has_gap is True.
    Calls real /api/trace logic first; falls back to dummy if no CSV data is loaded.
    """
    try:
        context = get_product_context(body.buyer_id, body.product_code)
        if not context["forecast"]["has_gap"]:
            return {
                "has_gap":  False,
                "message":  "No gap detected. Historical route fully covers projected demand.",
                "routes":   [],
            }
        result = await get_resolution_routes_from_trace(body.buyer_id, body.product_code, context)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("drilldown_resolve_gap error")
        raise HTTPException(status_code=500, detail="Internal error generating resolution routes")

@router.get("/capacity-heatmap", response_class=ORJSONResponse)
@limiter.limit("100/minute")
def drilldown_capacity_heatmap(request: Request) -> Dict[str, Any]:
    """
    Returns current-year capacity utilization per refinery for the heatmap widget.
    """
    return get_capacity_heatmap()
