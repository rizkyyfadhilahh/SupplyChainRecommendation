import os
from threading import Lock
from typing import Any, Optional

import pandas as pd

from app.config import TEMP_DIR
from app.utils import (
    bool_from_any,
    find_first_existing,
    normalize_columns,
    read_csv_required,
)


CONFIG_FILE_LOCK = Lock()


def is_hidden_sloc(value: Any) -> bool:
    sloc = str(value).strip().upper()
    return (
        sloc.startswith("9999")
        or sloc.startswith("FRA")
        or sloc.startswith("REF")
    )


def get_stock_snapshot() -> Optional[str]:
    trans_path = find_first_existing([
        "**/trans_mb51_ds*.csv",
        "**/trans_mb51*.csv",
    ])
    restan_path = find_first_existing([
        "**/restan_mb51_ds*.csv",
        "**/restan_mb51*.csv",
    ])

    if not trans_path or not restan_path:
        return None

    trans = normalize_columns(read_csv_required(trans_path, "trans_mb51"))
    restan = normalize_columns(read_csv_required(restan_path, "restan_mb51"))

    if "entry_date" in trans.columns:
        trans["entry_date"] = pd.to_datetime(trans["entry_date"], errors="coerce")
    if "input_date" in restan.columns:
        restan["input_date"] = pd.to_datetime(restan["input_date"], errors="coerce")

    if "entry_date" in trans.columns and trans["entry_date"].notna().any():
        return trans["entry_date"].max().strftime("%Y-%m-%d")

    if "input_date" in restan.columns and restan["input_date"].notna().any():
        return restan["input_date"].max().strftime("%Y-%m-%d")

    return None


# ✅ PERFORMANCE: Only load columns we actually use from large CSV files.
_TRANS_USECOLS  = ["id", "entry_date", "qty_restan_event1"]
_RESTAN_USECOLS = ["unique_id", "input_date", "plant", "name1",
                   "storagelocation", "material", "materialdescription"]


def _read_csv_slim(path: str, usecols: list, label: str) -> pd.DataFrame:
    """Read CSV with only the required columns; fall back to full read if
    any column is missing (handles schema variations across environments)."""
    try:
        df = pd.read_csv(path, usecols=usecols, low_memory=True)
        return normalize_columns(df)
    except ValueError:
        # Column subset not available — read all and let downstream handle it
        return normalize_columns(read_csv_required(path, label))


