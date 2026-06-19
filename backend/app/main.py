from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from typing import Optional, Dict, Any
from app.middleware import CorrelationIDMiddleware

from app.config import (
    ALLOWED_ORIGINS,
    process_map,
    facility_groups,
    buyer_blacklist,
)

from app.schemas import TraceRequest, SLOCConfigRequest

from app.utils import (
    setup_logging,
    register_exception_handler,
    require_api_key,
)

from app.data_loader import load_application_data

from app.services.stock_service import (
    ensure_sloc_config_seeded,
    get_sloc_master_service,
    refresh_stock_snapshot_service,
)

from app.services.sloc_config_service import update_sloc_config_service
from app.services.trace_service import trace_orders_service

setup_logging()

app = FastAPI(title="Supply Chain Planning API")
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.on_event("startup")
def startup_event() -> None:
    load_application_data()
    ensure_sloc_config_seeded()

register_exception_handler(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

@app.get("/api/options", dependencies=[Depends(require_api_key)])
def get_options() -> Dict[str, Any]:
    return {
        "refineries": list(facility_groups.keys()),
        "buyers": list(buyer_blacklist.keys()),
        "products": list(process_map.keys()),
    }

@app.get("/api/sloc-master", dependencies=[Depends(require_api_key)])
def get_sloc_master(facility: Optional[str] = None) -> Dict[str, Any]:
    try:
        return get_sloc_master_service(facility)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
@app.post("/api/sloc-config")
def update_sloc_config(
    request: SLOCConfigRequest,
    _: None = Depends(require_api_key),
) -> Dict[str, Any]:
    return update_sloc_config_service(request)

@app.post("/api/trace", response_class=ORJSONResponse, dependencies=[Depends(require_api_key)])
def trace_orders(request: TraceRequest) -> Dict[str, Any]:
    return trace_orders_service(request)

@app.post("/api/stock-refresh", dependencies=[Depends(require_api_key)])
def refresh_stock_snapshot() -> Dict[str, Any]:
    return refresh_stock_snapshot_service()

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


 