"""
Abstract base class for job store implementations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class JobStore(ABC):
    """Interface that all job store backends must implement."""

    @abstractmethod
    def set(self, job_id: str, data: Dict[str, Any]) -> None:
        """Create or fully replace a job record."""

    @abstractmethod
    def update(self, job_id: str, data: Dict[str, Any]) -> None:
        """Merge *data* into an existing job record.

        If the job does not exist, behaves like set().
        """

    @abstractmethod
    def get(self, job_id: str) -> Dict[str, Any]:
        """Return the job record, or {"status": "UNKNOWN"} if not found."""

    @abstractmethod
    def evict_stale(self, ttl_seconds: int) -> None:
        """Remove completed/failed jobs older than *ttl_seconds*."""