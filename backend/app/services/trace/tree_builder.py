from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from app.config import FORECAST_TARGET_DAYS
from app.services.trace.utils import (
    _facility_name_lookup, get_facility_type_safe, map_supplier_output_identity
)
from app.services.forecast_service import (
    compute_edge_estimated_days, apply_estimated_day_rules
)
from app.services.queue_service import (
    get_current_date, add_days_to_date, compute_schedule_days_from_tree,
    apply_queue_scheduling_to_paths, compute_total_estimated_days_by_level
)
from app.utils import normalize_display_key

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
  