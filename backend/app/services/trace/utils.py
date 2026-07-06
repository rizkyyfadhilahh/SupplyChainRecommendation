from typing import Any, Dict, List, Optional, Set
import pandas as pd

from app.config import (
    DIRECT_REFINERY_PRODUCTS,
    PASS_THROUGH_TYPES,
    REFINERIES_WITH_KCP,
    VENDOR_TYPE,
    conversion_map,
    facility_groups,
    process_map,
)
from app.state import get_app_data
from app.utils import normalize_facility_type, is_valid_value, normalize_spec_value

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


def get_receiver_facilities(current_facility: str) -> List[str]:
    if current_facility in facility_groups:
        return [str(x) for x in facility_groups[current_facility]]
    return [str(current_facility)]

def is_mill_supplier(supplier_id: str, supplier_type: str) -> bool:
    return str(supplier_id) in _mill_ids() or str(supplier_type).upper() == "MILL"

def is_mill_eudr(mill_id: str) -> bool:
    return normalize_spec_value(get_facility_spec_safe(str(mill_id))) == "EUDR"

def is_vendor_eudr_from_row(row: pd.Series) -> bool:
    return normalize_spec_value(row.get("supplier_spec", "")) == "EUDR"

def dedupe_warnings(warnings: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    unique: List[Dict[str, str]] = []

    for w in warnings:
        sid = str(w.get("supplier_id"))
        if sid not in seen:
            seen.add(sid)
            unique.append(w)

    return unique


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


