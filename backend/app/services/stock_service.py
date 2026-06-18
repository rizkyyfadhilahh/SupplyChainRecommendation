from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.config import (
    CACHE_TTL_SECONDS,
    DIRECT_REFINERY_PRODUCTS,
    REFINED_PRODUCTS,
    facility_groups,
    process_map,
)
from app.data_loader import get_app_data, require_app_data
from app.repositories.csv_repository import (
    get_stock_snapshot,
    load_sloc_eudr_config,
    load_stock_snapshot,
    save_sloc_eudr_config,
)
from app.utils import bool_from_any, to_date_str


sloc_cache_lock = Lock()

SLOC_CACHE: Dict[str, Any] = {
    "stock_snapshot": None,
    "stock_max_date": None,
    "base_sloc_master": None,
    "configured_sloc_master": None,
    "last_refresh_at": None,
}


def normalize_stock_product(material_type: Any, material_desc: Any) -> Optional[str]:
    mt = str(material_type).upper().strip()
    md = str(material_desc).upper().strip()

    if "PFAD" in mt:
        return "PFAD"
    if "RBDPS" in mt:
        return "RBDPS"
    if "RBDST" in mt:
        return "RBDST"
    if "RBDOLN" in mt or "OLEIN" in mt:
        return "RBDOLN"
    if "RBDPKO" in mt:
        return "RBDPKO"
    if ("CPKO" in mt or "PKO" in mt) and "RBD" not in mt:
        return "PKO"
    if "RBDPO" in mt or "NBDPO" in mt:
        return "RBDPO"
    if mt.startswith("CPO") or "CPO" in mt:
        return "CPO"
    if mt == "PK" or mt.startswith("PK "):
        return "PK"

    if "PFAD" in md:
        return "PFAD"
    if "RBDPS" in md:
        return "RBDPS"
    if "RBDST" in md:
        return "RBDST"
    if "RBDOLN" in md or "OLEIN" in md:
        return "RBDOLN"
    if "RBDPKO" in md:
        return "RBDPKO"
    if ("CPKO" in md or "PKO" in md) and "RBD" not in md:
        return "PKO"
    if "RBDPO" in md or "NBDPO" in md:
        return "RBDPO"
    if md.startswith("CPO") or "CRUDE PALM OIL" in md:
        return "CPO"
    if md == "PK" or md.startswith("PK "):
        return "PK"

    return None


def seed_dummy_sloc_eudr_config(snapshot: pd.DataFrame) -> pd.DataFrame:
    if snapshot.empty:
        return pd.DataFrame(columns=[
            "plant",
            "storagelocation",
            "material",
            "eudr",
            "eudr_valid_from",
            "eudr_valid_to",
        ])

    base = (
        snapshot[["plant", "storagelocation", "material"]]
        .drop_duplicates()
        .sort_values(by=["plant", "storagelocation", "material"])
        .reset_index(drop=True)
        .copy()
    )

    mask = base.index % 2 == 0

    base["eudr"] = mask
    base["eudr_valid_from"] = pd.NaT
    base["eudr_valid_to"] = pd.NaT

    today = pd.Timestamp.now().normalize()
    base.loc[mask, "eudr_valid_from"] = today - pd.Timedelta(days=30)
    base.loc[mask, "eudr_valid_to"] = today + pd.Timedelta(days=365)

    return base


def build_base_sloc_master_from_snapshot(snapshot: pd.DataFrame) -> pd.DataFrame:
    if snapshot.empty:
        cols = [
            "plant",
            "name1",
            "storagelocation",
            "material",
            "material_type",
            "materialdescription",
            "current_stock",
            "refinery_group",
            "product_code",
            "eudr",
            "eudr_valid_from",
            "eudr_valid_to",
        ]
        return pd.DataFrame(columns=cols)

    plant_to_refinery = require_app_data("plant_to_refinery")

    base = snapshot.copy()
    base["refinery_group"] = base["plant"].map(plant_to_refinery)
    base["product_code"] = base.apply(
        lambda r: normalize_stock_product(
            r.get("material_type"),
            r.get("materialdescription"),
        ),
        axis=1,
    )
    return base


