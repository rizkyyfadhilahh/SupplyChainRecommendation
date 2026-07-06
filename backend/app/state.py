import json
import logging
import time
from threading import Lock
from typing import Any, Dict, Optional

import pandas as pd

from app.database import engine
from app.csv_only_mode import is_sqlite_enabled, load_from_csv_cache, table_exists_in_cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Small in-memory lookups (dicts, sets, scalars)
# ---------------------------------------------------------------------------
APP_DATA: Dict[str, Any] = {}

# ---------------------------------------------------------------------------
# DB table names — written to SQLite by data_loader, read back on demand
# ---------------------------------------------------------------------------
DB_TABLES = {
    "master_facility",
    "events_bc",
    "links_bc",
    "facility_lookup",
    "relations_all",
    "product_relations",
    "product_flow",
    "ffb_relations",
    "ffb_flow",
    "tolling_flow",
}

# Tables that are NOT cached in CSV-only mode (derived/intermediate results).
# These are built during data_loader pipeline and not stored in CSV cache.
# Any table in this set will return an empty DataFrame instead of raising an error.
CSV_MODE_SKIP_TABLES = {
    "relations_all",
    "product_relations",
    "ffb_relations",
}

# ---------------------------------------------------------------------------
# DB cache with TTL
# ---------------------------------------------------------------------------
# Store the loaded DataFrame + the timestamp it was loaded.
# Callers get a zero-copy *view*; only mutating callers must call .copy().
_DB_CACHE: Dict[str, Dict[str, Any]] = {}  # {table: {"df": DataFrame, "loaded_at": float}}
_DB_CACHE_LOCK = Lock()
_DB_CACHE_TTL = 600  # seconds — reload from SQLite after 10 minutes

def _deserialize_json_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Decode columns that were serialised as JSON strings during save."""
    for col in df.columns:
        if df[col].dtype != "object":
            continue
        sample = df[col].dropna()
        if sample.empty:
            continue
        first = sample.iloc[0]
        if isinstance(first, str) and first.startswith("["):
            try:
                df[col] = df[col].apply(
                    lambda x: json.loads(x)
                    if isinstance(x, str) and x.startswith("[")
                    else x
                )
            except Exception:
                pass  # leave column as-is
    return df

def _load_table(key: str) -> pd.DataFrame:
    """Load a table from SQLite or CSV cache, deserialise JSON columns, cache the result."""
    start = time.monotonic()
    
    if not is_sqlite_enabled():
        # CSV-only mode: check skip tables BEFORE attempting cache load
        # This is defense-in-depth — get_app_data/require_app_data also check this,
        # but any code path that calls _load_table directly should be guarded too.
        if key in CSV_MODE_SKIP_TABLES:
            logger.debug(
                "_load_table: '%s' is in CSV_MODE_SKIP_TABLES, returning empty DataFrame", key
            )
            return pd.DataFrame()
        # CSV-only mode: load from in-memory cache
        df = load_from_csv_cache(key)
        df = _deserialize_json_cols(df)
        elapsed = time.monotonic() - start
        logger.debug("Loaded table '%s' from CSV cache in %.2fs (%d rows)", key, elapsed, len(df))
        return df
    
    # SQLite mode: load from database
    df = pd.read_sql_table(key, engine)
    df = _deserialize_json_cols(df)
    elapsed = time.monotonic() - start
    logger.debug("Loaded table '%s' from SQLite in %.2fs (%d rows)", key, elapsed, len(df))
    return df

def _get_cached_table(key: str) -> pd.DataFrame:
    """Return the cached DataFrame for *key*, refreshing if stale."""
    now = time.monotonic()
    with _DB_CACHE_LOCK:
        entry = _DB_CACHE.get(key)
        if entry is None or (now - entry["loaded_at"]) > _DB_CACHE_TTL:
            df = _load_table(key)
            _DB_CACHE[key] = {"df": df, "loaded_at": now}
        return _DB_CACHE[key]["df"]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def set_app_data(key: str, value: Any) -> None:
    """Store a small in-memory value (dict, set, scalar).
    Large DataFrames that live in DB_TABLES are intentionally excluded.
    """
    if key not in DB_TABLES:
        APP_DATA[key] = value

def get_app_data(key: str, default: Optional[Any] = None) -> Any:
    """Retrieve a value.  For DB tables, returns the cached DataFrame
    WITHOUT copying — callers that mutate the result must call .copy() themselves.
    """
    if key in DB_TABLES:
        # CSV-only mode: skip derived/intermediate tables entirely
        if not is_sqlite_enabled() and key in CSV_MODE_SKIP_TABLES:
            return default if default is not None else pd.DataFrame()
        try:
            return _get_cached_table(key)
        except Exception:
            return default if default is not None else pd.DataFrame()
    return APP_DATA.get(key, default)

def require_app_data(key: str) -> Any:
    """Like get_app_data but raises RuntimeError if the key is missing."""
    if key in DB_TABLES:
        # CSV-only mode: skip derived/intermediate tables, return empty DataFrame
        if not is_sqlite_enabled() and key in CSV_MODE_SKIP_TABLES:
            logger.debug("require_app_data: '%s' skipped in CSV-only mode, returning empty DataFrame", key)
            return pd.DataFrame()
        try:
            return _get_cached_table(key)
        except Exception as exc:
            raise RuntimeError(f"Database table '{key}' could not be loaded: {exc}") from exc
    if key not in APP_DATA:
        raise RuntimeError(f"Application data '{key}' is not loaded in memory")
    return APP_DATA[key]

def get_all_app_data() -> Dict[str, Any]:
    """Return the small in-memory lookup store (excludes DB tables)."""
    return APP_DATA

def clear_db_cache(key: Optional[str] = None) -> None:
    """Invalidate the DB cache.  Pass key=None to clear everything."""
    with _DB_CACHE_LOCK:
        if key:
            _DB_CACHE.pop(key, None)
        else:
            _DB_CACHE.clear()
    logger.info("DB cache cleared (key=%s)", key or "ALL")

