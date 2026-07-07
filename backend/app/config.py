import logging
import os
import json
from threading import RLock
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env for local development. In production, this can be omitted 
# or overriden by system-level environment variables from CI/CD.
load_dotenv()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(APP_DIR)
TEMP_DIR = os.path.join(BASE_DIR, "temp_data")

# ---------------------------------------------------------------------------
# Data source configuration
# Override these env vars to point at a different directory or filenames.
# DATA_DIR defaults to TEMP_DIR so existing deployments require no changes.
# File paths that include subdirectories (e.g. "3 months/events_bc.csv")
# are resolved relative to DATA_DIR — subdirectory separators are allowed.
# ---------------------------------------------------------------------------
DATA_DIR = os.getenv("DATA_DIR", TEMP_DIR)

# Supply chain event / linkage files
EVENTS_BC_FILENAME        = os.getenv("EVENTS_BC_FILENAME",        "3 months/events_bc_01_Des_24_Feb.csv")
LINKS_BC_FILENAME         = os.getenv("LINKS_BC_FILENAME",         "3 months/links_bc_01_Des_24_Feb.csv")

# Master facility reference
MASTER_FACILITY_FILENAME  = os.getenv("MASTER_FACILITY_FILENAME",  "master_facility.csv")

# Stock snapshot files (MB51 exports)
TRANS_MB51_FILENAME       = os.getenv("TRANS_MB51_FILENAME",       "trans_mb51.csv")
RESTAN_MB51_FILENAME      = os.getenv("RESTAN_MB51_FILENAME",      "restan_mb51.csv")

# SLOC EUDR config
SLOC_EUDR_CONFIG_FILENAME = os.getenv("SLOC_EUDR_CONFIG_FILENAME", "sloc_eudr_config.csv")


def get_data_file_path(filename: str) -> str:
    """Resolve a filename to an absolute path under DATA_DIR.

    Subdirectory separators are allowed so filenames like
    ``'3 months/events_bc.csv'`` resolve correctly.

    Raises EnvironmentError if the resolved path escapes DATA_DIR
    (path traversal guard) or if the file does not exist.
    """
    resolved = os.path.normpath(os.path.join(DATA_DIR, filename))
    # Guard against path traversal (e.g. filename = "../../etc/passwd")
    if not resolved.startswith(os.path.normpath(DATA_DIR)):
        raise EnvironmentError(
            f"Data file path {filename!r} escapes DATA_DIR — "
            "possible path traversal attempt."
        )
    if not os.path.isfile(resolved):
        raise EnvironmentError(
            f"Data file not found: {resolved!r}\n"
            f"  Set the env var that controls this file, or place the "
            f"file in DATA_DIR={DATA_DIR!r}."
        )
    return resolved


def validate_data_files() -> None:
    """Assert all required data files are present.

    Call once at startup (before loading data) to surface missing-file
    errors with a clear operator message instead of a silent AttributeError
    deep inside the pipeline.
    """
    required = {
        "EVENTS_BC_FILENAME":       EVENTS_BC_FILENAME,
        "LINKS_BC_FILENAME":        LINKS_BC_FILENAME,
        "MASTER_FACILITY_FILENAME": MASTER_FACILITY_FILENAME,
        "TRANS_MB51_FILENAME":      TRANS_MB51_FILENAME,
        "RESTAN_MB51_FILENAME":     RESTAN_MB51_FILENAME,
    }
    missing = []
    for env_var, filename in required.items():
        path = os.path.normpath(os.path.join(DATA_DIR, filename))
        if not os.path.isfile(path):
            missing.append(
                f"  {env_var}={filename!r}  →  expected at: {path}"
            )
    if missing:
        raise EnvironmentError(
            f"Required data files not found. "
            f"Set the correct env vars or place the files in "
            f"DATA_DIR={DATA_DIR!r}:\n" + "\n".join(missing)
        )

APP_DEBUG = False

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

API_KEY = os.getenv("API_KEY")

CACHE_TTL_SECONDS = 300

