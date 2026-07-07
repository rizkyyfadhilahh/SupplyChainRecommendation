import uuid
import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from app.job_store import get_job_store

logger = logging.getLogger(__name__)

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
# Job TTL — completed jobs are kept for this long before eviction.
# For RedisJobStore the TTL is enforced by Redis itself via EXPIRE;
# for InMemoryJobStore it is swept on each new job submission.
# ---------------------------------------------------------------------------
_JOB_TTL_SECONDS = 3600

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_background_task(func, *args) -> str:
    """
    Submit *func* to the thread pool and return a job_id.

    The caller polls get_job_status(job_id) to check progress.
    Job state is persisted in the configured JobStore (in-memory by default;
    Redis when REDIS_URL env var is set).
    """
    store = get_job_store()

    # Evict stale entries before writing a new one (amortised, cheap).
    store.evict_stale(_JOB_TTL_SECONDS)

    job_id = str(uuid.uuid4())
    store.set(job_id, {
        "status": "PENDING",
        "result": None,
        "error": None,
        "created_at": time.time(),
    })

    def _done_callback(future):
        try:
            result = future.result()
            store.update(job_id, {
                "status": "COMPLETED",
                "result": result,
                "finished_at": time.time(),
            })
        except Exception as exc:
            logger.exception("Background job %s failed", job_id)
            store.update(job_id, {
                "status": "FAILED",
                "error": str(exc),
                "finished_at": time.time(),
            })

    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(_executor, func, *args)
    future.add_done_callback(_done_callback)
    
    return job_id


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Return the current status dict for *job_id*.

    Returns ``{"status": "UNKNOWN"}`` if the job does not exist in the store.
    Works correctly across multiple Uvicorn workers when RedisJobStore is active.
    """
    return get_job_store().get(job_id)
