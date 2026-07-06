from typing import Any, Dict, Optional

import pandas as pd
import numpy as np
import contextvars

from app.config import (
    DEFAULT_LEAD_DAYS_BY_TYPE,
    DEFAULT_THROUGHPUT_TPD_BY_PRODUCT,
    FORECAST_TARGET_DAYS,
    MIN_ACTIVE_DAYS_FOR_EXACT,
    MIN_TXN_FOR_EXACT,
    facility_groups,
)
from app.state import get_app_data, require_app_data
from app.pipeline.utils import get_facility_type_for_trace, get_facility_type_safe
from app.utils import (
    normalize_facility_type,
    normalize_trace_product,
    safe_mean,
    safe_median,
    round_days_up,
)

EDGE_LEADTIME_MASTER = None
ESTATE_EDGE_LEADTIME_MASTER = None

_EDGE_IDX: dict = {}           
_EDGE_IDX_SUP_FAC: dict = {}  
_EDGE_IDX_SUP: dict = {}      
_EDGE_IDX_TYPE_FAC_PROD: dict = {}  
_EDGE_IDX_PROD: dict = {}      

_ESTATE_IDX: dict = {}        
_ESTATE_IDX_SUP: dict = {}     

_edge_days_cache_var: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "edge_days_cache", default=None
)

def _get_edge_days_cache() -> dict:
    cache = _edge_days_cache_var.get()
    if cache is None:
        cache = {}
        _edge_days_cache_var.set(cache)
    return cache

def _build_edge_indexes(df: "pd.DataFrame") -> None:
    global _EDGE_IDX, _EDGE_IDX_SUP_FAC, _EDGE_IDX_SUP, _EDGE_IDX_TYPE_FAC_PROD, _EDGE_IDX_PROD
    _EDGE_IDX = {}
    _EDGE_IDX_SUP_FAC = {}
    _EDGE_IDX_SUP = {}
    _EDGE_IDX_TYPE_FAC_PROD = {}
    _EDGE_IDX_PROD = {}

    for row in df.to_dict(orient="records"):
        sup = str(row.get("supplier", "")).strip()
        fac = str(row.get("facility", "")).strip()
        prod = str(row.get("product", "")).upper().strip()
        stype = str(row.get("supplier_type", "")).upper().strip()

        _EDGE_IDX.setdefault((sup, fac, prod), []).append(row)
        _EDGE_IDX_SUP_FAC.setdefault((sup, fac), []).append(row)
        _EDGE_IDX_SUP.setdefault(sup, []).append(row)
        _EDGE_IDX_TYPE_FAC_PROD.setdefault((stype, fac, prod), []).append(row)
        _EDGE_IDX_TYPE_FAC_PROD.setdefault((stype, fac, ""), []).append(row)  # type+fac only
        _EDGE_IDX_PROD.setdefault(prod, []).append(row)


def _build_estate_indexes(df: "pd.DataFrame") -> None:
    """Build O(1) lookup dicts from ESTATE_EDGE_LEADTIME_MASTER DataFrame."""
    global _ESTATE_IDX, _ESTATE_IDX_SUP
    _ESTATE_IDX = {}
    _ESTATE_IDX_SUP = {}

    for row in df.to_dict(orient="records"):
        sup = str(row.get("supplier", "")).strip()
        fac = str(row.get("facility", "")).strip()
        _ESTATE_IDX.setdefault((sup, fac), []).append(row)
        _ESTATE_IDX_SUP.setdefault(sup, []).append(row)

def get_target_days_for_edge(receiver_id: str) -> int:
    return int(FORECAST_TARGET_DAYS)

def apply_estimated_day_rules(raw_days: float, receiver_id: str) -> int:
    return round_days_up(float(raw_days or 0.0))