def apply_sloc_config_to_base(
    base_sloc_master: pd.DataFrame,
    cfg: pd.DataFrame,
) -> pd.DataFrame:
    if base_sloc_master.empty:
        return base_sloc_master.copy()

    out = base_sloc_master.copy()

    if cfg.empty:
        out["eudr"] = False
        out["eudr_valid_from"] = pd.NaT
        out["eudr_valid_to"] = pd.NaT
        out["current_stock"] = pd.to_numeric(
            out["current_stock"],
            errors="coerce",
        ).fillna(0.0)
        return out

    out = out.merge(
        cfg,
        on=["plant", "storagelocation", "material"],
        how="left",
    )

    out["eudr"] = out["eudr"].fillna(False).apply(bool_from_any)
    out["eudr_valid_from"] = pd.to_datetime(
        out["eudr_valid_from"],
        errors="coerce",
    )
    out["eudr_valid_to"] = pd.to_datetime(
        out["eudr_valid_to"],
        errors="coerce",
    )
    out["current_stock"] = pd.to_numeric(
        out["current_stock"],
        errors="coerce",
    ).fillna(0.0)

    return out


def ensure_sloc_config_seeded() -> None:
    cfg = load_sloc_eudr_config()

    if not cfg.empty:
        return

    events_bc = require_app_data("events_bc")
    snapshot = load_stock_snapshot(events_bc).copy()
    seeded = seed_dummy_sloc_eudr_config(snapshot)
    save_sloc_eudr_config(seeded)


def get_cached_sloc_master(
    force_refresh: bool = False,
) -> Tuple[pd.DataFrame, Optional[str], Optional[str]]:
    now = datetime.utcnow()

    with sloc_cache_lock:
        last_refresh_at = SLOC_CACHE["last_refresh_at"]
        cache_valid = (
            not force_refresh
            and SLOC_CACHE["configured_sloc_master"] is not None
            and last_refresh_at is not None
            and (now - last_refresh_at).total_seconds() < CACHE_TTL_SECONDS
        )

        if cache_valid:
            return (
                SLOC_CACHE["configured_sloc_master"].copy(),
                SLOC_CACHE["stock_max_date"],
                last_refresh_at.isoformat(),
            )

        events_bc = require_app_data("events_bc")
        snapshot = load_stock_snapshot(events_bc).copy()
        stock_max_date = get_stock_snapshot()
        base_sloc_master = build_base_sloc_master_from_snapshot(snapshot)

        cfg = load_sloc_eudr_config()
        configured_sloc_master = apply_sloc_config_to_base(
            base_sloc_master,
            cfg,
        )

        SLOC_CACHE["stock_snapshot"] = snapshot
        SLOC_CACHE["stock_max_date"] = stock_max_date
        SLOC_CACHE["base_sloc_master"] = base_sloc_master
        SLOC_CACHE["configured_sloc_master"] = configured_sloc_master
        SLOC_CACHE["last_refresh_at"] = now

        return configured_sloc_master.copy(), stock_max_date, now.isoformat()


def is_sloc_eudr_active(row: pd.Series, current_date: pd.Timestamp) -> bool:
    if not bool(row.get("eudr", False)):
        return False

    valid_from = pd.to_datetime(row.get("eudr_valid_from"), errors="coerce")
    valid_to = pd.to_datetime(row.get("eudr_valid_to"), errors="coerce")

    if pd.isna(valid_from) or pd.isna(valid_to):
        return False

    return valid_from.normalize() <= current_date <= valid_to.normalize()


def get_stock_candidate_products(requested_product: str) -> List[str]:
    requested_product = str(requested_product).upper().strip()

    if requested_product in REFINED_PRODUCTS or requested_product in DIRECT_REFINERY_PRODUCTS:
        return [requested_product]

    result: List[str] = []
    current = requested_product

    while current and current not in result:
        result.append(current)
        current = process_map.get(current)

    return result