VENDOR_TYPE = "VENDOR"
ALLOW_TERMINAL_VENDOR = True
ALLOW_TERMINAL_MILL = True
ALLOW_CPO_TOLLING = True
PRIORITIZE_VENDOR_DEBUG = False

# These values are defaults — they are overridden at runtime by
# reload_domain_config() which reads FORECAST_THRESHOLDS from SQLite
# (or domain_config.json in CSV-only mode).  Do NOT read these constants
# directly in hot-path code; use the get_forecast_threshold() accessor
# so live config changes take effect without a restart.
MIN_TXN_FOR_EXACT = 3
MIN_ACTIVE_DAYS_FOR_EXACT = 3
FORECAST_TARGET_DAYS = 15
MIN_ALLOCATED_SHARE_PER_SUPPLIER = 0.005

FORECAST_THRESHOLDS: dict = {}
ENABLE_QUEUE_SCHEDULING = True

def get_dynamic_min_allocated_share(demand_qty: float) -> float:
    demand_qty = float(demand_qty or 0.0)
    if demand_qty <= 1_000_000:
        return 0.05
    if demand_qty <= 3_000_000:
        return 0.03
    if demand_qty <= 5_000_000:
        return 0.02
    return 0.02

# ---------------------------------------------------------------------------
# Config lock — protects all mutable config globals below.
# Use _CONFIG_LOCK as a write lock inside reload_domain_config().
# Use the get_*() accessors (defined after reload_domain_config) for reads
# in hot-path code so that a concurrent reload never exposes a half-cleared
# collection to a reader.
# ---------------------------------------------------------------------------
_CONFIG_LOCK = RLock()

# Initialize empty objects that will be populated by reload_domain_config()
process_map = {}
conversion_map = {}
REFINED_PRODUCTS = []
DIRECT_REFINERY_PRODUCTS = set()
DIRECT_PRODUCT_EMPTY_FALLBACK = {}
VENDOR_PARTNER_PCA_PRODUCTS = set()
REFINERIES_WITH_KCP = set()
PASS_THROUGH_TYPES = set()
DEFAULT_LEAD_DAYS_BY_TYPE = {}
DEFAULT_THROUGHPUT_TPD_BY_PRODUCT = {}
facility_groups = {}
buyer_blacklist = {}

def get_forecast_threshold(key: str, default=None):
    """Return a forecast threshold value from the live in-memory config.
    Falls back to the module-level constant if the key is not present.
    This allows hot-reloading of thresholds without a server restart.

    Supported keys:
      MIN_TXN_FOR_EXACT, MIN_ACTIVE_DAYS_FOR_EXACT,
      FORECAST_TARGET_DAYS, MIN_ALLOCATED_SHARE_PER_SUPPLIER
    """
    if FORECAST_THRESHOLDS:
        return FORECAST_THRESHOLDS.get(key, default)
    # Fall back to module-level constants
    _fallbacks = {
        "MIN_TXN_FOR_EXACT": MIN_TXN_FOR_EXACT,
        "MIN_ACTIVE_DAYS_FOR_EXACT": MIN_ACTIVE_DAYS_FOR_EXACT,
        "FORECAST_TARGET_DAYS": FORECAST_TARGET_DAYS,
        "MIN_ALLOCATED_SHARE_PER_SUPPLIER": MIN_ALLOCATED_SHARE_PER_SUPPLIER,
    }
    return _fallbacks.get(key, default)