def build_edge_leadtime_master() -> pd.DataFrame:
    _EMPTY = pd.DataFrame(columns=[
        "supplier", "facility", "product",
        "txn_count", "total_qty", "active_days",
        "median_duration_days", "avg_duration_days", "throughput_tpd",
        "median_daily_qty", "avg_daily_qty",
        "supplier_type", "facility_type",
    ])

    relations_all = require_app_data("relations_all")
    facility_lookup = require_app_data("facility_lookup")

    needed_cols = [
        "vendor_receiver",
        "plant_supplier",
        "plant_receiver",
        "product_name_supplier",
        "qty",
        "insert_date_supplier",
        "insert_date_receiver",
    ]

    # Guard: empty DataFrame (CSV-only mode) or missing columns → return early.
    # This prevents KeyError when relations_all has no columns.
    if relations_all.empty or not all(c in relations_all.columns for c in needed_cols):
        return _EMPTY

    rel = relations_all[needed_cols].copy()
    if rel.empty:
        return pd.DataFrame(columns=[
            "supplier", "facility", "product",
            "txn_count", "total_qty", "active_days",
            "median_duration_days", "avg_duration_days", "throughput_tpd",
            "median_daily_qty", "avg_daily_qty",
            "supplier_type", "facility_type",
        ])

    rel["vendor_receiver"] = (
        pd.to_numeric(rel["vendor_receiver"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", "")
        .str.strip()
    )

    rel["plant_supplier"] = rel["plant_supplier"].fillna("").astype(str).str.strip()
    rel["plant_receiver"] = rel["plant_receiver"].fillna("").astype(str).str.strip()
    rel["product"] = rel["product_name_supplier"].apply(normalize_trace_product)
    rel["qty"] = pd.to_numeric(rel["qty"], errors="coerce").fillna(0.0)
    rel["duration_days"] = (
        (rel["insert_date_receiver"] - rel["insert_date_supplier"]).dt.total_seconds() / 86400.0
    )
    rel["active_day"] = pd.to_datetime(rel["insert_date_supplier"], errors="coerce").dt.normalize()

    rel_physical = rel.copy()
    rel_physical["supplier"] = rel_physical["plant_supplier"].astype(str)
    rel_physical["facility"] = rel_physical["plant_receiver"].astype(str)

    rel_vendor = rel[rel["vendor_receiver"] != ""].copy()
    rel_vendor["supplier"] = rel_vendor["vendor_receiver"].astype(str)
    rel_vendor["facility"] = rel_vendor["plant_receiver"].astype(str)

    rel = pd.concat([rel_physical, rel_vendor], ignore_index=True)

    rel = rel[
        rel["supplier"].notna() & rel["facility"].notna() &
        rel["product"].notna() & (rel["qty"] > 0) &
        rel["duration_days"].notna() & (rel["duration_days"] >= 0) &
        rel["active_day"].notna()
    ].copy()

    if rel.empty:
        return pd.DataFrame(columns=[
            "supplier", "facility", "product",
            "txn_count", "total_qty", "active_days",
            "median_duration_days", "avg_duration_days", "throughput_tpd",
            "median_daily_qty", "avg_daily_qty",
            "supplier_type", "facility_type",
        ])

    daily = (
        rel.groupby(["supplier", "facility", "product", "active_day"], as_index = False)["qty"]
        .sum()
        .rename(columns={"qty": "daily_qty"})
    )

    daily_summary = (
        daily.groupby(["supplier", "facility", "product"], as_index=False)
        .agg(
            active_days=("active_day", "nunique"),
            median_daily_qty=("daily_qty", "median"),
            avg_daily_qty=("daily_qty", "mean"),
        )
    )

    txn_summary = (
        rel.groupby(["supplier", "facility", "product"], as_index=False)
        .agg(
            txn_count=("qty", "count"),
            total_qty=("qty", "sum"),
            median_duration_days=("duration_days", "median"),
            avg_duration_days=("duration_days", "mean"),
        )
    )

    grouped = txn_summary.merge(
        daily_summary,
        on=["supplier", "facility", "product"],
        how="left",
    )

    grouped["throughput_tpd"] = pd.to_numeric(grouped["median_daily_qty"], errors="coerce").fillna(0.0)

    grouped = grouped.merge(
        facility_lookup.rename(columns={
            "facility_id": "supplier",
            "facility_name": "supplier_name",
            "facility_type": "supplier_type",
            "specification": "supplier_spec",
        }),
        on="supplier",
        how="left",
    )

    grouped = grouped.merge(
        facility_lookup.rename(columns={
            "facility_id": "facility",
            "facility_name": "facility_name",
            "facility_type": "facility_type",
            "specification": "facility_spec",
        }),
        on="facility",
        how="left",
    )

    grouped["supplier_type"] = grouped["supplier_type"].fillna("").astype(str).apply(normalize_facility_type)
    grouped["facility_type"] = grouped["facility_type"].fillna("").astype(str).apply(normalize_facility_type)

    grouped["supplier"] = grouped["supplier"].astype(str).str.strip()
    grouped["facility"] = grouped["facility"].astype(str).str.strip()
    grouped["product"] = grouped["product"].astype(str).str.upper().str.strip()
    grouped["supplier_type"] = grouped["supplier_type"].astype(str).str.upper().str.strip()

    return grouped


def build_estate_edge_leadtime_master() -> pd.DataFrame:
    _EMPTY = pd.DataFrame(columns=[
        "supplier", "facility", "product",
        "txn_count", "total_qty", "active_days",
        "median_duration_days", "avg_duration_days", "throughput_tpd",
        "median_daily_qty", "avg_daily_qty",
        "supplier_type", "facility_type",
    ])

    ffb_relations = require_app_data("ffb_relations")
    rel = ffb_relations.copy()

    # Guard: empty DataFrame (CSV-only mode) or missing 'mill' column → return early.
    if rel.empty or "mill" not in rel.columns:
        return _EMPTY

    rel["facility"] = rel["mill"].astype(str)
    rel["product"] = "FFB"

    rel["quantity"] = pd.to_numeric(rel["quantity"], errors="coerce").fillna(0.0)

    rel["insert_date_supplier"] = pd.to_datetime(
    rel["insert_date_supplier"],
    errors="coerce"
    )

    rel["insert_date_receiver"] = pd.to_datetime(
        rel["insert_date_receiver"],
        errors="coerce"
    )

    rel["active_day"] = (
        rel["insert_date_supplier"]
        .fillna(rel["insert_date_receiver"])
        .dt.normalize()
    )

    rel["duration_days"] = (
        (rel["insert_date_receiver"] - rel["insert_date_supplier"])
        .dt.total_seconds() / 86400.0
    )

    rel["duration_days"] = rel["duration_days"].fillna(
        DEFAULT_LEAD_DAYS_BY_TYPE["ESTATE_TO_MILL"]
    )

    rel["supplier"] = rel["supplier"].fillna("").astype(str).str.strip()
    rel["facility"] = rel["facility"].fillna("").astype(str).str.strip()

    rel = rel[
        (rel["supplier"] != "") &
        (rel["facility"] != "") &
        (rel["quantity"] > 0) &
        rel["active_day"].notna()
    ].copy()

    rel["duration_days"] = pd.to_numeric(
        rel["duration_days"],
        errors="coerce"
    ).fillna(DEFAULT_LEAD_DAYS_BY_TYPE["ESTATE_TO_MILL"])

    rel["duration_days"] = rel["duration_days"].clip(lower=0)

    if rel.empty:
        return pd.DataFrame(columns=[
            "supplier", "facility", "product",
            "txn_count", "total_qty", "active_days",
            "median_duration_days", "avg_duration_days", "throughput_tpd",
            "median_daily_qty", "avg_daily_qty",
            "supplier_type", "facility_type",
        ])

    daily = (
        rel.groupby(["supplier", "facility", "product", "active_day"], as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "daily_qty"})
    )

    daily_summary = (
    daily.groupby(["supplier", "facility", "product"], as_index=False)
    .agg(
        active_days=("active_day", "nunique"),
        median_daily_qty=("daily_qty", "median"),
        p50_daily_qty=("daily_qty", "median"),
        p75_daily_qty=("daily_qty", lambda x: float(x.quantile(0.75))),
        p90_daily_qty=("daily_qty", lambda x: float(x.quantile(0.90))),
        max_daily_qty=("daily_qty", "max"),
        avg_daily_qty=("daily_qty", "mean"),
        )
    )

    txn_summary = (
        rel.groupby(["supplier", "facility", "product"], as_index=False)
        .agg(
            txn_count=("quantity", "count"),
            total_qty=("quantity", "sum"),
            median_duration_days=("duration_days", "median"),
            avg_duration_days=("duration_days", "mean"),
        )
    )

    grouped = txn_summary.merge(
        daily_summary,
        on=["supplier", "facility", "product"],
        how="left",
    )

    grouped["throughput_tpd"] = pd.to_numeric(grouped["median_daily_qty"], errors="coerce").fillna(0.0)

    grouped = grouped.merge(
        rel[["supplier", "supplier_source_kind"]].drop_duplicates("supplier"),
        on="supplier",
        how="left",
    )

    grouped["supplier_type"] = grouped["supplier"].map(
        lambda x: get_facility_type_safe(str(x))
    )

    grouped["supplier_type"] = np.where(
        grouped["supplier_type"].fillna("").astype(str).str.strip() != "",
        grouped["supplier_type"],
        grouped["supplier_source_kind"].fillna("UNKNOWN").astype(str)
    )

    grouped["supplier_type"] = grouped["supplier_type"].fillna("UNKNOWN").astype(str).apply(normalize_facility_type)

    grouped["facility_type"] = grouped["facility"].map(
        lambda x: get_facility_type_safe(str(x)) or "MILL"
    )

    grouped["supplier"] = grouped["supplier"].astype(str).str.strip()
    grouped["facility"] = grouped["facility"].astype(str).str.strip()
    grouped["product"] = grouped["product"].astype(str).str.upper().str.strip()
    grouped["supplier_type"] = grouped["supplier_type"].astype(str).str.upper().str.strip()
    return grouped

def get_edge_leadtime_master() -> pd.DataFrame:
    global EDGE_LEADTIME_MASTER

    if EDGE_LEADTIME_MASTER is None:
        EDGE_LEADTIME_MASTER = build_edge_leadtime_master()
        _build_edge_indexes(EDGE_LEADTIME_MASTER)

    return EDGE_LEADTIME_MASTER


def get_estate_edge_leadtime_master() -> pd.DataFrame:
    global ESTATE_EDGE_LEADTIME_MASTER

    if ESTATE_EDGE_LEADTIME_MASTER is None:
        ESTATE_EDGE_LEADTIME_MASTER = build_estate_edge_leadtime_master()
        _build_estate_indexes(ESTATE_EDGE_LEADTIME_MASTER)

    return ESTATE_EDGE_LEADTIME_MASTER


def reset_forecast_cache() -> None:
    global EDGE_LEADTIME_MASTER, ESTATE_EDGE_LEADTIME_MASTER
    EDGE_LEADTIME_MASTER = None
    ESTATE_EDGE_LEADTIME_MASTER = None
    _build_edge_indexes(pd.DataFrame())
    _build_estate_indexes(pd.DataFrame())

def get_global_product_throughput(product: str) -> float:
    edge_leadtime_master = get_edge_leadtime_master()
    product = str(product).upper()
    df = edge_leadtime_master[
        edge_leadtime_master["product"].astype(str).str.upper() == product
    ]

    if not df.empty:
        v = safe_median(df["median_daily_qty"], default=0.0)
        if v > 0:
            return v

    return float(DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.get(product, 100.0))


def get_global_product_lead(product: str) -> float:
    edge_leadtime_master = get_edge_leadtime_master()

    product = str(product).upper()
    df = edge_leadtime_master[
        edge_leadtime_master["product"].astype(str).str.upper() == product
    ]

    if not df.empty:
        v = safe_median(df["median_duration_days"], default=0.0)
        if v > 0:
            return v

    return 1.0


def get_estate_global_throughput() -> float:
    estate_edge_leadtime_master = get_estate_edge_leadtime_master()

    if not estate_edge_leadtime_master.empty:
        v = safe_median(estate_edge_leadtime_master["median_daily_qty"], default=0.0)
        if v > 0:
            return v
    return float(DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.get("FFB", 150.0))


def get_estate_global_lead() -> float:
    estate_edge_leadtime_master = get_estate_edge_leadtime_master()

    if not estate_edge_leadtime_master.empty:
        v = safe_median(estate_edge_leadtime_master["median_duration_days"], default=0.0)
        if v > 0:
            return v
    return float(DEFAULT_LEAD_DAYS_BY_TYPE["ESTATE_TO_MILL"])

def get_queue_throughput_for_facility_product(
    supplier_id: str,
    product: str,
    fallback_tpd: float = 0.0,
) -> float:
    # Ensure indexes are built
    get_edge_leadtime_master()
    get_estate_edge_leadtime_master()

    supplier_id = str(supplier_id).strip()
    product = str(product).upper().strip()
    fallback_tpd = float(fallback_tpd or 0.0)

    if product == "FFB":
        rows = _ESTATE_IDX_SUP.get(supplier_id, [])
        if rows:
            vals = [float(r.get("median_daily_qty", 0) or 0) for r in rows]
            vals = [v for v in vals if v > 0]
            if vals:
                return float(max(vals))

        if fallback_tpd > 0:
            return fallback_tpd
        return float(get_estate_global_throughput())

    rows = _EDGE_IDX_SUP.get(supplier_id, [])
    rows = [r for r in rows if r.get("product", "") == product]
    if rows:
        vals = [float(r.get("median_daily_qty", 0) or 0) for r in rows]
        vals = [v for v in vals if v > 0]
        if vals:
            return float(max(vals))

    if fallback_tpd > 0:
        return fallback_tpd
    return float(get_global_product_throughput(product))

def aggregate_forecast(
    df: pd.DataFrame,
    supplier_id: str,
    facility_id: str,
    product: str,
) -> Optional[pd.Series]:
    if df.empty:
        return None

    return pd.Series({
        "median_duration_days": safe_median(df["median_duration_days"], default=0.0),
        "avg_duration_days": safe_mean(df["avg_duration_days"], default=0.0),
        "throughput_tpd": safe_median(df["median_daily_qty"], default=0.0),
        "median_daily_qty": safe_median(df["median_daily_qty"], default=0.0),
        "avg_daily_qty": safe_mean(df["avg_daily_qty"], default=0.0),
        "txn_count": int(pd.to_numeric(df["txn_count"], errors="coerce").fillna(0).sum()),
        "active_days": int(pd.to_numeric(df["active_days"], errors="coerce").fillna(0).sum()),
        "total_qty": float(pd.to_numeric(df["total_qty"], errors="coerce").fillna(0).sum()),
        "product": product,
        "supplier": supplier_id,
        "facility": facility_id,
    })


def row_meets_exact_threshold(row: pd.Series) -> bool:
    txn_count = int(row.get("txn_count", 0) or 0)
    active_days = int(row.get("active_days", 0) or 0)
    return txn_count >= MIN_TXN_FOR_EXACT and active_days >= MIN_ACTIVE_DAYS_FOR_EXACT

def get_estate_edge_forecast_row(
    supplier_id: str,
    facility_id: str,
    product: str,
) -> Optional[pd.Series]:
    # Ensure indexes are built
    get_estate_edge_leadtime_master()

    supplier_id = str(supplier_id).strip()
    facility_id = str(facility_id).strip()
    product = str(product).upper().strip()

    if product != "FFB":
        return None

    rows = _ESTATE_IDX.get((supplier_id, facility_id), [])
    if not rows:
        return None

    df = pd.DataFrame(rows)
    row = aggregate_forecast(df, supplier_id, facility_id, product)

    if row is not None:
        if row_meets_exact_threshold(row):
            row["forecast_match_level"] = "ESTATE_EXACT"
        else:
            row["forecast_match_level"] = "ESTATE_EXACT_LOW_CONFIDENCE"
        return row

    return None

def get_edge_forecast_row(
    supplier_id: str,
    facility_id: str,
    product: str,
) -> Optional[pd.Series]:
    # Ensure indexes are built
    get_edge_leadtime_master()

    supplier_id = str(supplier_id).strip()
    facility_id = str(facility_id).strip()
    product = str(product).upper().strip()

    supplier_type = get_facility_type_safe(supplier_id)

    if facility_id in facility_groups:
        refinery_plants = [str(x) for x in facility_groups[facility_id]]
        refinery_set = set(refinery_plants)

        # Level 1: exact supplier + refinery plant(s) + product
        rows = [r for r in _EDGE_IDX_SUP.get(supplier_id, [])
                if r.get("facility", "") in refinery_set and r.get("product", "") == product]
        if rows:
            row = aggregate_forecast(pd.DataFrame(rows), supplier_id, facility_id, product)
            if row is not None and row_meets_exact_threshold(row):
                row["forecast_match_level"] = "REFINERY_GROUP_SUPPLIER_PRODUCT"
                return row

        # Level 2: exact supplier + refinery plant(s), any product
        rows = [r for r in _EDGE_IDX_SUP.get(supplier_id, [])
                if r.get("facility", "") in refinery_set]
        if rows:
            row = aggregate_forecast(pd.DataFrame(rows), supplier_id, facility_id, product)
            if row is not None:
                row["forecast_match_level"] = "REFINERY_GROUP_SUPPLIER"
                return row

        if supplier_type:
            # Level 3: supplier type + refinery plant(s) + product
            rows = [r for r in _EDGE_IDX_TYPE_FAC_PROD.get((supplier_type, "", ""), [])
                    if r.get("facility", "") in refinery_set and r.get("product", "") == product]
            if not rows:
                rows = [r for r in _EDGE_IDX_PROD.get(product, [])
                        if r.get("supplier_type", "") == supplier_type and r.get("facility", "") in refinery_set]
            if rows:
                row = aggregate_forecast(pd.DataFrame(rows), supplier_id, facility_id, product)
                if row is not None:
                    row["forecast_match_level"] = "REFINERY_GROUP_SUPPLIER_TYPE_PRODUCT"
                    return row

            # Level 4: supplier type + refinery plant(s), any product
            rows = [r for r in _EDGE_IDX_PROD.get(product, [])
                    if r.get("supplier_type", "") == supplier_type and r.get("facility", "") in refinery_set]
            if not rows:
                rows = [r for r in _EDGE_IDX_SUP.get(supplier_id, [])
                        if r.get("facility", "") in refinery_set]
            rows_typed = [r for r in (
                    list({id(r): r for r in _EDGE_IDX_PROD.get(product, []) + list(_EDGE_IDX_SUP.get(supplier_id, []))}.values())
                ) if r.get("supplier_type", "") == supplier_type and r.get("facility", "") in refinery_set]
            if rows_typed:
                row = aggregate_forecast(pd.DataFrame(rows_typed), supplier_id, facility_id, product)
                if row is not None:
                    row["forecast_match_level"] = "REFINERY_GROUP_SUPPLIER_TYPE"
                    return row

    # Level 5: exact supplier + facility + product
    rows = _EDGE_IDX.get((supplier_id, facility_id, product), [])
    if rows:
        row = aggregate_forecast(pd.DataFrame(rows), supplier_id, facility_id, product)
        if row is not None and row_meets_exact_threshold(row):
            row["forecast_match_level"] = "EXACT_SUPPLIER_FACILITY_PRODUCT"
            return row

    # Level 6: exact supplier + facility, any product
    rows = _EDGE_IDX_SUP_FAC.get((supplier_id, facility_id), [])
    if rows:
        row = aggregate_forecast(pd.DataFrame(rows), supplier_id, facility_id, product)
        if row is not None:
            row["forecast_match_level"] = "EXACT_SUPPLIER_FACILITY"
            return row

    if supplier_type:
        # Level 7: supplier_type + facility + product
        rows = [r for r in _EDGE_IDX_TYPE_FAC_PROD.get((supplier_type, facility_id, product), [])]
        if not rows:
            rows = [r for r in _EDGE_IDX_PROD.get(product, [])
                    if r.get("supplier_type", "") == supplier_type and r.get("facility", "") == facility_id]
        if rows:
            row = aggregate_forecast(pd.DataFrame(rows), supplier_id, facility_id, product)
            if row is not None:
                row["forecast_match_level"] = "SUPPLIER_TYPE_FACILITY_PRODUCT"
                return row

    # Level 8: global product fallback
    rows = _EDGE_IDX_PROD.get(product, [])
    if rows:
        row = aggregate_forecast(pd.DataFrame(rows), supplier_id, facility_id, product)
        if row is not None:
            row["forecast_match_level"] = "GLOBAL_PRODUCT"
            return row

    return None


def compute_edge_estimated_days(
    supplier_id: str,
    facility_id: str,
    product: str,
    allocated_qty: float,
) -> Dict[str, Any]:
    supplier_id = str(supplier_id)
    facility_id = str(facility_id)
    product = str(product).upper().strip()
    allocated_qty = float(allocated_qty or 0.0)

    edge_days_cache = _get_edge_days_cache() 

    cache_key = (supplier_id, facility_id, product, round(allocated_qty, 2))
    if cache_key in edge_days_cache:
        return edge_days_cache[cache_key]

    supplier_type = get_facility_type_safe(supplier_id)
    receiver_type = get_facility_type_for_trace(facility_id)

    if supplier_type == "ESTATE" or product == "FFB":
        row = get_estate_edge_forecast_row(supplier_id, facility_id, product)

        if row is not None:
            throughput_tpd = float(row.get("throughput_tpd", 0.0) or 0.0)
            lead_time_days = float(row.get("median_duration_days", 0.0) or 0.0)
            match_level = str(row.get("forecast_match_level", "ESTATE_UNKNOWN"))

            if throughput_tpd <= 0:
                throughput_tpd = get_estate_global_throughput()
            if lead_time_days <= 0:
                lead_time_days = get_estate_global_lead()

            flow_days = allocated_qty / max(throughput_tpd, 1.0)
            estimated_days_raw = max(flow_days, 0.1)
            estimated_days = apply_estimated_day_rules(estimated_days_raw, facility_id)

            result = {
                "lead_time_days": round(lead_time_days, 2),
                "throughput_tpd": round(throughput_tpd, 2),
                "flow_days": round(flow_days, 2),
                "estimated_days": estimated_days,
                "estimated_days_raw": round(estimated_days_raw, 2),
                "target_days": get_target_days_for_edge(facility_id),
                "forecast_source": "ESTATE_HISTORICAL_FORECAST",
                "forecast_match_level": match_level,
            }
            edge_days_cache[cache_key] = result
            return result

        result = {
                "lead_time_days": 0.0,
                "throughput_tpd": 0.0,
                "flow_days": 0.0,
                "estimated_days": 0,
                "estimated_days_raw": 0.0,
                "target_days": get_target_days_for_edge(facility_id),
                "forecast_source": "ESTATE_NO_EXACT_FORECAST",
                "forecast_match_level": "ESTATE_NO_EXACT_MATCH",
            }
        edge_days_cache[cache_key] = result
        return result

    row = get_edge_forecast_row(supplier_id, facility_id, product)

    if row is not None:
        throughput_tpd = float(row.get("throughput_tpd", 0.0) or 0.0)
        lead_time_days = float(row.get("median_duration_days", 0.0) or 0.0)
        match_level = str(row.get("forecast_match_level", "UNKNOWN"))

        if throughput_tpd <= 0:
            throughput_tpd = get_global_product_throughput(product)
        if lead_time_days <= 0:
            lead_time_days = get_global_product_lead(product)

        flow_days = allocated_qty / max(throughput_tpd, 1.0)
        estimated_days_raw = max(flow_days, 0.1)
        estimated_days = apply_estimated_day_rules(estimated_days_raw, facility_id)

        result = {
            "lead_time_days": round(lead_time_days, 2),
            "throughput_tpd": round(throughput_tpd, 2),
            "flow_days": round(flow_days, 2),
            "estimated_days": estimated_days,
            "estimated_days_raw": round(estimated_days_raw, 2),
            "target_days": get_target_days_for_edge(facility_id),
            "forecast_source": "HISTORICAL_FORECAST",
            "forecast_match_level": match_level,
        }
        edge_days_cache[cache_key] = result
        return result

    if receiver_type == "REFINERY":
        lead_time_days = DEFAULT_LEAD_DAYS_BY_TYPE["REFINERY_GROUP"]
    else:
        lead_time_days = DEFAULT_LEAD_DAYS_BY_TYPE.get(supplier_type or "UNKNOWN", 1.0)

    throughput_tpd = get_global_product_throughput(product)
    flow_days = allocated_qty / max(throughput_tpd, 1.0)
    estimated_days_raw = max(flow_days, 0.1)
    estimated_days = apply_estimated_day_rules(estimated_days_raw, facility_id)

    result = {
        "lead_time_days": round(lead_time_days, 2),
        "throughput_tpd": round(throughput_tpd, 2),
        "flow_days": round(flow_days, 2),
        "estimated_days": estimated_days,
        "estimated_days_raw": round(estimated_days_raw, 2),
        "target_days": get_target_days_for_edge(facility_id),
        "forecast_source": "SAFE_FALLBACK",
        "forecast_match_level": "SAFE_DEFAULT",
    }
    edge_days_cache[cache_key] = result
    return result


