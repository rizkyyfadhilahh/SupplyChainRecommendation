from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from app.config import (
    ALLOW_CPO_TOLLING, ALLOW_TERMINAL_MILL, ALLOW_TERMINAL_VENDOR, VENDOR_TYPE
)

from app.utils import normalize_trace_product, normalize_spec_value

from app.services.trace.utils import (
    allow_fallback_for_facility, is_mill_supplier,
    get_facility_type_for_trace, facility_has_kcp,
    convert_product_quantity_along_path, convert_allocation_to_candidate_qty, is_mill_eudr
)

from app.services.trace.candidate_provider import (
    get_candidate_df_with_fallback, get_cpo_tolling_candidates, 
    get_ffb_upstream_candidates, get_upstream_candidates_df
)
from app.services.trace.allocation import select_candidates_target_aware
from app.services.trace.tree_builder import build_node, dedupe_selected_ffb_suppliers

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
