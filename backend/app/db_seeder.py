import os
import json
import logging
from threading import Lock

import pandas as pd
from sqlalchemy import inspect, text
from app.database import engine
from app.config import APP_DIR
from app.csv_only_mode import is_sqlite_enabled

logger = logging.getLogger(__name__)
_seed_lock = Lock()

def seed_domain_config_to_sqlite():
    """
    Reads domain_config.json and seeds it into relational SQLite tables.
    Only runs if the tables do not exist yet.
    Thread-safe: uses a lock to prevent concurrent seeding.
    Skipped if USE_SQLITE=false.
    """
    if not is_sqlite_enabled():
        logger.info("Skipping domain config seeding (CSV-only mode)")
        return
    
    with _seed_lock:
        _seed_domain_config_to_sqlite_inner()


def _seed_domain_config_to_sqlite_inner():
    inspector = inspect(engine)
    if "conversion_map" in inspector.get_table_names():
        return  # Already seeded

    config_path = os.path.join(APP_DIR, "domain_config.json")
    if not os.path.exists(config_path):
        return
        
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. conversion_map table
    if "conversion_map" in data:
        df_conv = pd.DataFrame(list(data["conversion_map"].items()), columns=["product", "ratio"])
        df_conv.to_sql("conversion_map", engine, if_exists="replace", index=False)
        
    # 2. process_map table
    if "process_map" in data:
        df_proc = pd.DataFrame(list(data["process_map"].items()), columns=["product", "raw_material"])
        df_proc.to_sql("process_map", engine, if_exists="replace", index=False)
        
    # 3. facility_groups table
    if "facility_groups" in data:
        rows = []
        for refinery, plants in data["facility_groups"].items():
            for plant in plants:
                rows.append({"refinery_name": refinery, "plant_id": plant})
        df_fac = pd.DataFrame(rows)
        df_fac.to_sql("facility_groups", engine, if_exists="replace", index=False)
        
    # 4. buyer_blacklist table
    if "buyer_blacklist" in data:
        rows = []
        for buyer, plants in data["buyer_blacklist"].items():
            for plant in plants:
                rows.append({"buyer_name": buyer, "blacklisted_plant_id": plant})
        df_buyer = pd.DataFrame(rows)
        df_buyer.to_sql("buyer_blacklist", engine, if_exists="replace", index=False)
        
    # 5. Generic Lists/Sets/Dicts as key-value JSON strings.
    # FORECAST_THRESHOLDS added so thresholds are configurable via the config UI.
    generic_keys = [
        "REFINED_PRODUCTS", "DIRECT_REFINERY_PRODUCTS", "DIRECT_PRODUCT_EMPTY_FALLBACK",
        "VENDOR_PARTNER_PCA_PRODUCTS", "REFINERIES_WITH_KCP", "PASS_THROUGH_TYPES",
        "DEFAULT_LEAD_DAYS_BY_TYPE", "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT",
        "FORECAST_THRESHOLDS",
    ]
    
    generic_data = []
    for k in generic_keys:
        if k in data:
            generic_data.append({"config_key": k, "config_value": json.dumps(data[k])})
            
    if generic_data:
        df_gen = pd.DataFrame(generic_data)
        df_gen.to_sql("general_config", engine, if_exists="replace", index=False)

    logger.info("Domain configuration successfully seeded into SQLite tables.")
