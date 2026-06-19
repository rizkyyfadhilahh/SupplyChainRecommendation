import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import HTTPException

from app.config import (
    ALLOW_CPO_TOLLING,
    ALLOW_TERMINAL_MILL,
    ALLOW_TERMINAL_VENDOR,
    DIRECT_PRODUCT_EMPTY_FALLBACK,
    DIRECT_REFINERY_PRODUCTS,
    ENABLE_QUEUE_SCHEDULING,
    FORECAST_TARGET_DAYS,
    MIN_ALLOCATED_SHARE_PER_SUPPLIER,
    get_dynamic_min_allocated_share,
    PASS_THROUGH_TYPES,
    REFINERIES_WITH_KCP,
    VENDOR_TYPE,
    buyer_blacklist,
    conversion_map,
    facility_groups,
    process_map,
)

from app.schemas import TraceRequest

from app.services.stock_service import (
    allocate_stock,
    get_cached_sloc_master,
)

from app.services.forecast_service import (
    apply_estimated_day_rules,
    compute_edge_estimated_days,
    get_edge_forecast_row,
    get_estate_edge_forecast_row,
)

from app.services.queue_service import (
    get_current_date,
    add_days_to_date,
    compute_schedule_days_from_tree,
    apply_queue_scheduling_to_paths,
    compute_total_estimated_days_by_level,
)

from app.utils import (
    is_valid_value,
    normalize_display_key,
    normalize_facility_type,
    normalize_spec_value,
    normalize_trace_product,
)

from app.data_loader import get_app_data


logger = logging.getLogger(__name__)

def _product_flow() -> pd.DataFrame:
    return get_app_data("product_flow")


def _ffb_flow() -> pd.DataFrame:
    return get_app_data("ffb_flow")


def _tolling_flow() -> pd.DataFrame:
    return get_app_data("tolling_flow")


def _mill_ids() -> Set[str]:
    return get_app_data("mill_ids", set())


def _facility_name_lookup() -> Dict[str, str]:
    return get_app_data("facility_name_lookup", {})


def _facility_type_lookup() -> Dict[str, str]:
    return get_app_data("facility_type_lookup", {})


def _facility_spec_lookup() -> Dict[str, str]:
    return get_app_data("facility_spec_lookup", {})


def get_facility_type_safe(facility_id: Any) -> str:
    fid = str(facility_id).strip()
    return normalize_facility_type(_facility_type_lookup().get(fid, ""))


def get_facility_name_safe(facility_id: Any) -> str:
    fid = str(facility_id).strip()
    return str(_facility_name_lookup().get(fid, fid))


def get_facility_spec_safe(facility_id: Any) -> str:
    fid = str(facility_id).strip()
    return str(_facility_spec_lookup().get(fid, ""))

def get_conversion_ratio(product: str) -> float:
    return float(conversion_map.get(str(product).upper(), 1.0) or 1.0)


def convert_volume(product: str, qty: float) -> float:
    ratio = get_conversion_ratio(product)
    if ratio <= 0:
        return float(qty)
    return float(qty) / ratio


def convert_product_quantity_along_path(from_product: str, to_product: str, qty: float) -> float:
    from_product = str(from_product).upper().strip()
    to_product = str(to_product).upper().strip()
    converted_qty = float(qty)

    if from_product == to_product:
        return converted_qty

    visited: Set[str] = set()
    current = from_product

    while current != to_product:
        if current in visited:
            break
        visited.add(current)

        next_product = process_map.get(current)
        if not next_product:
            break

        converted_qty = convert_volume(current, converted_qty)
        current = str(next_product).upper().strip()

    return converted_qty


def convert_allocation_to_candidate_qty(
    allocation_qty: float,
    query_product: str,
    candidate_product: str,
) -> float:
    query_product = str(query_product).upper().strip()
    candidate_product = str(candidate_product).upper().strip()

    if query_product == candidate_product:
        return float(allocation_qty)

    return convert_product_quantity_along_path(
        from_product=query_product,
        to_product=candidate_product,
        qty=float(allocation_qty),
    )


def map_supplier_output_identity(
    supplier_id: Any,
    supplier_name: Any,
    supplier_type: Any,
) -> Dict[str, Any]:

    raw_supplier_id = str(supplier_id).strip()
    raw_supplier_name = str(
        supplier_name if pd.notna(supplier_name) else raw_supplier_id
    )
    raw_supplier_type = str(
        supplier_type if pd.notna(supplier_type) else "UNKNOWN"
    ).upper()

    return {
        "supplier_id": raw_supplier_id,
        "supplier_name": raw_supplier_name,
        "supplier_type": raw_supplier_type,
        "alias_merged": False,
    }

def is_hardcoded_vendor_id(value: Any) -> bool:
    return is_external_vendor_id(value)

def is_external_vendor_id(value: Any) -> bool:
    value = str(value).strip()
    return is_valid_value(value) and value.startswith("1")

def is_internal_vendor_id(value: Any) -> bool:
    value = str(value).strip()
    return is_valid_value(value) and value.startswith("35")

def is_supported_vendor_id(value: Any) -> bool:
    return is_external_vendor_id(value) or is_internal_vendor_id(value)

def extract_facility_id_from_spb(value: Any) -> str:
    raw = str(value).strip()

    if not is_valid_value(raw):
        return ""

    digits = "".join(ch for ch in raw if ch.isdigit())

    if len(digits) < 4:
        return ""

    return digits[:4]

def resolve_spb_facility(spb_value: Any) -> Dict[str, str]:
    facility_id = extract_facility_id_from_spb(spb_value)

    if not is_valid_value(facility_id):
        return {
            "facility_id": "",
            "facility_name": "",
            "facility_type": "",
        }

    facility_type = get_facility_type_safe(facility_id)
    facility_name = get_facility_name_safe(facility_id)

    if not is_valid_value(facility_type):
        return {
            "facility_id": "",
            "facility_name": "",
            "facility_type": "",
        }

    return {
        "facility_id": facility_id,
        "facility_name": facility_name,
        "facility_type": facility_type,
    }

def get_facility_type_for_trace(facility: str) -> str:
    facility = str(facility).strip()

    if facility in facility_groups:
        return "REFINERY"

    return get_facility_type_safe(facility)

def is_facility_type(facility_id: Any, expected_type: str) -> bool:
    return get_facility_type_safe(facility_id) == str(expected_type).upper()

def facility_has_kcp(current_facility: str) -> bool:
    return str(current_facility).strip() in REFINERIES_WITH_KCP

def allow_fallback_for_facility(current_facility: str) -> bool:
    return get_facility_type_for_trace(current_facility) != "REFINERY"


def get_next_query_product(current_product: str, current_facility: str) -> Optional[str]:
    current_product = str(current_product).upper()
    facility_type = get_facility_type_for_trace(current_facility)

    if facility_type == "REFINERY":
        if current_product in {"RBDPO", "RBDOLN", "RBDST", "RBDPS", "PFAD"}:
            return "CPO"

        if current_product in {"RBDPKO"}:
            return "PKO"

        if current_product in DIRECT_REFINERY_PRODUCTS:
            return current_product

        return process_map.get(current_product)

    if facility_type in PASS_THROUGH_TYPES or facility_type == VENDOR_TYPE:
        return current_product

    return process_map.get(current_product)


def get_receiver_facilities(current_facility: str) -> List[str]:
    if current_facility in facility_groups:
        return [str(x) for x in facility_groups[current_facility]]
    return [str(current_facility)]


def get_upstream_candidates_df(
    current_facility: str,
    query_product: str,
    blacklist: Set[str],
    spec: str = "ALL",
    warnings: Optional[List[Dict[str, str]]] = None,
    collect_warnings: bool = True,
) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    warnings = warnings or []
    facilities = get_receiver_facilities(current_facility)

    product_flow = _product_flow()

    df = product_flow[
        (product_flow["facility"].astype(str).isin(facilities)) &
        (product_flow["product"].astype(str).str.upper() == str(query_product).upper())
    ].copy()

    if df.empty:
        return df, warnings

    if blacklist:
        blocked = df[df["supplier"].astype(str).isin(blacklist)].copy()
        if collect_warnings and not blocked.empty:
            for _, row in blocked.iterrows():
                sid = str(row["supplier"])
                warnings.append({
                    "supplier_id": sid,
                    "supplier_name": _facility_name_lookup().get(sid, sid),
                })
        df = df[~df["supplier"].astype(str).isin(blacklist)].copy()

    if df.empty:
        return df, warnings

    agg_cols = [
    c for c in [
        "supplier",
        "supplier_name",
        "supplier_type",
        "supplier_spec",
        "supplier_source_kind",
    ]
    if c in df.columns
    ]

    agg_dict = {
        "quantity": "sum",
    }

    if "raw_vendor_ids" in df.columns:
        agg_dict["raw_vendor_ids"] = lambda x: sorted(
            set(
                item
                for sublist in x
                if isinstance(sublist, list)
                for item in sublist
            )
        )[:10]

    if "raw_vendor_names" in df.columns:
        agg_dict["raw_vendor_names"] = lambda x: sorted(
            set(
                item
                for sublist in x
                if isinstance(sublist, list)
                for item in sublist
            )
        )[:10]

    if "vendor_resolution_rules" in df.columns:
        agg_dict["vendor_resolution_rules"] = lambda x: sorted(
            set(
                item
                for sublist in x
                if isinstance(sublist, list)
                for item in sublist
            )
        )[:10]

    df = df.groupby(
        agg_cols,
        as_index=False,
        dropna=False,
    ).agg(agg_dict)

    df["supplier"] = df["supplier"].astype(str)
    df["supplier_type"] = df["supplier_type"].fillna("").astype(str).apply(normalize_facility_type)
    df["supplier_spec"] = df["supplier_spec"].fillna("").astype(str).apply(normalize_spec_value)

    total_qty = float(df["quantity"].sum())
    df["probability"] = 0.0 if total_qty == 0 else df["quantity"] / total_qty

    df["is_vendor"] = df["supplier_type"].astype(str).str.upper().eq("VENDOR")
    df["selection_priority"] = 1

    df["candidate_product"] = str(query_product).upper().strip()
    df["upstream_route_kind"] = f"DIRECT_{str(query_product).upper().strip()}_SUPPLY"
    return df, warnings


