import uuid
import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Job Store
# ---------------------------------------------------------------------------
# In-memory store sufficient for single-instance deployments.
# For multi-instance deployments, replace with Redis.
JOB_STORE: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Thread pool
# ---------------------------------------------------------------------------
# NOTE: We intentionally use ThreadPoolExecutor (not ProcessPoolExecutor)
# because the worker functions share in-process APP_DATA (pandas DataFrames
# loaded at startup).  A separate *process* would have no access to that
# in-memory state and would need to reload the entire dataset.
#
# The GIL is released during pandas/numpy and SQLite I/O operations, so
# threads still provide real concurrency for these workloads.
#
# Tuning: use (2 * CPU_COUNT) workers so that while one thread waits on
# SQLite I/O, another can run CPU-bound trace logic.
_WORKER_COUNT = max(4, (os.cpu_count() or 2) * 2)
_executor = ThreadPoolExecutor(max_workers=_WORKER_COUNT, thread_name_prefix="sc_worker")
logger.info("Job executor initialised with %d workers", _WORKER_COUNT)

# ---------------------------------------------------------------------------
# Job TTL cleanup (avoid unbounded growth)
# ---------------------------------------------------------------------------
_JOB_TTL_SECONDS = 3600  # Keep completed jobs for 1 hour

def _evict_stale_jobs() -> None:
    """Remove completed/failed jobs older than TTL to prevent memory leak."""
    now = time.time()
    stale = [
        jid for jid, meta in list(JOB_STORE.items())
        if meta.get("status") in ("COMPLETED", "FAILED")
        and now - meta.get("created_at", now) > _JOB_TTL_SECONDS
    ]
    for jid in stale:
        JOB_STORE.pop(jid, None)
    if stale:
        logger.debug("Evicted %d stale jobs", len(stale))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_background_task(func, *args) -> str:
    """
    Submit a function to the thread pool and return a job_id.
    The caller can poll get_job_status(job_id) to check progress.
    """
    # Evict stale jobs on every submission (cheap, amortised O(1))
    _evict_stale_jobs()

    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {
        "status": "PENDING",
        "result": None,
        "error": None,
        "created_at": time.time(),
    }

    def _done_callback(future):
        try:
            result = future.result()
            JOB_STORE[job_id]["status"] = "COMPLETED"
            JOB_STORE[job_id]["result"] = result
            JOB_STORE[job_id]["finished_at"] = time.time()
        except Exception as exc:
            logger.exception("Background job %s failed", job_id)
            JOB_STORE[job_id]["status"] = "FAILED"
            JOB_STORE[job_id]["error"] = str(exc)
            JOB_STORE[job_id]["finished_at"] = time.time()

    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(_executor, func, *args)
    future.add_done_callback(_done_callback)
    
    return job_id


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Return the current status dict for job_id, or UNKNOWN if not found."""
    return JOB_STORE.get(job_id, {"status": "UNKNOWN"})
