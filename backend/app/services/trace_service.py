import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

from app.config import (
    ALLOW_CPO_TOLLING, ALLOW_TERMINAL_MILL, ALLOW_TERMINAL_VENDOR, 
    ENABLE_QUEUE_SCHEDULING, buyer_blacklist, facility_groups
)
from app.schemas import TraceRequest
from app.utils import normalize_trace_product
from app.services.stock_service import allocate_stock, get_cached_sloc_master
from app.services.queue_service import get_current_date, add_days_to_date, compute_schedule_days_from_tree

from app.services.trace.utils import get_facility_type_for_trace, facility_has_kcp, dedupe_warnings
from app.services.trace.candidate_provider import get_upstream_candidates_df
from app.services.trace.path_finder import trace_paths_from_facility, trace_additional_kcp_pk_paths
from app.services.trace.tree_builder import enrich_paths_with_forecast, flatten_paths_to_tree


logger = logging.getLogger(__name__)
   
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
                    "nodes_expanded": 0,
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

