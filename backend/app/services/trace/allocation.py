import logging
from typing import Optional
import pandas as pd

from app.config import FORECAST_TARGET_DAYS, get_dynamic_min_allocated_share
from app.services.forecast_service import (
    get_edge_forecast_row, get_estate_edge_forecast_row, compute_edge_estimated_days
)
from app.services.trace.utils import get_conversion_ratio, convert_allocation_to_candidate_qty

logger = logging.getLogger(__name__)

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
