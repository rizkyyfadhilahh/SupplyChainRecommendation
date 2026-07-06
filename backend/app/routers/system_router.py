import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict
from app.data_loader import load_application_data
from app.state import clear_db_cache

def reload_task():
    clear_db_cache()
    load_application_data()

router = APIRouter(prefix="/api/system", tags=["system"])

@router.post("/reload")
async def reload_data(background_tasks: BackgroundTasks) -> Dict[str, str]:
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
