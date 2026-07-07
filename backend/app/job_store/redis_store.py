"""
Redis-backed job store — required for multi-worker (WEB_CONCURRENCY > 1) deployments.

Each job is stored as a Redis hash under the key "sc:job:{job_id}" with a
TTL of _JOB_TTL_SECONDS so stale entries are cleaned up automatically by Redis
rather than a background sweep.

Requires: pip install redis
"""
import json
import logging
import time
from typing import Any, Dict

from app.job_store.base import JobStore

logger = logging.getLogger(__name__)

_KEY_PREFIX = "sc:job:"
_JOB_TTL_SECONDS = 3600  # Redis expires the key automatically after 1 hour


class RedisJobStore(JobStore):
    def __init__(self, redis_url: str) -> None:
        import redis  # imported lazily so missing package gives a clear error

        self._client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        # Verify connectivity at construction time so a misconfigured REDIS_URL
        # fails loudly at startup rather than silently at first job submission.
        self._client.ping()
        logger.info("RedisJobStore connected to %s", redis_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, job_id: str) -> str:
        return f"{_KEY_PREFIX}{job_id}"

    def _serialize(self, value: Any) -> str:
        """JSON-encode a value for storage in a Redis hash field."""
        return json.dumps(value, default=str)

    def _deserialize(self, raw: str) -> Any:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    # ------------------------------------------------------------------
    # JobStore interface
    # ------------------------------------------------------------------

    def set(self, job_id: str, data: Dict[str, Any]) -> None:
        key = self._key(job_id)
        mapping = {field: self._serialize(val) for field, val in data.items()}
        pipe = self._client.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, _JOB_TTL_SECONDS)
        pipe.execute()

    def update(self, job_id: str, data: Dict[str, Any]) -> None:
        key = self._key(job_id)
        mapping = {field: self._serialize(val) for field, val in data.items()}
        pipe = self._client.pipeline()
        pipe.hset(key, mapping=mapping)
        # Refresh TTL on every update so active jobs don't expire mid-flight.
        pipe.expire(key, _JOB_TTL_SECONDS)
        pipe.execute()

    def get(self, job_id: str) -> Dict[str, Any]:
        key = self._key(job_id)
        raw = self._client.hgetall(key)
        if not raw:
            return {"status": "UNKNOWN"}
        return {field: self._deserialize(val) for field, val in raw.items()}

    def evict_stale(self, ttl_seconds: int) -> None:
        # Redis handles TTL-based expiry automatically via EXPIRE.
        # This method is a no-op for Redis — kept to satisfy the interface.
        pass