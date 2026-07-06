import os
import json
import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.config import reload_domain_config
from app.database import engine

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("")
def get_domain_config() -> Dict[str, Any]:
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
def update_domain_config(new_config: Dict[str, Any]) -> Dict[str, str]:
    """Update the domain configuration in SQLite tables and reload in-memory."""
    try:
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
            
        generic_keys = [
            "REFINED_PRODUCTS", "DIRECT_REFINERY_PRODUCTS", "DIRECT_PRODUCT_EMPTY_FALLBACK",
            "VENDOR_PARTNER_PCA_PRODUCTS", "REFINERIES_WITH_KCP", "PASS_THROUGH_TYPES",
            "DEFAULT_LEAD_DAYS_BY_TYPE", "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT"
        ]
        generic_data = []
        for k in generic_keys:
            if k in new_config:
                generic_data.append({"config_key": k, "config_value": json.dumps(new_config[k])})
        
        if generic_data:
            pd.DataFrame(generic_data).to_sql("general_config", engine, if_exists="replace", index=False)

        # Trigger an in-memory reload
        reload_domain_config()
        
        return {"message": "Configuration updated in SQLite and reloaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
