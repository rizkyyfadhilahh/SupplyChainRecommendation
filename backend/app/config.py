import os
import json
from dotenv import load_dotenv

# Load .env for local development. In production, this can be omitted 
# or overriden by system-level environment variables from CI/CD.
load_dotenv()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(APP_DIR)
TEMP_DIR = os.path.join(BASE_DIR, "temp_data")

APP_DEBUG = False

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

API_KEY = os.getenv("API_KEY")

CACHE_TTL_SECONDS = 300

VENDOR_TYPE = "VENDOR"
ALLOW_TERMINAL_VENDOR = True
ALLOW_TERMINAL_MILL = True
ALLOW_CPO_TOLLING = True
PRIORITIZE_VENDOR_DEBUG = False

MIN_TXN_FOR_EXACT = 3
MIN_ACTIVE_DAYS_FOR_EXACT = 3
FORECAST_TARGET_DAYS = 15
MIN_ALLOCATED_SHARE_PER_SUPPLIER = 0.005
ENABLE_QUEUE_SCHEDULING = True

def get_dynamic_min_allocated_share(demand_qty: float) -> float:
    demand_qty = float(demand_qty or 0.0)
    if demand_qty <= 1_000_000:
        return 0.05
    if demand_qty <= 3_000_000:
        return 0.03
    if demand_qty <= 5_000_000:
        return 0.02
    return 0.02

# Initialize empty objects that will be populated by reload_domain_config()
process_map = {}
conversion_map = {}
REFINED_PRODUCTS = []
DIRECT_REFINERY_PRODUCTS = set()
DIRECT_PRODUCT_EMPTY_FALLBACK = {}
VENDOR_PARTNER_PCA_PRODUCTS = set()
REFINERIES_WITH_KCP = set()
PASS_THROUGH_TYPES = set()
DEFAULT_LEAD_DAYS_BY_TYPE = {}
DEFAULT_THROUGHPUT_TPD_BY_PRODUCT = {}
facility_groups = {}
buyer_blacklist = {}

def reload_domain_config():
    """Reads domain config from SQLite tables (or JSON if CSV-only mode) and updates the in-memory dictionaries directly."""
    from sqlalchemy import inspect
    from app.database import engine
    import pandas as pd
    import os
    
    # CSV-only mode: load directly from domain_config.json
    use_sqlite = os.getenv("USE_SQLITE", "true").lower() == "true"
    if not use_sqlite:
        config_path = os.path.join(APP_DIR, "domain_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Load all configs from JSON directly
            conversion_map.clear()
            conversion_map.update(data.get("conversion_map", {}))
            
            process_map.clear()
            process_map.update(data.get("process_map", {}))
            
            facility_groups.clear()
            for ref, plants in data.get("facility_groups", {}).items():
                facility_groups[ref] = plants
            
            buyer_blacklist.clear()
            for buyer, plants in data.get("buyer_blacklist", {}).items():
                buyer_blacklist[buyer] = plants
            
            REFINED_PRODUCTS.clear()
            REFINED_PRODUCTS.extend(data.get("REFINED_PRODUCTS", []))
            
            DIRECT_REFINERY_PRODUCTS.clear()
            DIRECT_REFINERY_PRODUCTS.update(data.get("DIRECT_REFINERY_PRODUCTS", []))
            
            DIRECT_PRODUCT_EMPTY_FALLBACK.clear()
            DIRECT_PRODUCT_EMPTY_FALLBACK.update(data.get("DIRECT_PRODUCT_EMPTY_FALLBACK", {}))
            
            VENDOR_PARTNER_PCA_PRODUCTS.clear()
            VENDOR_PARTNER_PCA_PRODUCTS.update(data.get("VENDOR_PARTNER_PCA_PRODUCTS", []))
            
            REFINERIES_WITH_KCP.clear()
            REFINERIES_WITH_KCP.update(data.get("REFINERIES_WITH_KCP", []))
            
            PASS_THROUGH_TYPES.clear()
            PASS_THROUGH_TYPES.update(data.get("PASS_THROUGH_TYPES", []))
            
            DEFAULT_LEAD_DAYS_BY_TYPE.clear()
            DEFAULT_LEAD_DAYS_BY_TYPE.update(data.get("DEFAULT_LEAD_DAYS_BY_TYPE", {}))
            
            DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.clear()
            DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.update(data.get("DEFAULT_THROUGHPUT_TPD_BY_PRODUCT", {}))
            
            print("Domain config loaded from JSON (CSV-only mode)")
        return
    
    # SQLite mode: load from database tables
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "conversion_map" in tables:
            df = pd.read_sql_table("conversion_map", engine)
            conversion_map.clear()
            conversion_map.update(dict(zip(df["product"], df["ratio"])))
            
        if "process_map" in tables:
            df = pd.read_sql_table("process_map", engine)
            process_map.clear()
            process_map.update(dict(zip(df["product"], df["raw_material"])))
            
        if "facility_groups" in tables:
            df = pd.read_sql_table("facility_groups", engine)
            facility_groups.clear()
            for ref, group in df.groupby("refinery_name"):
                facility_groups[ref] = group["plant_id"].tolist()
                
        if "buyer_blacklist" in tables:
            df = pd.read_sql_table("buyer_blacklist", engine)
            buyer_blacklist.clear()
            for buyer, group in df.groupby("buyer_name"):
                buyer_blacklist[buyer] = group["blacklisted_plant_id"].tolist()
                
        if "general_config" in tables:
            df = pd.read_sql_table("general_config", engine)
            for _, row in df.iterrows():
                k = row["config_key"]
                v = json.loads(row["config_value"])
                
                if k == "REFINED_PRODUCTS":
                    REFINED_PRODUCTS.clear()
                    REFINED_PRODUCTS.extend(v)
                elif k == "DIRECT_REFINERY_PRODUCTS":
                    DIRECT_REFINERY_PRODUCTS.clear()
                    DIRECT_REFINERY_PRODUCTS.update(v)
                elif k == "DIRECT_PRODUCT_EMPTY_FALLBACK":
                    DIRECT_PRODUCT_EMPTY_FALLBACK.clear()
                    DIRECT_PRODUCT_EMPTY_FALLBACK.update(v)
                elif k == "VENDOR_PARTNER_PCA_PRODUCTS":
                    VENDOR_PARTNER_PCA_PRODUCTS.clear()
                    VENDOR_PARTNER_PCA_PRODUCTS.update(v)
                elif k == "REFINERIES_WITH_KCP":
                    REFINERIES_WITH_KCP.clear()
                    REFINERIES_WITH_KCP.update(v)
                elif k == "PASS_THROUGH_TYPES":
                    PASS_THROUGH_TYPES.clear()
                    PASS_THROUGH_TYPES.update(v)
                elif k == "DEFAULT_LEAD_DAYS_BY_TYPE":
                    DEFAULT_LEAD_DAYS_BY_TYPE.clear()
                    DEFAULT_LEAD_DAYS_BY_TYPE.update(v)
                elif k == "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT":
                    DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.clear()
                    DEFAULT_THROUGHPUT_TPD_BY_PRODUCT.update(v)
                    
    except Exception as e:
        print(f"Warning: Could not load domain config from SQLite: {e}")

# Load the config immediately upon module import (will be empty until seeded)
reload_domain_config()