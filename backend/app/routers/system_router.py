import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import Dict
from app.data_loader import load_application_data
from app.limiter import limiter
from app.state import clear_db_cache
from app.services.forecast_service import reset_forecast_cache

def reload_task():
    # 1. Invalidate the SQLite/CSV DataFrame cache so the next read
    #    fetches fresh rows from the newly loaded tables.
    clear_db_cache()

    # 2. Clear the in-memory edge leadtime masters (EDGE_LEADTIME_MASTER
    #    and ESTATE_EDGE_LEADTIME_MASTER).  Without this, forecast lead
    #    times and throughput values stay stale until server restart even
    #    though the underlying data has changed.
    reset_forecast_cache()

    # 3. Re-run the full data loading pipeline (CSV → SQLite → in-memory).
    load_application_data()

router = APIRouter(prefix="/api/system", tags=["system"])

@router.post("/reload")
@limiter.limit("5/minute")
async def reload_data(request: Request, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Trigger a hot-reload of the core CSV data without restarting the server.
    This runs in the background and updates the in-memory DataFrames and lookups.
    """
    try:
        # Run the heavy data loading process in a background thread 
        # so it doesn't block the FastAPI event loop for other requests.
        background_tasks.add_task(reload_task)
        
        return {
            "message": "Data reload initiated in the background. Fresh data will be available shortly."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate reload: {str(e)}")
