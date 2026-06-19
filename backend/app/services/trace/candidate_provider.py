from typing import Dict, List, Optional, Set, Tuple
import pandas as pd
from app.config import ALLOW_CPO_TOLLING, DIRECT_PRODUCT_EMPTY_FALLBACK, process_map
from app.services.trace.utils import (
    _product_flow, _ffb_flow, _tolling_flow, _facility_name_lookup,
    get_facility_type_safe, get_receiver_facilities, get_next_query_product,
    convert_product_quantity_along_path, get_facility_type_for_trace
)
from app.utils import normalize_facility_type, normalize_spec_value

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