def get_candidate_df_with_fallback(
    current_facility: str,
    current_product: str,
    quantity: float,
    spec: str,
    blacklist: Set[str],
    warnings: Optional[List[Dict[str, str]]] = None,
    collect_warnings: bool = True,
    allow_fallback: bool = True,
):
    warnings = warnings or []

    query_product = get_next_query_product(current_product, current_facility)

    if not query_product:
        return None, 0.0, pd.DataFrame(), warnings

    query_quantity = convert_product_quantity_along_path(
        from_product=current_product,
        to_product=query_product,
        qty=quantity,
    )

    df, warnings = get_upstream_candidates_df(
        current_facility=current_facility,
        query_product=query_product,
        blacklist=blacklist,
        spec=spec,
        warnings=warnings,
        collect_warnings=collect_warnings,
    )

    if (
        df.empty
        and get_facility_type_for_trace(current_facility) == "REFINERY"
        and str(query_product).upper().strip() in DIRECT_PRODUCT_EMPTY_FALLBACK
    ):
        fallback_product = DIRECT_PRODUCT_EMPTY_FALLBACK[
            str(query_product).upper().strip()
        ]

        fallback_quantity = convert_product_quantity_along_path(
            from_product=current_product,
            to_product=fallback_product,
            qty=quantity,
        )

        fallback_df, warnings = get_upstream_candidates_df(
            current_facility=current_facility,
            query_product=fallback_product,
            blacklist=blacklist,
            spec=spec,
            warnings=warnings,
            collect_warnings=collect_warnings,
        )

        if not fallback_df.empty:
            query_product = fallback_product
            query_quantity = fallback_quantity
            df = fallback_df

    while allow_fallback and df.empty and query_product in process_map:
        next_product = process_map[query_product]
        query_product = next_product
        query_quantity = convert_product_quantity_along_path(
            from_product=current_product,
            to_product=query_product,
            qty=quantity,
        )

        df, warnings = get_upstream_candidates_df(
            current_facility=current_facility,
            query_product=query_product,
            blacklist=blacklist,
            spec=spec,
            warnings=warnings,
            collect_warnings=collect_warnings,
        )

    return query_product, query_quantity, df, warnings

def get_supplier_capacity_cap(
    supplier_id: str,
    facility_id: str,
    product: str,
    fallback_hist_qty: float = 0.0,
    demand_qty: float = 0.0,
    planning_days: Optional[float] = None,
    cap_mode: str = "EXPANDED",
) -> float:
    supplier_id = str(supplier_id)
    facility_id = str(facility_id)
    product = str(product).upper().strip()

    if product == "FFB":
        row = get_estate_edge_forecast_row(
            supplier_id=supplier_id,
            facility_id=facility_id,
            product=product,
        )
    else:
        row = get_edge_forecast_row(
            supplier_id=supplier_id,
            facility_id=facility_id,
            product=product,
        )

    if row is None:
        return float(max(fallback_hist_qty, 0.0))

    total_qty = float(row.get("total_qty", 0.0) or 0.0)
    median_daily_qty = float(row.get("median_daily_qty", 0.0) or 0.0)
    active_days = float(row.get("active_days", 0.0) or 0.0)

    planning_days_value = (
        float(planning_days)
        if planning_days is not None and float(planning_days) > 0
        else float(FORECAST_TARGET_DAYS)
    )

    cap_from_historical_active_days = median_daily_qty * active_days
    cap_from_planning_days = median_daily_qty * planning_days_value

    if str(cap_mode).upper() == "HISTORICAL_CONSERVATIVE":
        candidates = [
            x for x in [
                total_qty,
                cap_from_historical_active_days,
            ]
            if x > 0
        ]

        if not candidates:
            return float(max(fallback_hist_qty, 0.0))

        return float(min(candidates))

    candidates = [
        x for x in [
            total_qty,
            cap_from_historical_active_days,
            cap_from_planning_days,
            fallback_hist_qty,
        ]
        if x > 0
    ]

    if not candidates:
        return 0.0

    return float(max(candidates))

def allocate_with_capacity_caps(
    work: pd.DataFrame,
    demand_qty: float,
) -> pd.DataFrame:
    if work.empty:
        return work.copy()

    out = work.copy()
    out["allocated_volume"] = 0.0
    out["capacity_cap"] = pd.to_numeric(out["capacity_cap"], errors="coerce").fillna(0.0)
    out["probability"] = pd.to_numeric(out["probability"], errors="coerce").fillna(0.0)

    remaining = float(demand_qty)

    # Pass 1: alokasi mengikuti capacity_cap (distribusi berdasarkan probabilitas)
    for _ in range(len(out) + 3):
        if remaining <= 1e-9:
            break

        available_mask = out["allocated_volume"] < out["capacity_cap"] - 1e-9
        if not available_mask.any():
            break

        available = out.loc[available_mask].copy()
        prob_sum = float(available["probability"].sum())

        if prob_sum <= 0:
            out.loc[available.index, "temp_weight"] = 1.0 / len(available)
        else:
            out.loc[available.index, "temp_weight"] = available["probability"] / prob_sum

        allocated_this_round = 0.0

        for idx in available.index:
            room = float(out.at[idx, "capacity_cap"] - out.at[idx, "allocated_volume"])
            add_qty = min(float(remaining * out.at[idx, "temp_weight"]), room)

            if add_qty > 0:
                out.at[idx, "allocated_volume"] += add_qty
                allocated_this_round += add_qty

        remaining -= allocated_this_round

        if allocated_this_round <= 1e-9:
            break

    # Pass 2: kalau masih ada sisa setelah semua cap habis,
    # distribusikan proporsional ke semua supplier (overflow tanpa cap)
    if remaining > 1e-9:
        prob_sum = float(out["probability"].sum())
        if prob_sum <= 0:
            out["temp_weight"] = 1.0 / max(len(out), 1)
        else:
            out["temp_weight"] = out["probability"] / prob_sum

        for idx in out.index:
            add_qty = remaining * float(out.at[idx, "temp_weight"])
            if add_qty > 1e-9:
                out.at[idx, "allocated_volume"] += add_qty

    out = out.drop(columns=["temp_weight"], errors="ignore")
    return out

def select_candidates_greedy(df: pd.DataFrame, demand_qty: float) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    work = df.sort_values(by=["probability", "quantity"], ascending=[False, False]).copy()

    selected_rows = []
    cumulative_hist_qty = 0.0
    target_qty = float(demand_qty)

    for _, row in work.iterrows():
        selected_rows.append(row)
        cumulative_hist_qty += float(row["quantity"])

        if cumulative_hist_qty >= target_qty:
            break

        if len(selected_rows) >= 3 and cumulative_hist_qty >= target_qty * 0.85:
            break

    selected = pd.DataFrame(selected_rows)

    prob_sum = float(selected["probability"].sum())
    if prob_sum == 0:
        selected["probability"] = 1.0 / len(selected)
    else:
        selected["probability"] = selected["probability"] / prob_sum

    selected["allocated_volume"] = selected["probability"] * float(demand_qty)
    return selected

