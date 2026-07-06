"""
CSV-only mode wrapper - allows running the app without SQLite.
Set environment variable: USE_SQLITE=false
"""
import os
import logging
from typing import Any, Dict
import pandas as pd

logger = logging.getLogger(__name__)

# NOTE: Do NOT cache this as a module-level constant.
# os.getenv() must be read at runtime so that environment changes
# (e.g., $env:USE_SQLITE="false" set in PowerShell before uvicorn)
# are respected, especially with --reload which spawns subprocesses.
# In-memory storage when SQLite is disabled
_CSV_CACHE: Dict[str, pd.DataFrame] = {}

def is_sqlite_enabled() -> bool:
    """Check if SQLite mode is enabled.
    
    Reads USE_SQLITE from the environment at runtime to ensure
    the value is always current, even after --reload subprocess spawns.
    """
    return os.getenv("USE_SQLITE", "true").lower() == "true"

def save_to_csv_cache(table_name: str, df: pd.DataFrame, copy: bool = True) -> None:
    """Save DataFrame to in-memory cache instead of SQLite.
    Use copy=False for very large tables to avoid doubling memory usage.
    """
    if not is_sqlite_enabled():
        _CSV_CACHE[table_name] = df.copy() if copy else df
        logger.info(f"Cached {table_name} in memory ({len(df)} rows)")

def load_from_csv_cache(table_name: str) -> pd.DataFrame:
    """Load DataFrame from in-memory cache."""
    if table_name not in _CSV_CACHE:
        raise KeyError(f"Table {table_name} not found in CSV cache")
    return _CSV_CACHE[table_name].copy()

def table_exists_in_cache(table_name: str) -> bool:
    """Check if table exists in CSV cache."""
    return table_name in _CSV_CACHE

def clear_csv_cache() -> None:
    """Clear all cached DataFrames."""
    _CSV_CACHE.clear()
    logger.info("CSV cache cleared")
