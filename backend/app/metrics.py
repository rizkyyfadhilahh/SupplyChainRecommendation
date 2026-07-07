"""
Prometheus metrics definitions for the Supply Chain Planning API.

All metrics are registered here in one place so they can be imported
by any module without circular dependencies.

Usage:
    from app.metrics import TRACE_JOBS_SUBMITTED, STOCK_ALLOCATION_DURATION
    TRACE_JOBS_SUBMITTED.inc()
    with STOCK_ALLOCATION_DURATION.time():
        ...
"""
from prometheus_client import Counter, Histogram

# ---------------------------------------------------------------------------
# Trace job counters
# ---------------------------------------------------------------------------

TRACE_JOBS_SUBMITTED = Counter(
    "sc_trace_jobs_submitted_total",
    "Total number of trace jobs submitted to the background executor.",
)

TRACE_JOBS_COMPLETED = Counter(
    "sc_trace_jobs_completed_total",
    "Total number of trace jobs that completed successfully.",
)

TRACE_JOBS_FAILED = Counter(
    "sc_trace_jobs_failed_total",
    "Total number of trace jobs that failed with an exception.",
)

# ---------------------------------------------------------------------------
# Stock allocation latency
# ---------------------------------------------------------------------------

STOCK_ALLOCATION_DURATION = Histogram(
    "sc_stock_allocation_duration_seconds",
    "Time spent inside allocate_stock() per call.",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

# ---------------------------------------------------------------------------
# SLOC cache observability
# ---------------------------------------------------------------------------

SLOC_CACHE_STALE_SERVED = Counter(
    "sc_sloc_cache_stale_served_total",
    "Number of times a stale SLOC cache was returned while a background "
    "rebuild was triggered (stale-while-revalidate hits).",
)