def load_stock_snapshot(events_bc: pd.DataFrame) -> pd.DataFrame:
    trans_path = find_first_existing([
        "**/trans_mb51_ds*.csv",
        "**/trans_mb51*.csv",
    ])
    restan_path = find_first_existing([
        "**/restan_mb51_ds*.csv",
        "**/restan_mb51*.csv",
    ])

    if not trans_path or not restan_path:
        cols = [
            "plant", "name1", "storagelocation", "material",
            "material_type", "materialdescription", "current_stock",
        ]
        return pd.DataFrame(columns=cols)

    # ✅ PERFORMANCE: Load only needed columns (trans_mb51 is 335 MB)
    trans  = _read_csv_slim(trans_path,  _TRANS_USECOLS,  "trans_mb51")
    restan = _read_csv_slim(restan_path, _RESTAN_USECOLS, "restan_mb51")

    # Keep only the two columns we need from events_bc
    events_norm = events_bc[[c for c in ["unique_id", "product_name"]
                              if c in events_bc.columns]].copy()

    if "entry_date" in trans.columns:
        trans["entry_date"] = pd.to_datetime(trans["entry_date"], errors="coerce")
    if "input_date" in restan.columns:
        restan["input_date"] = pd.to_datetime(restan["input_date"], errors="coerce")

    latest_restan = restan.copy()

    if (
        "entry_date" in trans.columns
        and trans["entry_date"].notna().any()
        and "input_date" in restan.columns
    ):
        latest_entry_date = trans["entry_date"].max().normalize()
        latest_restan = restan[restan["input_date"] == latest_entry_date].copy()

        if latest_restan.empty:
            latest_restan = restan[
                restan["input_date"] == restan["input_date"].max()
            ].copy()

    elif "input_date" in restan.columns and restan["input_date"].notna().any():
        latest_restan = restan[
            restan["input_date"] == restan["input_date"].max()
        ].copy()

    merged = latest_restan.merge(
        trans,
        left_on="unique_id",
        right_on="id",
        how="inner",
    )

    merged = merged.merge(
        events_norm[["unique_id", "product_name"]].rename(
            columns={"product_name": "material_type"}
        ),
        left_on="id",
        right_on="unique_id",
        how="left",
        suffixes=("", "_events"),
    )

    required_group_cols = [
        "plant",
        "storagelocation",
        "material",
        "materialdescription",
    ]

    for col in required_group_cols:
        if col not in merged.columns:
            raise ValueError(f"Kolom '{col}' tidak ditemukan setelah join restan + trans")

    if "name1" not in merged.columns:
        merged["name1"] = merged["plant"]

    if "material_type" not in merged.columns:
        merged["material_type"] = None

    merged["storagelocation"] = merged["storagelocation"].astype(str).str.strip()
    merged = merged[
        ~merged["storagelocation"].apply(is_hidden_sloc)
    ].copy()

    snapshot = (
        merged.groupby(
            [
                "plant",
                "name1",
                "storagelocation",
                "material",
                "material_type",
                "materialdescription",
            ],
            dropna=False,
        )["qty_restan_event1"]
        .sum()
        .reset_index()
        .rename(columns={"qty_restan_event1": "current_stock"})
    )

    snapshot["plant"] = snapshot["plant"].astype(str)
    snapshot["name1"] = snapshot["name1"].astype(str)
    snapshot["storagelocation"] = snapshot["storagelocation"].astype(str)
    snapshot["material"] = snapshot["material"].astype(str)
    snapshot["material_type"] = snapshot["material_type"].fillna("").astype(str)
    snapshot["materialdescription"] = snapshot["materialdescription"].astype(str)
    snapshot["current_stock"] = pd.to_numeric(
        snapshot["current_stock"],
        errors="coerce",
    ).fillna(0.0)

    return snapshot


def load_sloc_eudr_config() -> pd.DataFrame:
    config_path = os.path.join(TEMP_DIR, "sloc_eudr_config.csv")

    if not os.path.exists(config_path):
        return pd.DataFrame(
            columns=[
                "plant",
                "storagelocation",
                "material",
                "eudr",
                "eudr_valid_from",
                "eudr_valid_to",
            ]
        )

    cfg = pd.read_csv(config_path, low_memory=False)
    cfg = normalize_columns(cfg)

    for col in ["plant", "storagelocation", "material"]:
        if col in cfg.columns:
            cfg[col] = cfg[col].astype(str)

    if "eudr" in cfg.columns:
        cfg["eudr"] = cfg["eudr"].apply(bool_from_any)

    if "eudr_valid_from" in cfg.columns:
        cfg["eudr_valid_from"] = pd.to_datetime(
            cfg["eudr_valid_from"],
            errors="coerce",
        )

    if "eudr_valid_to" in cfg.columns:
        cfg["eudr_valid_to"] = pd.to_datetime(
            cfg["eudr_valid_to"],
            errors="coerce",
        )

    return cfg


def save_sloc_eudr_config(cfg: pd.DataFrame) -> None:
    config_path = os.path.join(TEMP_DIR, "sloc_eudr_config.csv")
    out = cfg.copy()

    for col in ["eudr_valid_from", "eudr_valid_to"]:
        if col in out.columns:
            out[col] = pd.to_datetime(
                out[col],
                errors="coerce",
            ).dt.strftime("%Y-%m-%d")

    tmp_path = config_path + ".tmp"

    with CONFIG_FILE_LOCK:
        out.to_csv(tmp_path, index=False)
        os.replace(tmp_path, config_path)