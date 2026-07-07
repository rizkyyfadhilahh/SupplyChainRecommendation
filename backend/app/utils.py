import glob
import hmac
import logging
import math
import os
from typing import Any, List, Optional
import pandas as pd
from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse
from app.config import TEMP_DIR, API_KEY, APP_DEBUG

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure application logging.

    When ``python-json-logger`` is installed, emit structured JSON logs
    suitable for log aggregation (CloudWatch, Datadog, Elastic).
    Each log record includes ``timestamp``, ``level``, ``logger``,
    ``message``, and any extra fields passed to the logger.

    Falls back to the previous plain-text format if the package is not
    installed, so local development and CI remain unaffected.
    """
    level = logging.DEBUG if APP_DEBUG else logging.INFO

    try:
        from pythonjsonlogger.jsonlogger import JsonFormatter

        handler = logging.StreamHandler()
        handler.setFormatter(
            JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
                rename_fields={
                    "asctime": "timestamp",
                    "levelname": "level",
                    "name": "logger",
                },
            )
        )
        root = logging.getLogger()
        root.setLevel(level)
        # Remove default handlers to avoid duplicate output
        root.handlers.clear()
        root.addHandler(handler)
    except ImportError:
        # python-json-logger not installed — use plain text (dev/CI fallback)
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )


def register_exception_handler(app) -> None:
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        logger.exception("Unhandled internal server error")

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error",
            },
        )


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not API_KEY or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")


def find_first_existing(patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        matches = glob.glob(os.path.join(TEMP_DIR, pattern), recursive=True)
        if matches:
            return matches[0]
    return None


def read_csv_required(path: Optional[str], label: str) -> pd.DataFrame:
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"{label} tidak ditemukan. Path: {path}")
    return pd.read_csv(path, low_memory=False)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        for c in out.columns
    ]
    return out

def to_date_str(value: Any) -> Optional[str]:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.strftime("%Y-%m-%d")


def normalize_facility_type(value: Any) -> str:
    raw = str(value).upper().strip()
    if raw in {"BULKING", "TRADING", "KCP", "VENDOR", "MILL", "ESTATE", "REFINERY"}:
        return raw
    return raw

def normalize_spec_value(value: Any) -> str:
    raw = str(value).upper().strip()
    if raw in {"EUDR", "YES", "Y", "TRUE", "COMPLIANT", "EUDR COMPLIANT"}:
        return "EUDR"
    return raw


def bool_from_any(value: Any) -> bool:
    raw = str(value).strip().lower()
    return raw in {"true", "1", "yes", "y"}


def normalize_trace_product(value: Any) -> str:
    raw = str(value).upper().strip()

    if "RBDPKO" in raw:
        return "RBDPKO"
    if ("CPKO" in raw or "PKO" in raw) and "RBD" not in raw:
        return "PKO"
    if "RBDPO" in raw or "NBDPO" in raw:
        return "RBDPO"
    if "CPO" in raw or "CRUDE PALM OIL" in raw:
        return "CPO"
    if raw == "PK" or raw.startswith("PK "):
        return "PK"
    if "RBDOLN" in raw or "OLEIN" in raw:
        return "RBDOLN"
    if "RBDST" in raw:
        return "RBDST"
    if "RBDPS" in raw:
        return "RBDPS"
    if "PFAD" in raw:
        return "PFAD"
    if raw == "FFB":
        return "FFB"

    return raw


def safe_mean(series: pd.Series, default: float = 0.0) -> float:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().any():
        return float(s.mean())
    return float(default)


def safe_median(series: pd.Series, default: float = 0.0) -> float:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().any():
        return float(s.median())
    return float(default)


def round_days_up(value: float) -> int:
    value = float(value or 0.0)
    if value <= 0:
        return 0
    return int(math.ceil(value))

def is_valid_value(value: Any) -> bool:
    value = str(value).strip()
    return value != "" and value.upper() not in {"NAN", "NONE"}

def normalize_display_key(value: Any) -> str:
    raw = str(value if value is not None else "")
    raw = raw.replace("\u00A0", " ")
    raw = raw.replace("\u200B", "")
    raw = raw.upper().strip()
    return " ".join(raw.split())