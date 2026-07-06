import numpy as np
import pandas as pd
from typing import Any, Dict

from app.config import facility_groups
from app.utils import normalize_facility_type, is_valid_value
from app.state import get_app_data

def get_facility_name_safe(facility_id: Any) -> str:
    fid = str(facility_id).strip()
    lookup = get_app_data("facility_name_lookup", {})
    return str(lookup.get(fid, fid))

def get_facility_type_safe(facility_id: Any) -> str:
    fid = str(facility_id).strip()
    lookup = get_app_data("facility_type_lookup", {})
    return normalize_facility_type(lookup.get(fid, ""))

def get_facility_spec_safe(facility_id: Any) -> str:
    fid = str(facility_id).strip()
    lookup = get_app_data("facility_spec_lookup", {})
    return str(lookup.get(fid, ""))

def get_facility_type_for_trace(facility: Any) -> str:
    facility = str(facility).strip()

    if facility in facility_groups:
        return "REFINERY"

    return get_facility_type_safe(facility)

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

def vectorize_normalize_trace_product(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.upper().str.strip()
    conds = [
        s.str.contains("RBDPKO", na=False),
        s.str.contains("RBDPO", na=False),
        s.str.contains("PKO", na=False),
        s.str.contains("CPO", na=False),
        (s == "PK") | s.str.startswith("PK "),
        s.str.contains("RBDOLN", na=False) | s.str.contains("OLEIN", na=False),
        s.str.contains("RBDST", na=False),
        s.str.contains("RBDPS", na=False),
        s.str.contains("PFAD", na=False),
        s == "FFB"
    ]
    choices = ["RBDPKO", "RBDPO", "PKO", "CPO", "PK", "RBDOLN", "RBDST", "RBDPS", "PFAD", "FFB"]
    return pd.Series(np.select(conds, choices, default=s), index=s.index)

def vectorize_normalize_facility_type(series: pd.Series) -> pd.Series:
    return series.astype(str).str.upper().str.strip()

def vectorize_normalize_spec_value(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.upper().str.strip()
    return pd.Series(np.where(s.isin({"EUDR", "YES", "Y", "TRUE", "COMPLIANT", "EUDR COMPLIANT"}), "EUDR", s), index=s.index)
