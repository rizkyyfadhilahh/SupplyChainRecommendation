"""
Job store abstraction — pluggable backend for async job state.

Usage:
    from app.job_store import get_job_store

    store = get_job_store()
    store.set(job_id, {"status": "PENDING", ...})
    store.get(job_id)

The active implementation is chosen at import time based on REDIS_URL:
  - REDIS_URL set   → RedisJobStore  (supports multiple Uvicorn workers)
  - REDIS_URL unset → InMemoryJobStore (single-process, default)
"""
import os
from app.job_store.base import JobStore
from app.job_store.memory_store import InMemoryJobStore

_store: JobStore | None = None


def get_job_store() -> JobStore:
    """Return the singleton job store instance.

    Initialised once on first call.  Subsequent calls return the same
    instance so callers never need to worry about construction cost.
    """
    global _store
    if _store is not None:
        return _store

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            from app.job_store.redis_store import RedisJobStore
            _store = RedisJobStore(redis_url)
        except ImportError:
            import logging
            logging.getLogger(__name__).warning(
                "REDIS_URL is set but 'redis' package is not installed. "
                "Falling back to InMemoryJobStore. "
                "Install it with: pip install redis"
            )
            _store = InMemoryJobStore()
    else:
        _store = InMemoryJobStore()

    return _store