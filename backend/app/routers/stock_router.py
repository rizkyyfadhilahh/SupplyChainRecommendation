from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from app.limiter import limiter

from app.schemas import SLOCConfigRequest
from app.utils import require_api_key
from app.services.stock_service import (
    get_sloc_master_service,
    refresh_stock_snapshot_service,
)
from app.services.sloc_config_service import update_sloc_config_service

router = APIRouter(
    prefix="/api",
    tags=["stock"],
    dependencies=[Depends(require_api_key)],
)

@router.get("/sloc-master")
@limiter.limit("100/minute")
def get_sloc_master(request: Request, facility: Optional[str] = None) -> Dict[str, Any]:
    try:
        return get_sloc_master_service(facility)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
@router.post("/sloc-config")
@limiter.limit("30/minute")
def update_sloc_config(request: Request, body: SLOCConfigRequest) -> Dict[str, Any]:
    return update_sloc_config_service(body)

@router.post("/stock-refresh")
@limiter.limit("30/minute")
def refresh_stock_snapshot(request: Request) -> Dict[str, Any]:
    return refresh_stock_snapshot_service()
