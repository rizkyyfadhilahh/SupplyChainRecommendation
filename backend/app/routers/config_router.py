import os
import json
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Any, Dict, Optional
from app.config import reload_domain_config
from app.database import engine
from app.limiter import limiter
from app.utils import require_api_key
from app.services.audit_service import log_config_change, get_audit_history, get_audit_entry

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

@router.put("")
@limiter.limit("10/minute")
def update_domain_config(request: Request, new_config: Dict[str, Any]) -> Dict[str, str]:
    """Update the domain configuration in SQLite tables and reload in-memory."""
    request_id = getattr(request.state, "request_id", None)
    client_ip  = request.client.host if request.client else None

    try:
        # Load current config for diff (audit purposes)
        # Pass a dummy request since get_domain_config requires it for rate limiting
        old_config = get_domain_config(request)

        _GENERIC_KEYS = [
            "REFINED_PRODUCTS", "DIRECT_REFINERY_PRODUCTS", "DIRECT_PRODUCT_EMPTY_FALLBACK",
            "VENDOR_PARTNER_PCA_PRODUCTS", "REFINERIES_WITH_KCP", "PASS_THROUGH_TYPES",
            "DEFAULT_LEAD_DAYS_BY_TYPE", "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT",
            "FORECAST_THRESHOLDS",
        ]

        if "conversion_map" in new_config:
            df = pd.DataFrame(list(new_config["conversion_map"].items()), columns=["product", "ratio"])
            df.to_sql("conversion_map", engine, if_exists="replace", index=False)
            
        if "process_map" in new_config:
            df = pd.DataFrame(list(new_config["process_map"].items()), columns=["product", "raw_material"])
            df.to_sql("process_map", engine, if_exists="replace", index=False)
            
        if "facility_groups" in new_config:
            rows = []
            for refinery, plants in new_config["facility_groups"].items():
                for plant in plants:
                    rows.append({"refinery_name": refinery, "plant_id": plant})
            pd.DataFrame(rows).to_sql("facility_groups", engine, if_exists="replace", index=False)
            
        if "buyer_blacklist" in new_config:
            rows = []
            for buyer, plants in new_config["buyer_blacklist"].items():
                for plant in plants:
                    rows.append({"buyer_name": buyer, "blacklisted_plant_id": plant})
            pd.DataFrame(rows).to_sql("buyer_blacklist", engine, if_exists="replace", index=False)

        generic_data = []
        for k in _GENERIC_KEYS:
            if k in new_config:
                generic_data.append({"config_key": k, "config_value": json.dumps(new_config[k])})
        
        if generic_data:
            pd.DataFrame(generic_data).to_sql("general_config", engine, if_exists="replace", index=False)

        # Trigger in-memory reload
        reload_domain_config()
        
        # --- Audit: log each changed top-level key ---
        all_keys = ["conversion_map", "process_map", "facility_groups", "buyer_blacklist"] + _GENERIC_KEYS
        for key in all_keys:
            if key not in new_config:
                continue
            old_val = old_config.get(key)
            new_val = new_config[key]
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