def select_candidates_target_aware(
    df: pd.DataFrame,
    current_facility: str,
    query_product: str,
    demand_qty: float,
    target_total_days: Optional[int] = None,
    strategy: str = "OPTIMIZED",
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    work = df.copy()

    if "supplier" in work.columns:
        candidate_id_col = "supplier"
        cap_product = str(query_product).upper()
        if "candidate_product" not in work.columns:
            work["candidate_product"] = cap_product
    elif "estate_supplier" in work.columns:
        candidate_id_col = "estate_supplier"
        cap_product = "FFB"
    else:
        return select_candidates_greedy(work, demand_qty)

    work["probability"] = pd.to_numeric(work["probability"], errors="coerce").fillna(0.0)
    work["quantity"] = pd.to_numeric(work["quantity"], errors="coerce").fillna(0.0)

    if "selection_priority" not in work.columns:
        work["selection_priority"] = 1

    cap_mode = (
        "HISTORICAL_CONSERVATIVE" if str(strategy).upper() == "VOLUME_GREEDY"
        else "EXPANDED"
    )

    def _capacity_cap_for_row(row: pd.Series) -> float:
        row_product = str(row.get("candidate_product", cap_product)).upper().strip()

        raw_cap = get_supplier_capacity_cap(
            supplier_id=str(row[candidate_id_col]),
            facility_id=str(current_facility),
            product=row_product,
            fallback_hist_qty=float(
                row.get("actual_product_quantity", row.get("quantity", 0.0)) or 0.0
            ),
            demand_qty=float(demand_qty),
            planning_days=target_total_days,
            cap_mode=cap_mode,
        )

        if str(query_product).upper().strip() == "PKO" and row_product == "PK":
            return float(raw_cap) * get_conversion_ratio("PKO")

        return float(raw_cap)

    work["capacity_cap"] = work.apply(_capacity_cap_for_row, axis=1)

    work["proxy_allocated_qty"] = work["quantity"].apply(
        lambda q: min(float(q or 0.0), float(demand_qty))
    )

    def _estimate_proxy_days(row: pd.Series) -> int:
        supplier_id = str(row[candidate_id_col])
        row_product = str(row.get("candidate_product", cap_product)).upper().strip()

        proxy_qty = float(row["proxy_allocated_qty"])

        actual_proxy_qty = convert_allocation_to_candidate_qty(
            allocation_qty=proxy_qty,
            query_product=str(query_product).upper().strip(),
            candidate_product=row_product,
        )

        return int(
            compute_edge_estimated_days(
                supplier_id=supplier_id,
                facility_id=str(current_facility),
                product=row_product,
                allocated_qty=float(actual_proxy_qty),
            )["estimated_days"]
        )

    work["edge_days_proxy"] = work.apply(_estimate_proxy_days, axis=1)

    if strategy == "OPTIMIZED":
        dynamic_min_share = 0.005

        fast_weight = 1.0 / pd.to_numeric(
            work["edge_days_proxy"],
            errors="coerce"
        ).fillna(1.0).clip(lower=1.0)

        fast_weight_sum = float(fast_weight.sum())
        if fast_weight_sum > 0:
            work["probability"] = fast_weight / fast_weight_sum

        work = work.sort_values(
            by=["selection_priority", "probability", "edge_days_proxy", "quantity"],
            ascending=[True, False, True, False],
        ).copy()

    elif strategy == "VOLUME_GREEDY":
        dynamic_min_share = get_dynamic_min_allocated_share(demand_qty)

        if target_total_days and target_total_days > 0:
            work = work.sort_values(
                by=["selection_priority", "edge_days_proxy", "probability", "quantity"],
                ascending=[True, True, False, False],
            ).copy()
        else:
            work = work.sort_values(
                by=["selection_priority", "probability", "quantity"],
                ascending=[True, False, False],
            ).copy()


    else:
        dynamic_min_share = get_dynamic_min_allocated_share(demand_qty)

        work = work.sort_values(
            by=["selection_priority", "probability", "quantity"],
            ascending=[True, False, False],
        ).copy()

    work = allocate_with_capacity_caps(
        work=work,
        demand_qty=float(demand_qty),
    )

    min_allocated_qty = float(demand_qty) * dynamic_min_share
    filtered = work[work["allocated_volume"] >= min_allocated_qty].copy()

    if filtered.empty:
        filtered = work.sort_values(
            by=["probability", "quantity"],
            ascending=[False, False],
        ).head(1).copy()
    
    filtered["allocated_volume"] = 0.0

    work = allocate_with_capacity_caps(
        work=filtered,
        demand_qty=float(demand_qty),
    )

    if work.empty:
        return work

    allocated_sum = float(work["allocated_volume"].sum())
    if allocated_sum > 0:
        work["probability"] = work["allocated_volume"] / allocated_sum
    else:
        work["probability"] = 1.0 / len(work)


    logger.debug(
        "DEMAND: %.2f | ALLOCATED: %.2f | CAPACITY: %.2f",
        demand_qty,
        work["allocated_volume"].sum(),
        work["capacity_cap"].sum(),
    )
    return work

def is_mill_supplier(supplier_id: str, supplier_type: str) -> bool:
    return str(supplier_id) in _mill_ids() or str(supplier_type).upper() == "MILL"

def get_ffb_upstream_candidates(
    mill_id: str,
    mill_output_product: str,
    spec: str,
    blacklist: Set[str],
    warnings: Optional[List[Dict[str, str]]] = None,
    collect_warnings: bool = True,
) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    warnings = warnings or []
    ffb_flow = _ffb_flow()
    candidates = ffb_flow[ffb_flow["mill"].astype(str) == str(mill_id)].copy()

    if candidates.empty:
        return candidates, warnings

    if blacklist:
        blocked = candidates[candidates["supplier"].astype(str).isin(blacklist)].copy()
        if collect_warnings and not blocked.empty:
            for _, row in blocked.iterrows():
                sid = str(row["supplier"])
                warnings.append({
                    "supplier_id": sid,
                    "supplier_name": _facility_name_lookup().get(sid, sid),
                })
        candidates = candidates[~candidates["supplier"].astype(str).isin(blacklist)].copy()

    if candidates.empty:
        return candidates, warnings

    candidates["mill_spec"] = candidates["mill_spec"].fillna("").astype(str).apply(normalize_spec_value)
    candidates["supplier_spec"] = candidates["supplier_spec"].fillna("").astype(str).apply(normalize_spec_value)
    candidates["supplier_type"] = candidates["supplier_type"].fillna("").astype(str).apply(normalize_facility_type)

    if str(spec).upper() == "EUDR":
        candidates = candidates[
            (candidates["mill_spec"] == "EUDR") &
            (candidates["supplier_spec"] == "EUDR")
        ].copy()

    if candidates.empty:
        return candidates, warnings

    total_qty = float(candidates["quantity"].sum())
    candidates["probability"] = 0.0 if total_qty == 0 else candidates["quantity"] / total_qty
    candidates["mill_output_product"] = str(mill_output_product).upper()

    return candidates, warnings

def get_cpo_tolling_candidates(
    receiver_mill_id: str,
    spec: str,
    blacklist: Set[str],
    enable_tolling: bool = False,
    warnings: Optional[List[Dict[str, str]]] = None,
    collect_warnings: bool = True,
) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    warnings = warnings or []
    tolling_flow = _tolling_flow()

    if not ALLOW_CPO_TOLLING or not enable_tolling:
        return pd.DataFrame(), warnings

    if tolling_flow.empty:
        return tolling_flow.copy(), warnings

    receiver_mill_id = str(receiver_mill_id).strip()

    candidates = tolling_flow[
        (tolling_flow["facility"].astype(str).str.strip() == receiver_mill_id) &
        (tolling_flow["product"].astype(str).str.upper() == "CPO")
    ].copy()

    if candidates.empty:
        return candidates, warnings

    if blacklist:
        blocked = candidates[candidates["supplier"].astype(str).isin(blacklist)].copy()

        if collect_warnings and not blocked.empty:
            for _, row in blocked.iterrows():
                sid = str(row["supplier"])
                warnings.append({
                    "supplier_id": sid,
                    "supplier_name": _facility_name_lookup().get(sid, sid),
                })

        candidates = candidates[
            ~candidates["supplier"].astype(str).isin(blacklist)
        ].copy()

    if candidates.empty:
        return candidates, warnings

    candidates["supplier_type"] = (
        candidates["supplier_type"]
        .fillna("")
        .astype(str)
        .apply(normalize_facility_type)
    )

    candidates["supplier_spec"] = (
        candidates["supplier_spec"]
        .fillna("")
        .astype(str)
        .apply(normalize_spec_value)
    )

    if str(spec).upper() == "EUDR":
        candidates = candidates[
            candidates["supplier_spec"].eq("EUDR")
        ].copy()

        if candidates.empty:
            return candidates, warnings

    total_qty = float(candidates["quantity"].sum())
    candidates["probability"] = 0.0 if total_qty == 0 else candidates["quantity"] / total_qty
    candidates["upstream_route_kind"] = "TOLLING_CPO_961_TO_601"

    return candidates, warnings

def has_valid_path_from_facility(
    current_product: str,
    current_facility: str,
    spec: str,
    blacklist: Set[str],
    visited: Set[Tuple[str, str]],
    enable_tolling: bool = False,
    tolling_already_used: bool = False,
) -> bool:
    key = (str(current_facility), str(current_product).upper())
    if key in visited:
        return False

    query_product, _, df, _ = get_candidate_df_with_fallback(
        current_facility=current_facility,
        current_product=current_product,
        quantity=1.0,
        spec=spec,
        blacklist=blacklist,
        warnings=[],
        collect_warnings=False,
        allow_fallback=allow_fallback_for_facility(current_facility),
    )

    if not query_product or df.empty:
        return False

    for row in df.to_dict(orient="records"):
        ok = has_valid_path_through_supplier(
            current_product=query_product,
            supplier_id=str(row["supplier"]),
            supplier_type=str(row.get("supplier_type", "")).upper(),
            supplier_spec=str(row.get("supplier_spec", "")).upper(),
            spec=spec,
            blacklist=blacklist,
            visited=visited | {key},
            enable_tolling=enable_tolling,
            tolling_already_used=tolling_already_used,
        )
        if ok:
            return True

    return False

def has_valid_path_through_supplier(
    current_product: str,
    supplier_id: str,
    supplier_type: str,
    supplier_spec: str,
    spec: str,
    blacklist: Set[str],
    visited: Set[Tuple[str, str]],
    enable_tolling: bool = False,
    tolling_already_used: bool = False,
) -> bool:
    supplier_id = str(supplier_id)
    supplier_type = str(supplier_type).upper()
    requested_spec = str(spec).upper()

    if supplier_type == VENDOR_TYPE:
        if not ALLOW_TERMINAL_VENDOR:
            return False

        if requested_spec != "EUDR":
            return True

        return normalize_spec_value(supplier_spec) == "EUDR"

    if is_mill_supplier(supplier_id, supplier_type):
        if (
            enable_tolling
            and ALLOW_CPO_TOLLING
            and not tolling_already_used
            and str(current_product).upper().strip() == "CPO"
        ):
            tolling_candidates, _ = get_cpo_tolling_candidates(
                receiver_mill_id=supplier_id,
                spec=spec,
                blacklist=blacklist,
                enable_tolling=enable_tolling,
                warnings=[],
                collect_warnings=False,
            )

            for _, tolling_row in tolling_candidates.iterrows():
                processor_mill_id = str(tolling_row["supplier"])

                ffb_candidates, _ = get_ffb_upstream_candidates(
                    mill_id=processor_mill_id,
                    mill_output_product="CPO",
                    spec=spec,
                    blacklist=blacklist,
                    warnings=[],
                    collect_warnings=False,
                )

                if not ffb_candidates.empty:
                    return True

        estates, _ = get_ffb_upstream_candidates(
            mill_id=supplier_id,
            mill_output_product=current_product,
            spec=spec,
            blacklist=blacklist,
            warnings=[],
            collect_warnings=False,
        )

        if not estates.empty:
            return True

        if ALLOW_TERMINAL_MILL and requested_spec != "EUDR":
            return True

        return False

    return has_valid_path_from_facility(
        current_product=current_product,
        current_facility=supplier_id,
        spec=spec,
        blacklist=blacklist,
        visited=visited,
        enable_tolling=enable_tolling,
        tolling_already_used=tolling_already_used,
    )

def build_node(row: pd.Series, product: str, quantity: float) -> Dict[str, Any]:
    supplier_id = str(row.get("supplier"))
    supplier_name = row.get("supplier_name")
    supplier_type = row.get("supplier_type")

    mapped = map_supplier_output_identity(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        supplier_type=supplier_type,
    )

    node = {
        "supplier_id": mapped["supplier_id"],
        "supplier_name": mapped["supplier_name"],
        "supplier_type": mapped["supplier_type"],
        "product": str(product).upper(),
        "quantity": round(float(quantity), 2),
    }

    if "raw_vendor_ids" in row and row.get("raw_vendor_ids"):
        node["raw_vendor_ids"] = row.get("raw_vendor_ids")

    if "raw_vendor_names" in row and row.get("raw_vendor_names"):
        node["raw_vendor_names"] = row.get("raw_vendor_names")

    if "vendor_resolution_rules" in row and row.get("vendor_resolution_rules"):
        node["vendor_resolution_rules"] = row.get("vendor_resolution_rules")

    if mapped.get("alias_merged"):
        node["alias_merged"] = True
        node["raw_supplier_id"] = mapped.get("raw_supplier_id")
        node["raw_supplier_name"] = mapped.get("raw_supplier_name")
        node["alias_mapping_type"] = mapped.get("alias_mapping_type")

    if "supplier_source_kind" in row.index:
        node["supplier_source_kind"] = str(row.get("supplier_source_kind", ""))

    return node

def dedupe_selected_ffb_suppliers(selected_ffb_suppliers: pd.DataFrame) -> pd.DataFrame:
    if selected_ffb_suppliers.empty:
        return selected_ffb_suppliers.copy()

    df = selected_ffb_suppliers.copy()

    df["allocated_volume"] = pd.to_numeric(
        df.get("allocated_volume", 0.0),
        errors="coerce"
    ).fillna(0.0)

    df["quantity"] = pd.to_numeric(
        df.get("quantity", 0.0),
        errors="coerce"
    ).fillna(0.0)

    if "supplier_name" not in df.columns:
        df["supplier_name"] = df["supplier"].astype(str).map(
            lambda x: _facility_name_lookup().get(str(x), str(x))
        )

    if "supplier_type" not in df.columns:
        df["supplier_type"] = df["supplier"].astype(str).map(
            lambda x: get_facility_type_safe(str(x)) or "UNKNOWN"
        )

    df["supplier_display_key"] = np.where(
        df["supplier_name"].fillna("").astype(str).str.strip() != "",
        df["supplier_name"].fillna("").astype(str),
        df["supplier"].fillna("").astype(str),
    )

    df["supplier_display_key"] = df["supplier_display_key"].apply(normalize_display_key)

    agg_dict = {
        "supplier": "first",
        "supplier_name": "first",
        "supplier_type": "first",
        "quantity": "sum",
        "allocated_volume": "sum",
    }

    for col in [
        "supplier_spec",
        "supplier_source_kind",
        "probability",
        "mill",
        "mill_name",
        "mill_type",
        "mill_spec",
        "mill_output_product",
        "raw_estate_receivers",
        "raw_vendor_receivers",
        "ffb_resolution_rules",
        "capacity_cap",
        "edge_days_proxy",
        "selection_priority",
    ]:
        if col in df.columns and col not in agg_dict:
            agg_dict[col] = "first"

    grouped = (
        df.groupby("supplier_display_key", as_index=False, dropna=False)
        .agg(agg_dict)
        .drop(columns=["supplier_display_key"], errors="ignore")
    )

    allocated_sum = float(grouped["allocated_volume"].sum())

    if allocated_sum > 0:
        grouped["probability"] = grouped["allocated_volume"] / allocated_sum
    else:
        grouped["probability"] = 1.0 / max(len(grouped), 1)

    return grouped

def trace_paths_from_facility(
    current_product: str,
    current_facility: str,
    quantity: float,
    spec: str = "ALL",
    blacklist: Optional[Set[str]] = None,
    warnings: Optional[List[Dict[str, str]]] = None,
    visited: Optional[Set[Tuple[str, str]]] = None,
    trace_meta: Optional[Dict[str, bool]] = None,
    target_total_days: Optional[int] = None,
    strategy: str = "OPTIMIZED",
    enable_tolling: bool = False,
    tolling_already_used: bool = False,
) -> Tuple[List[List[Dict[str, Any]]], List[Dict[str, str]], Dict[str, bool]]:
    warnings = warnings or []
    visited = visited or set()
    trace_meta = trace_meta or {
        "invalid_paths_removed": False,
        "volume_redistributed": False,
        "terminal_vendor_used": False,
        "terminal_mill_used": False,
        "tolling_used": False,
    }

    key = (str(current_facility), str(current_product).upper())
    if key in visited:
        return [], warnings, trace_meta

    query_product, query_quantity, df, warnings = get_candidate_df_with_fallback(
        current_facility=current_facility,
        current_product=current_product,
        quantity=quantity,
        spec=spec,
        blacklist=blacklist or set(),
        warnings=warnings,
        collect_warnings=True,
        allow_fallback=allow_fallback_for_facility(current_facility),
    )

    if not query_product or df.empty:
        return [], warnings, trace_meta

    df = df.copy()

# ✅ SESUDAH — tambahkan _validity_cache sebagai parameter fungsi
    _cache = getattr(trace_paths_from_facility, "_validity_cache", {})

    def _check_validity(r):
        sid = str(r["supplier"])
        stype = str(r.get("supplier_type", "")).upper()
        sspec = str(r.get("supplier_spec", "")).upper()
        cache_key = (query_product, sid, stype, sspec, spec, frozenset(blacklist or set()), enable_tolling, tolling_already_used)
        if cache_key not in _cache:
            _cache[cache_key] = has_valid_path_through_supplier(
                current_product=query_product,
                supplier_id=sid,
                supplier_type=stype,
                supplier_spec=sspec,
                spec=spec,
                blacklist=blacklist or set(),
                visited=visited | {key},
                enable_tolling=enable_tolling,
                tolling_already_used=tolling_already_used,
            )
        return _cache[cache_key]

    df["is_valid_branch"] = df.apply(_check_validity, axis=1)

    invalid_df = df[~df["is_valid_branch"]].copy()
    valid_df = df[df["is_valid_branch"]].copy()

    if not invalid_df.empty:
        trace_meta["invalid_paths_removed"] = True

    if valid_df.empty:
        return [], warnings, trace_meta

    valid_df = valid_df.copy()

    valid_df["force_keep_terminal"] = valid_df.apply(
        lambda r: should_force_keep_terminal_candidate(
            supplier_id=str(r["supplier"]),
            supplier_type=str(r.get("supplier_type", "")).upper(),
            supplier_spec=str(r.get("supplier_spec", "")).upper(),
            current_product=query_product,
            spec=spec,
            blacklist=blacklist or set(),
            enable_tolling=enable_tolling,
            tolling_already_used=tolling_already_used,
        ),
        axis=1,
    )

    force_keep_df = valid_df[valid_df["force_keep_terminal"]].copy()
    normal_df = valid_df[~valid_df["force_keep_terminal"]].copy()

    ranked_selected = pd.DataFrame()
    if not normal_df.empty:
        ranked_selected = select_candidates_target_aware(
            normal_df,
            current_facility=current_facility,
            query_product=query_product,
            demand_qty=query_quantity,
            target_total_days=target_total_days,
            strategy=strategy,
        )

    selected_parts = []

    if not ranked_selected.empty:
        selected_parts.append(ranked_selected)

    if not force_keep_df.empty:
        force_keep_df = force_keep_df.copy()
        if "allocated_volume" not in force_keep_df.columns:
            force_keep_df["allocated_volume"] = (
                pd.to_numeric(force_keep_df["probability"], errors="coerce").fillna(0.0)
                * float(query_quantity)
            )
        selected_parts.append(force_keep_df)

    if not selected_parts:
        return [], warnings, trace_meta

    selected = pd.concat(selected_parts, ignore_index=True)
    selected = selected.drop_duplicates(subset=["supplier"], keep="first").copy()

    selected["allocated_volume"] = pd.to_numeric(
        selected.get("allocated_volume", 0.0),
        errors="coerce"
    ).fillna(0.0)

    selected = selected[selected["allocated_volume"] > 1e-9].copy()

    selected_total_alloc = float(selected["allocated_volume"].sum())

    if selected_total_alloc > float(query_quantity) + 1e-6:
        # Scale DOWN kalau alokasi melebihi demand
        scale_factor = float(query_quantity) / selected_total_alloc
        selected["allocated_volume"] = selected["allocated_volume"] * scale_factor
        trace_meta["volume_redistributed"] = True
    elif selected_total_alloc > 1e-9 and selected_total_alloc < float(query_quantity) - 1e-6:
        # Scale UP kalau alokasi kurang dari demand (misal sebagian mill tidak punya subpaths)
        scale_factor = float(query_quantity) / selected_total_alloc
        selected["allocated_volume"] = selected["allocated_volume"] * scale_factor
        trace_meta["volume_redistributed"] = True

    if selected.empty:
        return [], warnings, trace_meta

    allocated_sum = float(selected["allocated_volume"].sum())
    if allocated_sum > 0:
        selected["probability"] = selected["allocated_volume"] / allocated_sum
    else:
        selected["probability"] = 1.0 / max(len(selected), 1)

    if len(selected) < len(valid_df):
        trace_meta["volume_redistributed"] = True

    all_paths: List[List[Dict[str, Any]]] = []
    requested_spec = str(spec).upper()

    tolling_used_for_current_parent = False

    if (
        enable_tolling
        and ALLOW_CPO_TOLLING
        and not tolling_already_used
        and str(query_product).upper().strip() == "CPO"
    ):
        tolling_receiver_rows = []

        for idx, candidate_row in selected.iterrows():
            candidate_supplier_id = str(candidate_row["supplier"])
            candidate_supplier_type = str(
                candidate_row.get("supplier_type", "")
            ).upper()

            if not is_mill_supplier(candidate_supplier_id, candidate_supplier_type):
                continue

            tolling_candidates, _ = get_cpo_tolling_candidates(
                receiver_mill_id=candidate_supplier_id,
                spec=spec,
                blacklist=blacklist or set(),
                enable_tolling=enable_tolling,
                warnings=[],
                collect_warnings=False,
            )

            if tolling_candidates.empty:
                continue

            has_valid_tolling = False

            for _, tolling_row in tolling_candidates.iterrows():
                processor_mill_id = str(tolling_row["supplier"])

                if processor_mill_id == candidate_supplier_id:
                    continue

                if (processor_mill_id, "CPO") in visited:
                    continue

                ffb_candidates, _ = get_ffb_upstream_candidates(
                    mill_id=processor_mill_id,
                    mill_output_product="CPO",
                    spec=spec,
                    blacklist=blacklist or set(),
                    warnings=[],
                    collect_warnings=False,
                )

                if not ffb_candidates.empty:
                    ffb_candidates = ffb_candidates[
                        ~ffb_candidates["supplier_type"]
                        .fillna("")
                        .astype(str)
                        .str.upper()
                        .eq("MILL")
                    ].copy()

                if not ffb_candidates.empty:
                    has_valid_tolling = True
                    break

            if has_valid_tolling:
                score_probability = float(candidate_row.get("probability", 0.0) or 0.0)
                score_quantity = float(candidate_row.get("quantity", 0.0) or 0.0)
                score_allocated = float(candidate_row.get("allocated_volume", 0.0) or 0.0)

                tolling_receiver_rows.append(
                    (idx, score_probability, score_quantity, score_allocated)
                )

        if tolling_receiver_rows:
            best_idx = sorted(
                tolling_receiver_rows,
                key=lambda x: (x[1], x[2], x[3]),
                reverse=True,
            )[0][0]


    for _, row in selected.iterrows():
        supplier_id = str(row["supplier"])
        supplier_type = str(row.get("supplier_type", "")).upper()

        candidate_product = str(
            row.get("candidate_product", query_product)
        ).upper().strip()

        allocated_basis_qty = float(row["allocated_volume"])

        allocated = convert_allocation_to_candidate_qty(
            allocation_qty=allocated_basis_qty,
            query_product=query_product,
            candidate_product=candidate_product,
        )

        if supplier_type == VENDOR_TYPE:
            vendor_node = build_node(row, candidate_product, allocated)
            vendor_node["upstream_route_kind"] = str(row.get("upstream_route_kind", ""))
            vendor_node["allocation_basis_product"] = str(query_product).upper()
            vendor_node["allocation_basis_quantity"] = round(float(allocated_basis_qty), 2)

            trace_meta["terminal_vendor_used"] = True
            all_paths.append([vendor_node])
            continue

        if is_mill_supplier(supplier_id, supplier_type):
            created_paths_for_mill = False
            tolling_used_qty = 0.0

            if (
                enable_tolling
                and ALLOW_CPO_TOLLING
                and not tolling_already_used
                and not tolling_used_for_current_parent
                and candidate_product == "CPO"
            ):
                tolling_candidates, warnings = get_cpo_tolling_candidates(
                    receiver_mill_id=supplier_id,
                    spec=spec,
                    blacklist=blacklist or set(),
                    enable_tolling=enable_tolling,
                    warnings=warnings,
                    collect_warnings=True,
                )

                if not tolling_candidates.empty:
                    selected_tolling = select_candidates_target_aware(
                        tolling_candidates,
                        current_facility=supplier_id,
                        query_product="CPO",
                        demand_qty=allocated,
                        target_total_days=target_total_days,
                        strategy=strategy,
                    )

                    selected_tolling = selected_tolling[
                        pd.to_numeric(
                            selected_tolling.get("allocated_volume", 0.0),
                            errors="coerce"
                        ).fillna(0.0) > 1e-9
                    ].copy()

                    if not selected_tolling.empty:
                        selected_tolling = selected_tolling.sort_values(
                            by=["probability", "quantity"],
                            ascending=[False, False],
                        ).head(1).copy()

                    for _, processor_row in selected_tolling.iterrows():
                        processor_mill_id = str(processor_row["supplier"])
                        processor_cpo_qty = float(
                            processor_row.get("allocated_volume", 0.0) or 0.0
                        )

                        if processor_cpo_qty <= 1e-9:
                            continue

                        if processor_mill_id == supplier_id:
                            continue

                        if (processor_mill_id, "CPO") in visited:
                            continue

                        ffb_qty = convert_product_quantity_along_path(
                            from_product="CPO",
                            to_product="FFB",
                            qty=processor_cpo_qty,
                        )

                        ffb_candidates, warnings = get_ffb_upstream_candidates(
                            mill_id=processor_mill_id,
                            mill_output_product="CPO",
                            spec=spec,
                            blacklist=blacklist or set(),
                            warnings=warnings,
                            collect_warnings=True,
                        )

                        if not ffb_candidates.empty:
                            ffb_candidates = ffb_candidates[
                                ~ffb_candidates["supplier_type"]
                                .fillna("")
                                .astype(str)
                                .str.upper()
                                .eq("MILL")
                            ].copy()

                        if ffb_candidates.empty:
                            continue

                        selected_ffb_suppliers = select_candidates_target_aware(
                            ffb_candidates,
                            current_facility=processor_mill_id,
                            query_product="FFB",
                            demand_qty=ffb_qty,
                            target_total_days=target_total_days,
                            strategy=strategy,
                        )

                        selected_ffb_suppliers = selected_ffb_suppliers[
                            pd.to_numeric(
                                selected_ffb_suppliers.get("allocated_volume", 0.0),
                                errors="coerce"
                            ).fillna(0.0) > 1e-9
                        ].copy()

                        selected_ffb_suppliers = dedupe_selected_ffb_suppliers(
                            selected_ffb_suppliers
                        )

                        if selected_ffb_suppliers.empty:
                            continue

                        total_ffb = float(
                            selected_ffb_suppliers["allocated_volume"].sum()
                        ) or 1.0

                        for _, up in selected_ffb_suppliers.iterrows():
                            up_ffb_qty = float(up.get("allocated_volume", 0.0) or 0.0)

                            if up_ffb_qty <= 1e-9:
                                continue

                            share = up_ffb_qty / total_ffb

                            receiver_branch_qty = processor_cpo_qty * share
                            processor_branch_qty = processor_cpo_qty * share
                            receiver_branch_basis_qty = allocated_basis_qty * share

                            receiver_node = build_node(row, "CPO", receiver_branch_qty)
                            receiver_node["upstream_route_kind"] = "TOLLING_RECEIVER_STORAGE_MILL"
                            receiver_node["tolling_used"] = True
                            receiver_node["tolling_role"] = "RECEIVER_STORAGE_MILL"
                            receiver_node["movement_pattern"] = "961_TO_601"
                            receiver_node["allocation_basis_product"] = str(query_product).upper()
                            receiver_node["allocation_basis_quantity"] = round(float(receiver_branch_basis_qty), 2)

                            processor_node = build_node(
                                processor_row,
                                "CPO",
                                processor_branch_qty,
                            )
                            processor_node["upstream_route_kind"] = "TOLLING_PROCESSING_MILL"
                            processor_node["tolling_used"] = True
                            processor_node["tolling_role"] = "PROCESSING_MILL"
                            processor_node["movement_pattern"] = "961_TO_601"
                            processor_node["allocation_basis_product"] = "CPO"
                            processor_node["allocation_basis_quantity"] = round(float(processor_branch_qty), 2)

                            upstream_node = build_node(up, "FFB", up_ffb_qty)
                            upstream_node["upstream_route_kind"] = "TOLLING_FFB_ORIGIN"

                            all_paths.append([
                                receiver_node,
                                processor_node,
                                upstream_node,
                            ])

                        tolling_used_qty += processor_cpo_qty
                        created_paths_for_mill = True
                        trace_meta["tolling_used"] = True
                        tolling_used_for_current_parent = True
                        break

            if created_paths_for_mill and tolling_used_qty > 1e-9:
                continue

            remaining_qty = max(float(allocated) - float(tolling_used_qty), 0.0)

            if remaining_qty <= 1e-9:
                continue

            ffb_qty = convert_product_quantity_along_path(
                from_product=candidate_product,
                to_product="FFB",
                qty=remaining_qty,
            )

            ffb_candidates, warnings = get_ffb_upstream_candidates(
                mill_id=supplier_id,
                mill_output_product=candidate_product,
                spec=spec,
                blacklist=blacklist or set(),
                warnings=warnings,
                collect_warnings=True,
            )

            if not ffb_candidates.empty:
                selected_ffb_suppliers = select_candidates_target_aware(
                    ffb_candidates,
                    current_facility=supplier_id,
                    query_product="FFB",
                    demand_qty=ffb_qty,
                    target_total_days=target_total_days,
                    strategy=strategy,
                )

                selected_ffb_suppliers = selected_ffb_suppliers[
                    pd.to_numeric(
                        selected_ffb_suppliers.get("allocated_volume", 0.0),
                        errors="coerce"
                    ).fillna(0.0) > 1e-9
                ].copy()

                selected_ffb_suppliers = dedupe_selected_ffb_suppliers(
                    selected_ffb_suppliers
                )

                if not selected_ffb_suppliers.empty:
                    total_ffb = float(
                        selected_ffb_suppliers["allocated_volume"].sum()
                    ) or 1.0

                    for _, up in selected_ffb_suppliers.iterrows():
                        up_ffb_qty = float(up.get("allocated_volume", 0.0) or 0.0)

                        if up_ffb_qty <= 1e-9:
                            continue

                        share = up_ffb_qty / total_ffb
                        mill_branch_qty = remaining_qty * share
                        mill_branch_basis_qty = allocated_basis_qty * share

                        mill_node = build_node(row, candidate_product, mill_branch_qty)
                        mill_node["ffb_upstream_used"] = True
                        mill_node["upstream_route_kind"] = str(
                            row.get("upstream_route_kind", "FFB_CONVERSION")
                        )
                        mill_node["allocation_basis_product"] = str(query_product).upper()
                        mill_node["allocation_basis_quantity"] = round(float(mill_branch_basis_qty), 2)

                        upstream_node = build_node(up, "FFB", up_ffb_qty)
                        upstream_node["upstream_route_kind"] = "FFB_ORIGIN"

                        all_paths.append([mill_node, upstream_node])

                    continue

            if ALLOW_TERMINAL_MILL and requested_spec != "EUDR":
                mill_node = build_node(row, candidate_product, remaining_qty)
                mill_node["upstream_route_kind"] = str(row.get("upstream_route_kind", "TERMINAL_MILL"))
                mill_node["allocation_basis_product"] = str(query_product).upper()
                mill_node["allocation_basis_quantity"] = round(float(allocated_basis_qty), 2)

                trace_meta["terminal_mill_used"] = True
                all_paths.append([mill_node])
                continue

            continue

        subpaths, warnings, trace_meta = trace_paths_from_facility(
            current_product=candidate_product,
            current_facility=supplier_id,
            quantity=allocated,
            spec=spec,
            blacklist=blacklist or set(),
            warnings=warnings,
            visited=visited | {key},
            trace_meta=trace_meta,
            target_total_days=target_total_days,
            strategy=strategy,
            enable_tolling=enable_tolling,
            tolling_already_used=tolling_already_used,
        )

        if subpaths:
            child_quantities = []

            for sp in subpaths:
                if sp:
                    child_qty = float(sp[0].get("quantity", 0.0) or 0.0)
                else:
                    child_qty = 0.0

                child_quantities.append(child_qty)

            total_child_qty = float(sum(child_quantities))

            for idx, sp in enumerate(subpaths):
                if not sp:
                    continue

                if total_child_qty > 1e-9:
                    share = float(child_quantities[idx]) / total_child_qty
                else:
                    share = 1.0 / max(len(subpaths), 1)

                branch_qty = float(allocated) * share
                branch_basis_qty = float(allocated_basis_qty) * share

                node = build_node(row, candidate_product, branch_qty)
                node["upstream_route_kind"] = str(row.get("upstream_route_kind", ""))
                node["allocation_basis_product"] = str(query_product).upper()
                node["allocation_basis_quantity"] = round(float(branch_basis_qty), 2)

                all_paths.append([node] + sp)
        else:
            node = build_node(row, candidate_product, allocated)
            node["upstream_route_kind"] = str(row.get("upstream_route_kind", ""))
            node["allocation_basis_product"] = str(query_product).upper()
            node["allocation_basis_quantity"] = round(float(allocated_basis_qty), 2)

            all_paths.append([node])

    return all_paths, warnings, trace_meta
  
def trace_additional_kcp_pk_paths(
    current_facility: str,
    current_product: str,
    quantity: float,
    spec: str,
    blacklist: Set[str],
    target_total_days: Optional[int],
    strategy: str,
    enable_tolling: bool,
    trace_meta: Dict[str, bool],
) -> Tuple[List[List[Dict[str, Any]]], List[Dict[str, str]], Dict[str, bool]]:
    warnings: List[Dict[str, str]] = []

    requested_product = normalize_trace_product(current_product)

    if get_facility_type_for_trace(current_facility) != "REFINERY":
        return [], warnings, trace_meta

    if not facility_has_kcp(current_facility):
        return [], warnings, trace_meta

    if requested_product not in {"RBDPKO", "PKO"}:
        return [], warnings, trace_meta

    pk_quantity = convert_product_quantity_along_path(
        from_product=requested_product,
        to_product="PK",
        qty=quantity,
    )

    pk_df, warnings = get_upstream_candidates_df(
        current_facility=current_facility,
        query_product="PK",
        blacklist=blacklist,
        spec=spec,
        warnings=warnings,
        collect_warnings=True,
    )

    if pk_df.empty:
        return [], warnings, trace_meta

    selected_pk = select_candidates_target_aware(
        pk_df,
        current_facility=current_facility,
        query_product="PK",
        demand_qty=pk_quantity,
        target_total_days=target_total_days,
        strategy=strategy,
    )

    selected_pk = selected_pk[
        pd.to_numeric(
            selected_pk.get("allocated_volume", 0.0),
            errors="coerce"
        ).fillna(0.0) > 1e-9
    ].copy()

    if selected_pk.empty:
        return [], warnings, trace_meta

    additional_paths: List[List[Dict[str, Any]]] = []

    for _, row in selected_pk.iterrows():
        supplier_id = str(row["supplier"])
        supplier_type = str(row.get("supplier_type", "")).upper()
        allocated_pk = float(row.get("allocated_volume", 0.0) or 0.0)

        if allocated_pk <= 1e-9:
            continue

        if is_mill_supplier(supplier_id, supplier_type):
            ffb_candidates, warnings = get_ffb_upstream_candidates(
                mill_id=supplier_id,
                mill_output_product="PK",
                spec=spec,
                blacklist=blacklist,
                warnings=warnings,
                collect_warnings=True,
            )

            if not ffb_candidates.empty:
                ffb_qty = convert_product_quantity_along_path(
                    from_product="PK",
                    to_product="FFB",
                    qty=allocated_pk,
                )

                selected_ffb = select_candidates_target_aware(
                    ffb_candidates,
                    current_facility=supplier_id,
                    query_product="FFB",
                    demand_qty=ffb_qty,
                    target_total_days=target_total_days,
                    strategy=strategy,
                )

                selected_ffb = selected_ffb[
                    pd.to_numeric(
                        selected_ffb.get("allocated_volume", 0.0),
                        errors="coerce"
                    ).fillna(0.0) > 1e-9
                ].copy()

                selected_ffb = dedupe_selected_ffb_suppliers(selected_ffb)

                if not selected_ffb.empty:
                    total_ffb = float(selected_ffb["allocated_volume"].sum()) or 1.0

                    for _, up in selected_ffb.iterrows():
                        upstream_ffb_qty = float(up.get("allocated_volume", 0.0) or 0.0)

                        if upstream_ffb_qty <= 1e-9:
                            continue

                        share = upstream_ffb_qty / total_ffb
                        pk_branch_qty = allocated_pk * share
                        basis_branch_qty = float(quantity) * share

                        pk_node = build_node(row, "PK", pk_branch_qty)
                        pk_node["upstream_route_kind"] = "KCP_PK_TO_PKO_ROUTE"
                        pk_node["allocation_basis_product"] = requested_product
                        pk_node["allocation_basis_quantity"] = round(float(basis_branch_qty), 2)

                        ffb_node = build_node(up, "FFB", upstream_ffb_qty)
                        ffb_node["upstream_route_kind"] = "KCP_PK_FFB_ORIGIN"

                        additional_paths.append([pk_node, ffb_node])

                    continue

        pk_node = build_node(row, "PK", allocated_pk)
        pk_node["upstream_route_kind"] = "KCP_PK_TO_PKO_ROUTE"
        pk_node["allocation_basis_product"] = requested_product
        pk_node["allocation_basis_quantity"] = round(float(quantity), 2)

        additional_paths.append([pk_node])

    return additional_paths, warnings, trace_meta

def is_mill_eudr(mill_id: str) -> bool:
    return normalize_spec_value(get_facility_spec_safe(str(mill_id))) == "EUDR"

def is_vendor_eudr_from_row(row: pd.Series) -> bool:
    return normalize_spec_value(row.get("supplier_spec", "")) == "EUDR"

def should_force_keep_terminal_candidate(
    supplier_id: str,
    supplier_type: str,
    supplier_spec: str,
    current_product: str,
    spec: str,
    blacklist: Set[str],
    enable_tolling: bool = False,
    tolling_already_used: bool = False,
) -> bool:
    supplier_id = str(supplier_id)
    supplier_type = str(supplier_type).upper()
    requested_spec = str(spec).upper()

    if supplier_type == VENDOR_TYPE:
        return False

    if is_mill_supplier(supplier_id, supplier_type):
        if (
            enable_tolling
            and ALLOW_CPO_TOLLING
            and not tolling_already_used
            and str(current_product).upper().strip() == "CPO"
        ):
            tolling_candidates, _ = get_cpo_tolling_candidates(
                receiver_mill_id=supplier_id,
                spec=spec,
                blacklist=blacklist,
                enable_tolling=enable_tolling,
                warnings=[],
                collect_warnings=False,
            )

            for _, tolling_row in tolling_candidates.iterrows():
                processor_mill_id = str(tolling_row["supplier"])

                ffb_candidates, _ = get_ffb_upstream_candidates(
                    mill_id=processor_mill_id,
                    mill_output_product="CPO",
                    spec=spec,
                    blacklist=blacklist,
                    warnings=[],
                    collect_warnings=False,
                )

                if not ffb_candidates.empty:
                    return False

        estates, _ = get_ffb_upstream_candidates(
            mill_id=supplier_id,
            mill_output_product=current_product,
            spec=spec,
            blacklist=blacklist,
            warnings=[],
            collect_warnings=False,
        )

        if estates.empty:
            if requested_spec != "EUDR":
                return True
            return is_mill_eudr(supplier_id)

    return False

def enrich_paths_with_forecast(
    paths: List[List[Dict[str, Any]]],
    root_receiver_id: str,
    queue_state: Optional[Dict[str, Dict[str, float]]] = None,
    start_date: Optional[pd.Timestamp] = None,
    enable_queue_scheduling: bool = False,
) -> Tuple[List[List[Dict[str, Any]]], List[Dict[str, Any]], int, List[Dict[str, Any]], Optional[str]]:
    enriched_paths: List[List[Dict[str, Any]]] = []
    path_summaries: List[Dict[str, Any]] = []

    for idx, path in enumerate(paths, start=1):
        if not path:
            continue

        receiver_id = str(root_receiver_id)
        enriched_nodes: List[Dict[str, Any]] = []

        for node in path:
            supplier_id = str(node["supplier_id"])
            product = str(node["product"]).upper()
            qty = float(node["quantity"])

            forecast = compute_edge_estimated_days(
                supplier_id=supplier_id,
                facility_id=receiver_id,
                product=product,
                allocated_qty=qty,
            )

            enriched_node = {
                **node,
                "receiver_id": receiver_id,
                "lead_time_days": forecast["lead_time_days"],
                "throughput_tpd": forecast["throughput_tpd"],
                "flow_days": forecast["flow_days"],
                "estimated_days": forecast["estimated_days"],
                "estimated_days_raw": forecast.get("estimated_days_raw", forecast["estimated_days"]),
                "target_days": forecast.get("target_days", FORECAST_TARGET_DAYS),
                "forecast_source": forecast["forecast_source"],
                "forecast_match_level": forecast["forecast_match_level"],
            }
            enriched_nodes.append(enriched_node)
            receiver_id = supplier_id

        enriched_paths.append(enriched_nodes)
        path_total_days = int(sum(int(n.get("estimated_days", 0) or 0) for n in enriched_nodes))
        path_summaries.append({
            "path_id": idx,
            "path_estimated_days": path_total_days,
            "path_volume": round(float(path[0]["quantity"]) if path else 0.0, 2),
        })

    batch_completion_date = None

    if enable_queue_scheduling:
        if queue_state is None:
            queue_state = {}

        if start_date is None:
            start_date = get_current_date()

        enriched_paths, total_estimated_days = apply_queue_scheduling_to_paths(
            enriched_paths=enriched_paths,
            queue_state=queue_state,
            start_date=start_date,
        )

        batch_completion_date = add_days_to_date(start_date, total_estimated_days)

        level_day_breakdown = [
            {
                "level": 0,
                "max_estimated_days": int(total_estimated_days),
                "basis": "queue_finish_day",
            }
        ]
    else:
        total_estimated_days, level_day_breakdown = compute_total_estimated_days_by_level(enriched_paths)

    return enriched_paths, path_summaries, int(total_estimated_days), level_day_breakdown, batch_completion_date

def flatten_paths_to_tree(paths: List[List[Dict[str, Any]]], root_receiver_id: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for path in paths:
        receiver_id = str(root_receiver_id)
        for level, node in enumerate(path):
            rows.append({
                "level": level,
                "supplier_id": str(node["supplier_id"]),
                "supplier_name": str(node["supplier_name"]),
                "supplier_type": str(node["supplier_type"]).upper(),
                "supplier_source_kind": str(node.get("supplier_source_kind", "")),
                "receiver_id": str(node.get("receiver_id", receiver_id)),
                "product": str(node["product"]).upper(),
                "quantity": round(float(node["quantity"]), 2),
                "allocation_basis_product": str(
                    node.get("allocation_basis_product", node.get("product", ""))
                ).upper(),
                "allocation_basis_quantity": round(
                    float(node.get("allocation_basis_quantity", node.get("quantity", 0.0)) or 0.0),
                    2
                ),
                "throughput_tpd": round(float(node.get("throughput_tpd", 0.0) or 0.0), 2),
                "flow_days": round(float(node.get("flow_days", 0.0) or 0.0), 2),
                "estimated_days": int(node.get("estimated_days", 0) or 0),
                "target_days": int(node.get("target_days", FORECAST_TARGET_DAYS) or FORECAST_TARGET_DAYS),
                "forecast_source": str(node.get("forecast_source", "")),
                "forecast_match_level": str(node.get("forecast_match_level", "")),
                "raw_vendor_ids": node.get("raw_vendor_ids", []),
                "raw_vendor_names": node.get("raw_vendor_names", []),
                "vendor_resolution_rules": node.get("vendor_resolution_rules", []),
                "upstream_route_kind": str(node.get("upstream_route_kind", "")),
                "tolling_used": bool(node.get("tolling_used", False)),
                "tolling_role": str(node.get("tolling_role", "")),
                "movement_pattern": str(node.get("movement_pattern", "")),
                "queue_key": str(node.get("queue_key", "")),
                "queue_cumulative_qty_before": round(float(node.get("queue_cumulative_qty_before", 0.0) or 0.0), 2),
                "queue_cumulative_qty_after": round(float(node.get("queue_cumulative_qty_after", 0.0) or 0.0), 2),
                "queue_throughput_tpd": round(float(node.get("queue_throughput_tpd", 0.0) or 0.0), 2),
                "queue_start_day_raw": round(float(node.get("queue_start_day_raw", 0.0) or 0.0), 4),
                "queue_finish_day_raw": round(float(node.get("queue_finish_day_raw", 0.0) or 0.0), 4),
                "queue_start_day": int(node.get("queue_start_day", 0) or 0),
                "queue_finish_day": int(node.get("queue_finish_day", node.get("estimated_days", 0)) or 0),
                "start_date": node.get("start_date"),
                "arrival_date": node.get("arrival_date"),
                "queue_enabled": bool(node.get("queue_enabled", False)),
            })
            receiver_id = str(node["supplier_id"])

    if not rows:
        return rows
    
    df = pd.DataFrame(rows)

    def get_receiver_display_name(receiver_id: Any) -> str:
        rid = str(receiver_id if receiver_id is not None else "").strip()
        return str(_facility_name_lookup().get(rid, rid)).strip()

    df["receiver_name"] = df["receiver_id"].apply(get_receiver_display_name)

    df["receiver_display_key"] = df["receiver_name"].apply(normalize_display_key)

    df["supplier_name_key"] = df["supplier_name"].apply(normalize_display_key)

    df["product_key"] = (
        df["product"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df["supplier_display_key"] = np.where(
        df["supplier_name_key"].astype(str).str.strip() != "",
        df["supplier_name_key"],
        df["supplier_id"].astype(str).apply(normalize_display_key),
    )

    grouped = (
        df.groupby(
            [
                "receiver_display_key",
                "supplier_display_key",
                "product_key",
            ],
            as_index=False,
            dropna=False,
        )
        .agg({
            "level": "min",

            "receiver_id": "first",
            "receiver_name": "first",

            "supplier_id": "first",
            "supplier_name": "first",
            "supplier_type": "first",
            "supplier_source_kind": "first",
            "product": "first",

            "quantity": "sum",
            "allocation_basis_product": "first",
            "allocation_basis_quantity": "sum",
            "throughput_tpd": "max",
            "flow_days": "max",
            "estimated_days": "max",
            "target_days": "max",
            "forecast_source": "first",
            "forecast_match_level": "first",

            "raw_vendor_ids": "first",
            "raw_vendor_names": "first",
            "vendor_resolution_rules": "first",

            "upstream_route_kind": "first",
            "tolling_used": "max",
            "tolling_role": "first",
            "movement_pattern": "first",

            "queue_key": "first",
            "queue_cumulative_qty_before": "min",
            "queue_cumulative_qty_after": "max",
            "queue_throughput_tpd": "max",
            "queue_start_day_raw": "min",
            "queue_finish_day_raw": "max",
            "queue_start_day": "min",
            "queue_finish_day": "max",
            "start_date": "min",
            "arrival_date": "max",
            "queue_enabled": "max",
        })
        .drop(
            columns=[
                "receiver_display_key",
                "supplier_display_key",
                "product_key",
            ],
            errors="ignore",
        )
        .sort_values(by=["level", "receiver_name", "supplier_name"])
    )

    grouped["quantity"] = pd.to_numeric(
        grouped["quantity"],
        errors="coerce"
    ).fillna(0.0)

    grouped["throughput_tpd"] = pd.to_numeric(
        grouped["throughput_tpd"],
        errors="coerce"
    ).fillna(0.0)

    grouped["flow_days"] = np.where(
        grouped["throughput_tpd"] > 0,
        grouped["quantity"] / grouped["throughput_tpd"],
        0.0,
    )

    grouped["estimated_days"] = grouped.apply(
        lambda r: apply_estimated_day_rules(
            float(r["flow_days"]),
            str(r["receiver_id"]),
        ),
        axis=1,
    )

    grouped["quantity"] = grouped["quantity"].round(2)
    grouped["throughput_tpd"] = grouped["throughput_tpd"].round(2)
    grouped["flow_days"] = grouped["flow_days"].round(2)
    grouped["estimated_days"] = grouped["estimated_days"].astype(int)

    for col in [
    "queue_cumulative_qty_before",
    "queue_cumulative_qty_after",
    "queue_throughput_tpd",
    ]:
        if col in grouped.columns:
            grouped[col] = pd.to_numeric(
                grouped[col],
                errors="coerce"
            ).fillna(0.0).round(2)

    for col in [
        "queue_start_day_raw",
        "queue_finish_day_raw",
    ]:
        if col in grouped.columns:
            grouped[col] = pd.to_numeric(
                grouped[col],
                errors="coerce"
            ).fillna(0.0).round(4)

    for col in [
        "queue_start_day",
        "queue_finish_day",
    ]:
        if col in grouped.columns:
            grouped[col] = pd.to_numeric(
                grouped[col],
                errors="coerce"
            ).fillna(0).astype(int)

    return grouped.to_dict(orient="records")
       
def dedupe_warnings(warnings: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    unique: List[Dict[str, str]] = []

    for w in warnings:
        sid = str(w.get("supplier_id"))
        if sid not in seen:
            seen.add(sid)
            unique.append(w)

    return unique

def trace_orders_service(request: TraceRequest) -> Dict[str, Any]:
    trace_start_time = time.time()
    logger.info("TRACE START: %s", datetime.now().isoformat())
    sloc_master, stock_snapshot_max_date, _ = get_cached_sloc_master()
    sloc_state = sloc_master.copy()
    current_date = get_current_date()

    all_results: List[Dict[str, Any]] = []
    _path_validity_cache: Dict[tuple, bool] = {}  # cache per-request
    trace_paths_from_facility._validity_cache = {}

    queue_state_by_strategy: Dict[str, Dict[str, Dict[str, float]]] = {
        "VOLUME_GREEDY": {},
    }

    overall_batch_completion_by_strategy: Dict[str, int] = {
        "VOLUME_GREEDY": 0,
    }
    for i, order in enumerate(request.orders):
        if order.facility not in facility_groups:
            raise HTTPException(status_code=400, detail=f"Facility '{order.facility}' tidak valid")

        blacklist = set(str(x) for x in buyer_blacklist.get(order.buyer, [])) if order.buyer else set()
        requested_product = normalize_trace_product(order.product)

        stock_overview, sloc_state = allocate_stock(
            sloc_state=sloc_state,
            refinery_group=order.facility,
            requested_product=requested_product,
            spec=order.spec.upper(),
            demand_qty=float(order.quantity),
            current_date=current_date,
        )
        logger.info("Stock allocation done: %.2f seconds", time.time() - trace_start_time)

        fulfilled_from_stock = float(stock_overview["summary"]["fulfilled_from_stock"])
        unmet_demand = float(stock_overview["summary"]["unmet_demand"])

        warnings: List[Dict[str, str]] = []
        options_results = []

        if unmet_demand > 0:
            strategies = ["VOLUME_GREEDY"]

            for strat in strategies:
                current_trace_meta = {
                    "invalid_paths_removed": False,
                    "volume_redistributed": False,
                    "terminal_vendor_used": False,
                    "terminal_mill_used": False,
                    "tolling_used": False,
                }

                normal_trace_qty = float(unmet_demand)
                additional_pk_qty = 0.0

                if (
                    get_facility_type_for_trace(order.facility) == "REFINERY"
                    and facility_has_kcp(order.facility)
                    and requested_product in {"RBDPKO", "PKO"}
                ):
                    pk_check_df, _ = get_upstream_candidates_df(
                        current_facility=order.facility,
                        query_product="PK",
                        blacklist=blacklist,
                        spec=order.spec.upper(),
                        warnings=[],
                        collect_warnings=False,
                    )

                    pko_check_df, _ = get_upstream_candidates_df(
                        current_facility=order.facility,
                        query_product="PKO",
                        blacklist=blacklist,
                        spec=order.spec.upper(),
                        warnings=[],
                        collect_warnings=False,
                    )

                    if not pk_check_df.empty and not pko_check_df.empty:
                        additional_pk_qty = float(unmet_demand) * 0.5
                        normal_trace_qty = float(unmet_demand) - additional_pk_qty

                paths, strat_warnings, current_trace_meta = trace_paths_from_facility(
                    current_product=requested_product,
                    current_facility=order.facility,
                    quantity=normal_trace_qty,
                    spec=order.spec.upper(),
                    blacklist=blacklist,
                    warnings=[],
                    visited=set(),
                    trace_meta=current_trace_meta,
                    target_total_days=order.target_total_days,
                    strategy=strat,
                    enable_tolling=ALLOW_CPO_TOLLING,
                    tolling_already_used=False,
                )
                logger.info("Normal trace done: %.2f seconds", time.time() - trace_start_time)

                if additional_pk_qty > 1e-9:
                    additional_pk_paths, additional_pk_warnings, current_trace_meta = trace_additional_kcp_pk_paths(
                        current_facility=order.facility,
                        current_product=requested_product,
                        quantity=additional_pk_qty,
                        spec=order.spec.upper(),
                        blacklist=blacklist,
                        target_total_days=order.target_total_days,
                        strategy=strat,
                        enable_tolling=ALLOW_CPO_TOLLING,
                        trace_meta=current_trace_meta,
                    )

                    if additional_pk_paths:
                        paths.extend(additional_pk_paths)

                    strat_warnings.extend(additional_pk_warnings)
                    logger.info("Additional PK trace done: %.2f seconds", time.time() - trace_start_time)
                logger.info("Additional PK check done: %.2f seconds", time.time() - trace_start_time)

                enriched_paths, path_summaries, total_estimated_days, level_day_breakdown, batch_completion_date = enrich_paths_with_forecast(
                    paths=paths,
                    root_receiver_id=order.facility,
                    queue_state=queue_state_by_strategy.get(strat, {}),
                    start_date=current_date,
                    enable_queue_scheduling=ENABLE_QUEUE_SCHEDULING,
                )
                logger.info("Enrich forecast done: %.2f seconds", time.time() - trace_start_time)

                tree = flatten_paths_to_tree(enriched_paths, root_receiver_id=order.facility)
                logger.info("Flatten tree done: %.2f seconds", time.time() - trace_start_time)

                root_debug_rows = [
                    {
                        "supplier": row.get("supplier_name"),
                        "product": row.get("product"),
                        "quantity": row.get("quantity"),
                        "allocation_basis_product": row.get("allocation_basis_product"),
                        "allocation_basis_quantity": row.get("allocation_basis_quantity"),
                        "route_kind": row.get("upstream_route_kind"),
                    }
                    for row in tree
                    if int(row.get("level", 0) or 0) == 0
                ]

                logger.debug("ROOT TREE CHECK: %s", root_debug_rows)

                root_qty_debug = sum(
                    float(row.get("allocation_basis_quantity", row.get("quantity", 0.0)) or 0.0)
                    for row in tree
                    if int(row.get("level", 0) or 0) == 0
                )

                logger.debug("ROOT ALLOCATION BASIS TOTAL: %.2f", round(root_qty_debug, 2))

                tree_schedule_days = int(total_estimated_days)
                tree_start_date = None
                tree_arrival_date = batch_completion_date

                if ENABLE_QUEUE_SCHEDULING:
                    recalculated_days, recalculated_start_date, recalculated_arrival_date = compute_schedule_days_from_tree(tree)

                    if recalculated_days > 0 and recalculated_start_date and recalculated_arrival_date:
                        total_estimated_days = recalculated_days
                        batch_completion_date = recalculated_arrival_date
                        tree_schedule_days = recalculated_days
                        tree_start_date = recalculated_start_date
                        tree_arrival_date = recalculated_arrival_date

                target_days_message = None
                target_days_met = None
                target_days_gap = None

                if order.target_total_days is not None:
                    target_days_met = int(total_estimated_days) <= int(order.target_total_days)
                    target_days_gap = max(int(total_estimated_days) - int(order.target_total_days), 0)

                    if target_days_met:
                        target_days_message = f"Recommendation meets the {order.target_total_days}-day target (result: {total_estimated_days} days)."
                    else:
                        target_days_message = f"Target of {order.target_total_days} days was not met. Best result is {total_estimated_days} days ({target_days_gap} days longer)."

                if ENABLE_QUEUE_SCHEDULING:
                    overall_batch_completion_by_strategy[strat] = max(
                        overall_batch_completion_by_strategy.get(strat, 0),
                        int(total_estimated_days or 0),
                    )

                tree_total_qty = sum(
                    float(
                        row.get(
                            "allocation_basis_quantity",
                            row.get("quantity", 0.0)
                        ) or 0.0
                    )
                    for row in tree
                    if int(row.get("level", 0) or 0) == 0
                )

                allocation_fulfillment_rate = (
                    tree_total_qty / unmet_demand
                    if unmet_demand > 0
                    else 0.0
                )

            
                options_results.append({
                    "option_type": "Historical Volume-Based Recommendation",
                    "total_estimated_days": int(total_estimated_days),
                    "tree": tree,
                    "forecast_summary": {
                        "unmet_demand_qty": round(unmet_demand, 2),
                        "allocated_root_qty": round(tree_total_qty, 2),
                        "unallocated_root_qty": round(max(unmet_demand - tree_total_qty, 0.0), 2),
                        "allocation_fulfillment_rate": round(allocation_fulfillment_rate, 4),
                        "total_estimated_days": int(total_estimated_days),
                        "queue_scheduling_enabled": ENABLE_QUEUE_SCHEDULING,
                        "batch_completion_date": batch_completion_date,
                        "schedule_start_date": tree_start_date,
                        "schedule_arrival_date": tree_arrival_date,
                        "schedule_days_basis": "tree_min_start_to_max_arrival" if ENABLE_QUEUE_SCHEDULING else "estimated_days",
                        "path_summaries": path_summaries,
                        "level_day_breakdown": level_day_breakdown,
                        "target_total_days_input": order.target_total_days,
                        "target_total_days_met": target_days_met,
                        "target_total_days_gap": target_days_gap,
                        "target_total_days_message": target_days_message,
                    },
                    "trace_policy": {
                        "allow_terminal_vendor": ALLOW_TERMINAL_VENDOR,
                        "allow_terminal_mill": ALLOW_TERMINAL_MILL,
                        "tolling_enabled": bool(ALLOW_CPO_TOLLING),
                        "tolling_used": bool(current_trace_meta.get("tolling_used", False)),
                        "terminal_vendor_used": bool(current_trace_meta["terminal_vendor_used"]),
                        "terminal_mill_used": bool(current_trace_meta["terminal_mill_used"]),
                    }
                })
                warnings.extend(strat_warnings)

        unique_warnings = dedupe_warnings(warnings)

        all_results.append({
            "order_index": i + 1,
            "max_date": stock_snapshot_max_date,
            "facility": order.facility,
            "product": requested_product,
            "quantity": order.quantity,
            "spec": order.spec.upper(),
            "buyer": order.buyer,
            "enable_tolling": bool(ALLOW_CPO_TOLLING),
            "stock_overview": stock_overview,
            "recommendation_options": options_results if unmet_demand > 0 else [],
            "warnings": unique_warnings,
        })

    batch_summary = {
        "queue_scheduling_enabled": ENABLE_QUEUE_SCHEDULING,
        "overall_completion_by_strategy": {
            strat: {
                "completion_day": int(day),
                "completion_date": add_days_to_date(current_date, int(day)),
            }
            for strat, day in overall_batch_completion_by_strategy.items()
        },
    }

    if ENABLE_QUEUE_SCHEDULING:
        for order_result in all_results:
            for option in order_result.get("recommendation_options", []):
                strat = str(option.get("option_type", ""))
                batch_info = batch_summary["overall_completion_by_strategy"].get(strat)

                if batch_info:
                    option["forecast_summary"]["overall_batch_completion_day"] = batch_info["completion_day"]
                    option["forecast_summary"]["overall_batch_completion_date"] = batch_info["completion_date"]


    logger.info("TRACE FINISHED IN: %.2f seconds", time.time() - trace_start_time)
    return {"orders": all_results, "batch_summary": batch_summary,}