def classify_slocs(
    candidate_pool: pd.DataFrame,
    spec: str,
    current_date: pd.Timestamp,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = candidate_pool.copy()

    if df.empty:
        return df.copy(), df.copy()

    df["eudr_active_today"] = df.apply(
        lambda r: is_sloc_eudr_active(r, current_date),
        axis=1,
    )

    reasons: List[str] = []
    eligible_mask: List[bool] = []

    for _, row in df.iterrows():
        stock = float(row.get("current_stock", 0) or 0)

        if stock <= 0:
            eligible_mask.append(False)
            reasons.append("Rejected: current_stock <= 0")
            continue

        if str(spec).upper() == "EUDR" and not bool(row.get("eudr_active_today", False)):
            eligible_mask.append(False)
            reasons.append("Rejected: EUDR requested but SLOC not active EUDR")
            continue

        eligible_mask.append(True)

        if str(spec).upper() == "EUDR":
            reasons.append("Eligible by refinery + product + active EUDR")
        else:
            reasons.append("Eligible by refinery + product")

    df["eligible"] = eligible_mask
    df["eligibility_reason"] = reasons

    eligible = df[df["eligible"]].copy()
    ineligible = df[~df["eligible"]].copy()

    return eligible, ineligible


def sloc_row_to_output(
    row: pd.Series,
    allocated_qty: float = 0.0,
    stock_after: Optional[float] = None,
) -> Dict[str, Any]:
    stock_before = float(row.get("current_stock", 0) or 0)

    return {
        "plant": str(row.get("plant", "")),
        "name1": str(row.get("name1", "")),
        "storage_location": str(row.get("storagelocation", "")),
        "material": str(row.get("material", "")),
        "material_type": str(row.get("material_type", "")),
        "material_description": str(row.get("materialdescription", "")),
        "refinery_group": row.get("refinery_group"),
        "product_code": row.get("product_code"),
        "stock_before": round(stock_before, 2),
        "allocated_qty": round(float(allocated_qty or 0), 2),
        "stock_after": round(
            float(stock_after if stock_after is not None else stock_before),
            2,
        ),
        "eudr_label": bool(row.get("eudr", False)),
        "eudr_valid_from": to_date_str(row.get("eudr_valid_from")),
        "eudr_valid_to": to_date_str(row.get("eudr_valid_to")),
        "eudr_active_today": bool(row.get("eudr_active_today", False)),
        "eligible": bool(row.get("eligible", False)),
        "eligibility_reason": row.get("eligibility_reason"),
    }


def allocate_stock(
    sloc_state: pd.DataFrame,
    refinery_group: str,
    requested_product: str,
    spec: str,
    demand_qty: float,
    current_date: pd.Timestamp,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    candidate_products = get_stock_candidate_products(requested_product)
    refinery_pool = sloc_state[
        sloc_state["refinery_group"] == refinery_group
    ].copy()

    used_product: Optional[str] = None
    chosen_pool = pd.DataFrame()
    chosen_eligible = pd.DataFrame()
    chosen_ineligible = pd.DataFrame()

    for product_code in candidate_products:
        pool = refinery_pool[refinery_pool["product_code"] == product_code].copy()

        if pool.empty:
            continue

        eligible, ineligible = classify_slocs(pool, spec, current_date)

        if not eligible.empty:
            used_product = product_code
            chosen_pool = pool
            chosen_eligible = eligible
            chosen_ineligible = ineligible
            break

    if used_product is None:
        for product_code in candidate_products:
            pool = refinery_pool[refinery_pool["product_code"] == product_code].copy()

            if not pool.empty:
                eligible, ineligible = classify_slocs(pool, spec, current_date)
                used_product = product_code
                chosen_pool = pool
                chosen_eligible = eligible
                chosen_ineligible = ineligible
                break

    selected_slocs: List[Dict[str, Any]] = []
    eligible_but_unused: List[Dict[str, Any]] = []
    ineligible_slocs: List[Dict[str, Any]] = []

    fulfilled_from_stock = 0.0
    unmet_demand = float(demand_qty)
    total_before = 0.0
    total_after = 0.0

    if used_product is not None and not chosen_pool.empty:
        total_before = float(chosen_pool["current_stock"].sum())

        eligible_sorted = chosen_eligible.sort_values(
            by=["plant", "storagelocation", "material"],
            ascending=[True, True, True],
        ).copy()

        remaining = float(demand_qty)

        for _, row in eligible_sorted.iterrows():
            stock_before = float(row["current_stock"])

            if remaining <= 0:
                eligible_but_unused.append(
                    sloc_row_to_output(
                        row,
                        allocated_qty=0,
                        stock_after=stock_before,
                    )
                )
                continue

            allocated = min(stock_before, remaining)
            stock_after = stock_before - allocated
            remaining -= allocated

            if allocated > 0:
                selected_slocs.append(
                    sloc_row_to_output(
                        row,
                        allocated_qty=allocated,
                        stock_after=stock_after,
                    )
                )

                state_mask = (
                    (sloc_state["plant"].astype(str) == str(row["plant"]))
                    & (
                        sloc_state["storagelocation"].astype(str)
                        == str(row["storagelocation"])
                    )
                    & (sloc_state["material"].astype(str) == str(row["material"]))
                )
                sloc_state.loc[state_mask, "current_stock"] = stock_after

            else:
                eligible_but_unused.append(
                    sloc_row_to_output(
                        row,
                        allocated_qty=0,
                        stock_after=stock_before,
                    )
                )

        for _, row in chosen_ineligible.iterrows():
            ineligible_slocs.append(
                sloc_row_to_output(
                    row,
                    allocated_qty=0,
                    stock_after=float(row["current_stock"]),
                )
            )

        used_keys = {
            (x["plant"], x["storage_location"], x["material"])
            for x in selected_slocs
        }

        for _, row in eligible_sorted.iterrows():
            key = (
                str(row["plant"]),
                str(row["storagelocation"]),
                str(row["material"]),
            )

            if key not in used_keys:
                already_exists = any(
                    y["plant"] == str(row["plant"])
                    and y["storage_location"] == str(row["storagelocation"])
                    and y["material"] == str(row["material"])
                    for y in eligible_but_unused
                )

                if not already_exists:
                    eligible_but_unused.append(
                        sloc_row_to_output(
                            row,
                            allocated_qty=0,
                            stock_after=float(row["current_stock"]),
                        )
                    )

        fulfilled_from_stock = float(
            sum(x["allocated_qty"] for x in selected_slocs)
        )
        unmet_demand = max(float(demand_qty) - fulfilled_from_stock, 0.0)

        pool_after = sloc_state[
            (sloc_state["refinery_group"] == refinery_group)
            & (sloc_state["product_code"] == used_product)
        ].copy()
        total_after = float(pool_after["current_stock"].sum())

    stock_status = "NOT_FULFILLED"

    if fulfilled_from_stock >= demand_qty:
        stock_status = "FULLY_FULFILLED"
    elif fulfilled_from_stock > 0:
        stock_status = "PARTIALLY_FULFILLED"

    stock_overview = {
        "stock_check_basis": {
            "requested_product": str(requested_product).upper(),
            "matched_products_for_stock": [] if used_product is None else [used_product],
            "refinery_group": refinery_group,
            "request_date": current_date.strftime("%Y-%m-%d"),
            "spec_filter": str(spec).upper(),
        },
        "summary": {
            "total_stock_before_allocation": round(total_before, 2),
            "total_stock_allocated": round(fulfilled_from_stock, 2),
            "total_stock_after_allocation": round(total_after, 2),
            "fulfilled_from_stock": round(fulfilled_from_stock, 2),
            "unmet_demand": round(unmet_demand, 2),
            "stock_status": stock_status,
        },
        "selected_slocs": selected_slocs,
        "eligible_but_unused_slocs": eligible_but_unused,
        "ineligible_slocs": ineligible_slocs,
    }

    return stock_overview, sloc_state


def get_sloc_master_service(facility: Optional[str] = None) -> Dict[str, Any]:
    sloc_master, max_date, last_refresh_at = get_cached_sloc_master()

    if facility:
        if facility not in facility_groups:
            raise ValueError(f"Facility '{facility}' tidak valid")

        sloc_master = sloc_master[
            sloc_master["refinery_group"] == facility
        ].copy()

    if sloc_master.empty:
        return {
            "max_date": max_date,
            "last_refresh_at": last_refresh_at,
            "rows": [],
        }

    out = sloc_master.copy()
    out["eudr_valid_from"] = pd.to_datetime(
        out["eudr_valid_from"],
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")
    out["eudr_valid_to"] = pd.to_datetime(
        out["eudr_valid_to"],
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")
    out = out.replace({np.nan: None})

    return {
        "max_date": max_date,
        "last_refresh_at": last_refresh_at,
        "rows": out.to_dict(orient="records"),
    }


def refresh_stock_snapshot_service() -> Dict[str, Any]:
    sloc_master, max_date, last_refresh_at = get_cached_sloc_master(
        force_refresh=True
    )

    return {
        "status": "ok",
        "max_date": max_date,
        "last_refresh_at": last_refresh_at,
        "rows_count": int(len(sloc_master)),
    }