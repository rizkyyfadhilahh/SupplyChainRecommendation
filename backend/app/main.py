import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Any, Dict
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.limiter import limiter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import ALLOWED_ORIGINS
from app.data_loader import load_application_data
from app.db_seeder import seed_domain_config_to_sqlite
from app.config import reload_domain_config
from app.database import create_performance_indexes
from app.services.stock_service import ensure_sloc_config_seeded
from app.utils import setup_logging, register_exception_handler
from app.middleware import CorrelationIDMiddleware

# Import routers
from app.routers import stock_router, trace_router, gap_router, drilldown_router, config_router, system_router

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Seed domain config to SQLite tables if empty
        await asyncio.to_thread(seed_domain_config_to_sqlite)
        # Reload the configs into memory
        await asyncio.to_thread(reload_domain_config)
        
        # Then load application data
        await asyncio.to_thread(load_application_data)
        await asyncio.to_thread(ensure_sloc_config_seeded)
        
        # ✅ PERFORMANCE: Create indexes AFTER data is loaded
        await asyncio.to_thread(create_performance_indexes)
        
        logger.info("Application data loaded successfully")
    except Exception as e:
        # Log as ERROR (not warning) so it's visible in production logs.
        # The server stays up so gap-analysis endpoints remain available,
        # but trace/stock endpoints will return a clear 503 via the
        # app_data_loaded guard in get_cached_sloc_master.
        logger.error(
            "Application data load FAILED — trace/stock features will be "
            "unavailable until the server is restarted: %s",
            e,
            exc_info=True,
        )
    yield

app = FastAPI(title="Supply Chain Planning API", lifespan=lifespan)

# Middlewares
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

register_exception_handler(app)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(stock_router.router)
app.include_router(trace_router.router)
app.include_router(gap_router.router)
app.include_router(drilldown_router.router)
app.include_router(config_router.router)
app.include_router(system_router.router)

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/health/data")
def health_data() -> Dict[str, Any]:
    """Returns whether application data (plant_to_refinery, events_bc_slim, etc.)
    has been fully loaded into memory.  Use this to check server readiness
    before sending trace/stock requests."""
    from app.state import get_app_data
    loaded = bool(get_app_data("app_data_loaded", False))
    return {
        "status": "ready" if loaded else "initializing",
        "app_data_loaded": loaded,
    }