def reload_domain_config():
    """Reads domain config from SQLite tables (or JSON if CSV-only mode) and
    updates the in-memory dictionaries atomically under _CONFIG_LOCK.

    The lock ensures that readers using the get_*() accessors never see a
    partially-cleared collection during a reload.
    """
    from sqlalchemy import inspect
    from app.database import engine
    import pandas as pd
    import os
    
    # CSV-only mode: load directly from domain_config.json
    use_sqlite = os.getenv("USE_SQLITE", "true").lower() == "true"
    if not use_sqlite:
        config_path = os.path.join(APP_DIR, "domain_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Build all new values BEFORE acquiring the lock so readers are
            # blocked for the shortest possible time.
            new_conversion_map   = data.get("conversion_map", {})
            new_process_map      = data.get("process_map", {})
            new_facility_groups  = dict(data.get("facility_groups", {}))
            new_buyer_blacklist  = dict(data.get("buyer_blacklist", {}))
            new_refined          = list(data.get("REFINED_PRODUCTS", []))
            new_direct_ref       = set(data.get("DIRECT_REFINERY_PRODUCTS", []))
            new_direct_fallback  = dict(data.get("DIRECT_PRODUCT_EMPTY_FALLBACK", {}))
            new_vendor_pca       = set(data.get("VENDOR_PARTNER_PCA_PRODUCTS", []))
            new_kcp              = set(data.get("REFINERIES_WITH_KCP", []))
            new_pass_through     = set(data.get("PASS_THROUGH_TYPES", []))
            new_lead_days        = dict(data.get("DEFAULT_LEAD_DAYS_BY_TYPE", {}))
            new_throughput       = dict(data.get("DEFAULT_THROUGHPUT_TPD_BY_PRODUCT", {}))
            new_thresholds       = dict(data.get("FORECAST_THRESHOLDS", {}))

            with _CONFIG_LOCK:
                conversion_map.clear()
                conversion_map.update(new_conversion_map)

                process_map.clear()
                process_map.update(new_process_map)

                facility_groups.clear()
                facility_groups.update(new_facility_groups)

                buyer_blacklist.clear()
                buyer_blacklist.update(new_buyer_blacklist)

                REFINED_PRODUCTS.clear()
                REFINED_PRODUCTS.extend(new_refined)

                DIRECT_REFINERY_PRODUCTS.clear()
                DIRECT_REFINERY_PRODUCTS.update(new_direct_ref)

                DIRECT_PRODUCT_EMPTY_FALLBACK.clear()
                DIRECT_PRODUCT_EMPTY_FALLBACK.update(new_direct_fallback)

                VENDOR_PARTNER_PCA_PRODUCTS.clear()
                VENDOR_PARTNER_PCA_PRODUCTS.update(new_vendor_pca)

                REFINERIES_WITH_KCP.clear()
                REFINERIES_WITH_KCP.update(new_kcp)

                PASS_THROUGH_TYPES.clear()
                PASS_THROUGH_TYPES.update(new_pass_through)

                DEFAULT_LEAD_DAYS_BY_TYPE.clear()
                DEFAULT_LEAD_DAYS_BY_TYPE.update(new_lead_days)

                DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.clear()
                DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.update(new_throughput)

                FORECAST_THRESHOLDS.clear()
                FORECAST_THRESHOLDS.update(new_thresholds)

            logger.info("Domain config loaded from JSON (CSV-only mode)")
        return
    
    # SQLite mode: load from database tables
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Read all data from SQLite BEFORE acquiring the lock.
        new_conversion_map  = {}
        new_process_map     = {}
        new_facility_groups = {}
        new_buyer_blacklist = {}
        new_general: dict   = {}

        if "conversion_map" in tables:
            df = pd.read_sql_table("conversion_map", engine)
            new_conversion_map = dict(zip(df["product"], df["ratio"]))

        if "process_map" in tables:
            df = pd.read_sql_table("process_map", engine)
            new_process_map = dict(zip(df["product"], df["raw_material"]))

        if "facility_groups" in tables:
            df = pd.read_sql_table("facility_groups", engine)
            for ref, group in df.groupby("refinery_name"):
                new_facility_groups[ref] = group["plant_id"].tolist()

        if "buyer_blacklist" in tables:
            df = pd.read_sql_table("buyer_blacklist", engine)
            for buyer, group in df.groupby("buyer_name"):
                new_buyer_blacklist[buyer] = group["blacklisted_plant_id"].tolist()

        if "general_config" in tables:
            df = pd.read_sql_table("general_config", engine)
            for _, row in df.iterrows():
                new_general[row["config_key"]] = json.loads(row["config_value"])

        # Now acquire the lock and swap atomically.
        with _CONFIG_LOCK:
            conversion_map.clear()
            conversion_map.update(new_conversion_map)

            process_map.clear()
            process_map.update(new_process_map)

            facility_groups.clear()
            facility_groups.update(new_facility_groups)

            buyer_blacklist.clear()
            buyer_blacklist.update(new_buyer_blacklist)

            for k, v in new_general.items():
                if k == "REFINED_PRODUCTS":
                    REFINED_PRODUCTS.clear()
                    REFINED_PRODUCTS.extend(v)
                elif k == "DIRECT_REFINERY_PRODUCTS":
                    DIRECT_REFINERY_PRODUCTS.clear()
                    DIRECT_REFINERY_PRODUCTS.update(v)
                elif k == "DIRECT_PRODUCT_EMPTY_FALLBACK":
                    DIRECT_PRODUCT_EMPTY_FALLBACK.clear()
                    DIRECT_PRODUCT_EMPTY_FALLBACK.update(v)
                elif k == "VENDOR_PARTNER_PCA_PRODUCTS":
                    VENDOR_PARTNER_PCA_PRODUCTS.clear()
                    VENDOR_PARTNER_PCA_PRODUCTS.update(v)
                elif k == "REFINERIES_WITH_KCP":
                    REFINERIES_WITH_KCP.clear()
                    REFINERIES_WITH_KCP.update(v)
                elif k == "PASS_THROUGH_TYPES":
                    PASS_THROUGH_TYPES.clear()
                    PASS_THROUGH_TYPES.update(v)
                elif k == "DEFAULT_LEAD_DAYS_BY_TYPE":
                    DEFAULT_LEAD_DAYS_BY_TYPE.clear()
                    DEFAULT_LEAD_DAYS_BY_TYPE.update(v)
                elif k == "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT":
                    DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.clear()
                    DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.update(v)
                elif k == "FORECAST_THRESHOLDS":
                    FORECAST_THRESHOLDS.clear()
                    FORECAST_THRESHOLDS.update(v)
                    
    except Exception as e:
        logger.warning("Could not load domain config from SQLite: %s", e)

# ---------------------------------------------------------------------------
# Thread-safe read accessors for hot-path code.
# Import and call these instead of reading the module globals directly.
# Each accessor acquires _CONFIG_LOCK for the duration of the read, which
# is safe because RLock allows re-entrant acquisition from the same thread.
# ---------------------------------------------------------------------------

def get_process_map() -> dict:
    """Return a shallow copy of process_map under the config lock."""
    with _CONFIG_LOCK:
        return dict(process_map)


def get_conversion_map() -> dict:
    """Return a shallow copy of conversion_map under the config lock."""
    with _CONFIG_LOCK:
        return dict(conversion_map)


def get_facility_groups() -> dict:
    """Return a shallow copy of facility_groups under the config lock."""
    with _CONFIG_LOCK:
        return dict(facility_groups)


def get_buyer_blacklist() -> dict:
    """Return a shallow copy of buyer_blacklist under the config lock."""
    with _CONFIG_LOCK:
        return dict(buyer_blacklist)


def get_refined_products() -> list:
    """Return a copy of REFINED_PRODUCTS under the config lock."""
    with _CONFIG_LOCK:
        return list(REFINED_PRODUCTS)


def get_direct_refinery_products() -> set:
    """Return a copy of DIRECT_REFINERY_PRODUCTS under the config lock."""
    with _CONFIG_LOCK:
        return set(DIRECT_REFINERY_PRODUCTS)


def get_direct_product_empty_fallback() -> dict:
    """Return a shallow copy of DIRECT_PRODUCT_EMPTY_FALLBACK under the config lock."""
    with _CONFIG_LOCK:
        return dict(DIRECT_PRODUCT_EMPTY_FALLBACK)


def get_pass_through_types() -> set:
    """Return a copy of PASS_THROUGH_TYPES under the config lock."""
    with _CONFIG_LOCK:
        return set(PASS_THROUGH_TYPES)


def get_refineries_with_kcp() -> set:
    """Return a copy of REFINERIES_WITH_KCP under the config lock."""
    with _CONFIG_LOCK:
        return set(REFINERIES_WITH_KCP)


# Load the config immediately upon module import (will be empty until seeded)
reload_domain_config()