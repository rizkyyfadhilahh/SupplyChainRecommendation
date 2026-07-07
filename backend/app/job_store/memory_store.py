"""
In-memory job store — default for single-process deployments.

Thread-safe via a single RLock.  Not suitable for multi-worker deployments;
use RedisJobStore when WEB_CONCURRENCY > 1.
"""
import time
from threading import RLock
from typing import Any, Dict

from app.job_store.base import JobStore


class InMemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    def set(self, job_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._store[job_id] = dict(data)

    def update(self, job_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            existing = self._store.get(job_id, {})
            existing.update(data)
            self._store[job_id] = existing

    def get(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._store.get(job_id, {"status": "UNKNOWN"}))

    def evict_stale(self, ttl_seconds: int) -> None:
        now = time.time()
        with self._lock:
            stale = [
                jid
                for jid, meta in list(self._store.items())
                if meta.get("status") in ("COMPLETED", "FAILED")
                and now - meta.get("created_at", now) > ttl_seconds
            ]
            for jid in stale:
                self._store.pop(jid, None)