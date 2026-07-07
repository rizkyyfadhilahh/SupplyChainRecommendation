import os
import json
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Any, Dict, Optional
from app.config import reload_domain_config, _CONFIG_LOCK
from app.database import engine
from app.limiter import limiter
from app.utils import require_api_key
from app.services.audit_service import log_config_change, get_audit_history, get_audit_entry
from app.schemas_config import GeneralConfigUpdate

router = APIRouter(
    prefix="/api/config",
    tags=["config"],
    dependencies=[Depends(require_api_key)],
)

@router.get("/audit-history")
@limiter.limit("60/minute")
def get_config_audit_history(request: Request,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    # NOTE: request param is required by slowapi even if unused in the handler
    """Return audit log history for domain config changes, newest first."""
    return {
        "audit_logs": get_audit_history(
            entity_type=entity_type,
            action=action,
            limit=min(limit, 500),
        )
    }


@router.get("/audit-history/{audit_id}")
@limiter.limit("60/minute")
def get_config_audit_entry(request: Request, audit_id: int) -> Dict[str, Any]:
    """Return a single audit log entry by id."""
    entry = get_audit_entry(audit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Audit log #{audit_id} not found")
    return entry


@router.get("")
@limiter.limit("60/minute")
def get_domain_config(request: Request) -> Dict[str, Any]:
    """Retrieve the current domain configuration from SQLite tables."""
    data = {}
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "conversion_map" in tables:
            df = pd.read_sql_table("conversion_map", engine)
            data["conversion_map"] = dict(zip(df["product"], df["ratio"]))
            
        if "process_map" in tables:
            df = pd.read_sql_table("process_map", engine)
            data["process_map"] = dict(zip(df["product"], df["raw_material"]))
            
        if "facility_groups" in tables:
            df = pd.read_sql_table("facility_groups", engine)
            fac_groups = {}
            for ref, group in df.groupby("refinery_name"):
                fac_groups[ref] = group["plant_id"].tolist()
            data["facility_groups"] = fac_groups
            
        if "buyer_blacklist" in tables:
            df = pd.read_sql_table("buyer_blacklist", engine)
            blacklists = {}
            for buyer, group in df.groupby("buyer_name"):
                blacklists[buyer] = group["blacklisted_plant_id"].tolist()
            data["buyer_blacklist"] = blacklists
            
        if "general_config" in tables:
            df = pd.read_sql_table("general_config", engine)
            for _, row in df.iterrows():
                data[row["config_key"]] = json.loads(row["config_value"])
                
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")

# ---------------------------------------------------------------------------
# Per-section GET endpoint
# ---------------------------------------------------------------------------

_SECTION_KEYS = {
    "conversion_map", "process_map", "facility_groups", "buyer_blacklist",
    "REFINED_PRODUCTS", "DIRECT_REFINERY_PRODUCTS", "DIRECT_PRODUCT_EMPTY_FALLBACK",
    "VENDOR_PARTNER_PCA_PRODUCTS", "REFINERIES_WITH_KCP", "PASS_THROUGH_TYPES",
    "DEFAULT_LEAD_DAYS_BY_TYPE", "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT",
    "FORECAST_THRESHOLDS",
}


@router.get("/sections")
@limiter.limit("60/minute")
def list_config_sections(request: Request) -> Dict[str, Any]:
    """Return the list of valid config section names."""
    return {"sections": sorted(_SECTION_KEYS)}


@router.get("/{section}")
@limiter.limit("60/minute")
def get_config_section(request: Request, section: str) -> Dict[str, Any]:
    """Return a single config section by name.

    Valid section names: conversion_map, process_map, facility_groups,
    buyer_blacklist, REFINED_PRODUCTS, DIRECT_REFINERY_PRODUCTS,
    DIRECT_PRODUCT_EMPTY_FALLBACK, VENDOR_PARTNER_PCA_PRODUCTS,
    REFINERIES_WITH_KCP, PASS_THROUGH_TYPES, DEFAULT_LEAD_DAYS_BY_TYPE,
    DEFAULT_THROUGHPUT_TPD_BY_PRODUCT, FORECAST_THRESHOLDS.
    """
    if section not in _SECTION_KEYS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown config section '{section}'. "
                   f"Valid sections: {sorted(_SECTION_KEYS)}",
        )
    full = get_domain_config(request)
    if section not in full:
        return {section: None}
    return {section: full[section]}


# ---------------------------------------------------------------------------
# Cascade helper — rebuild derived lookups after structural config changes
# ---------------------------------------------------------------------------

def _cascade_facility_groups(new_groups: Dict[str, Any]) -> None:
    """Rebuild plant_to_refinery in APP_DATA after facility_groups changes.

    This ensures that stock allocation and trace services immediately see
    the new plant→refinery mapping without a server restart.
    """
    from app.state import set_app_data
    mapping = {
        str(plant): ref
        for ref, plants in new_groups.items()
        for plant in plants
    }
    set_app_data("plant_to_refinery", mapping)


# ---------------------------------------------------------------------------
# PUT — validated update
# ---------------------------------------------------------------------------

@router.put("")
@limiter.limit("10/minute")
def update_domain_config(request: Request, new_config: GeneralConfigUpdate) -> Dict[str, str]:
    """Update the domain configuration in SQLite tables and reload in-memory.

    Only the sections present in the payload are updated — omitted sections
    are left unchanged.  Unknown top-level keys are rejected with 422.
    """
    request_id = getattr(request.state, "request_id", None)
    client_ip  = request.client.host if request.client else None

    _GENERIC_KEYS = [
        "REFINED_PRODUCTS", "DIRECT_REFINERY_PRODUCTS", "DIRECT_PRODUCT_EMPTY_FALLBACK",
        "VENDOR_PARTNER_PCA_PRODUCTS", "REFINERIES_WITH_KCP", "PASS_THROUGH_TYPES",
        "DEFAULT_LEAD_DAYS_BY_TYPE", "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT",
        "FORECAST_THRESHOLDS",
    ]

    # Convert validated Pydantic model to plain dict, dropping unset fields
    payload = new_config.model_dump(exclude_none=True)

    try:
        # Load current config for diff (audit purposes)
        old_config = get_domain_config(request)

        if "conversion_map" in payload:
            df = pd.DataFrame(
                list(payload["conversion_map"].items()),
                columns=["product", "ratio"],
            )
            df.to_sql("conversion_map", engine, if_exists="replace", index=False)

        if "process_map" in payload:
            df = pd.DataFrame(
                list(payload["process_map"].items()),
                columns=["product", "raw_material"],
            )
            df.to_sql("process_map", engine, if_exists="replace", index=False)

        if "facility_groups" in payload:
            rows = [
                {"refinery_name": refinery, "plant_id": plant}
                for refinery, plants in payload["facility_groups"].items()
                for plant in plants
            ]
            pd.DataFrame(rows).to_sql(
                "facility_groups", engine, if_exists="replace", index=False
            )

        if "buyer_blacklist" in payload:
            rows = [
                {"buyer_name": buyer, "blacklisted_plant_id": plant}
                for buyer, plants in payload["buyer_blacklist"].items()
                for plant in plants
            ]
            pd.DataFrame(rows).to_sql(
                "buyer_blacklist", engine, if_exists="replace", index=False
            )

        generic_data = [
            {"config_key": k, "config_value": json.dumps(payload[k])}
            for k in _GENERIC_KEYS
            if k in payload
        ]
        if generic_data:
            pd.DataFrame(generic_data).to_sql(
                "general_config", engine, if_exists="replace", index=False
            )

        # Reload in-memory config under the config lock
        reload_domain_config()

        # Cascade: rebuild plant_to_refinery if facility_groups changed
        if "facility_groups" in payload:
            _cascade_facility_groups(payload["facility_groups"])

        # Audit: log each changed top-level key
        all_keys = ["conversion_map", "process_map", "facility_groups", "buyer_blacklist"] + _GENERIC_KEYS
        for key in all_keys:
            if key not in payload:
                continue
            old_val = old_config.get(key)
            new_val = payload[key]
            if old_val != new_val:
                log_config_change(
                    action="UPDATE",
                    entity_type=key,
                    old_value=old_val,
                    new_value=new_val,
                    request_id=request_id,
                    ip_address=client_ip,
                )

        return {"message": "Configuration updated in SQLite and reloaded successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
