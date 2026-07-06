import logging
import time
from typing import Any, Dict
import pandas as pd
from threading import Lock

logger = logging.getLogger(__name__)

from app.config import facility_groups
from app.utils import find_first_existing, read_csv_required, normalize_columns
from app.state import APP_DATA, set_app_data
from app.database import engine
from sqlalchemy import text
from app.csv_only_mode import is_sqlite_enabled, save_to_csv_cache
from app.pipeline.utils import vectorize_normalize_facility_type, vectorize_normalize_spec_value
from app.pipeline.product_flow import process_product_relations, process_product_flow
from app.pipeline.ffb_flow import process_ffb_relations, process_ffb_flow
from app.pipeline.tolling_flow import process_tolling_flow

def load_application_data() -> Dict[str, Any]:
    logger.info("load_application_data STARTING")
    new_app_data = {}

    logger.info("Loading master_facility")
    plant_to_refinery: Dict[str, str] = {}
    for refinery_name, plants in facility_groups.items():
        for plant in plants:
            plant_to_refinery[str(plant)] = refinery_name

    CACHE_TTL_SECONDS = 300
    CONFIG_FILE_LOCK = Lock()

    master_facility_path = find_first_existing([
        "master_facility.csv",
        "master_facility_new.csv",
        "**/master_facility.csv",
        "**/master_facility_new.csv",
    ])

    logger.info("Loading events_bc and links_bc")
    events_path = find_first_existing([
        "3 month/events_bc_01_Des_24_Feb.csv",
        "3 month/events_bc_01_Des_24_feb.csv",
        "**/events_bc_01_Des_24_Feb.csv",
        "**/events_bc_01_Des_24_feb.csv",
    ])

    links_path = find_first_existing([
        "3 month/links_bc_01_Des_24_Feb.csv",
        "3 month/links_bc_01_Des_24_feb.csv",
        "**/links_bc_01_Des_24_Feb.csv",
        "**/links_bc_01_Des_24_feb.csv",
    ])

    master_facility = normalize_columns(
        read_csv_required(master_facility_path, "master_facility")
    )
    events_bc = normalize_columns(
        read_csv_required(events_path, "events_bc")
    )
    links_bc = normalize_columns(
        read_csv_required(links_path, "links_bc")
    )

    master_facility = master_facility.drop_duplicates("facility_id").copy()
    master_facility["facility_id"] = master_facility["facility_id"].astype(str)

    if "facility_type" in master_facility.columns:
        master_facility["facility_type"] = master_facility["facility_type"].pipe(vectorize_normalize_facility_type)
    if "specification" in master_facility.columns:
        master_facility["specification"] = master_facility["specification"].pipe(vectorize_normalize_spec_value)

    facility_name_lookup = master_facility.set_index("facility_id")["facility_name"].to_dict()
    facility_type_lookup = master_facility.set_index("facility_id")["facility_type"].fillna("").astype(str).to_dict()
    facility_spec_lookup = master_facility.set_index("facility_id")["specification"].fillna("").astype(str).to_dict()

    facility_lookup = master_facility[["facility_id", "facility_name", "facility_type", "specification"]].copy()

    vendor_ids_from_events = (
        pd.to_numeric(events_bc["vendor"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", "")
        .str.strip()
    )

    vendor_ids_from_events = vendor_ids_from_events[vendor_ids_from_events != ""].unique().tolist()
    existing_facility_ids = set(facility_lookup["facility_id"].astype(str).tolist())
    missing_vendor_ids = [vid for vid in vendor_ids_from_events if vid not in existing_facility_ids]

    if missing_vendor_ids:
        vendor_lookup_add = pd.DataFrame({
            "facility_id": missing_vendor_ids,
            "facility_name": missing_vendor_ids,
            "facility_type": ["VENDOR"] * len(missing_vendor_ids),
            "specification": [None] * len(missing_vendor_ids),
        })

        facility_lookup = pd.concat([facility_lookup, vendor_lookup_add], ignore_index=True)

    facility_lookup["facility_id"] = facility_lookup["facility_id"].astype(str)

    facility_name_lookup = facility_lookup.set_index("facility_id")["facility_name"].to_dict()
    facility_type_lookup = facility_lookup.set_index("facility_id")["facility_type"].fillna("").astype(str).to_dict()
    facility_spec_lookup = facility_lookup.set_index("facility_id")["specification"].fillna("").astype(str).to_dict()

    set_app_data("facility_name_lookup", facility_name_lookup)
    set_app_data("facility_type_lookup", facility_type_lookup)
    set_app_data("facility_spec_lookup", facility_spec_lookup)

    if "insert_date" not in events_bc.columns:
        events_bc["insert_date"] = pd.NaT

    # Optimize Memory: Only keep columns that are absolutely needed for linkages
    cols_to_keep_supplier = ["unique_id", "plant", "estate", "partner_pca", "spb", "product_name", "movement_type", "insert_date"]
    # Check which ones actually exist in events_bc
    cols_to_keep_supplier = [c for c in cols_to_keep_supplier if c in events_bc.columns]
    
    events_supplier = events_bc[cols_to_keep_supplier].rename(
        columns={
            "unique_id": "event1_id",
            "plant": "plant_supplier",
            "estate": "estate_supplier",
            "partner_pca": "partner_pca_supplier",
            "spb": "spb_supplier",
            "product_name": "product_name_supplier",
            "movement_type": "movement_type_supplier",
            "insert_date": "insert_date_supplier",
        }
    )

    cols_to_keep_receiver = ["unique_id", "plant", "estate", "vendor", "spb", "product_name", "movement_type", "insert_date"]
    cols_to_keep_receiver = [c for c in cols_to_keep_receiver if c in events_bc.columns]

    events_receiver = events_bc[cols_to_keep_receiver].rename(
        columns={
            "unique_id": "event2_id",
            "plant": "plant_receiver",
            "estate": "estate_receiver",
            "vendor": "vendor_receiver",
            "spb": "spb_receiver",
            "product_name": "product_name_receiver",
            "movement_type": "movement_type_receiver",
            "insert_date": "insert_date_receiver",
        }
    )

    logger.info("Processing linkages")
    relations_all = (
        links_bc
        .merge(events_supplier, on="event1_id", how="left")
        .merge(events_receiver, on="event2_id", how="left")
    )

    relations_all["insert_date_supplier"] = pd.to_datetime(relations_all["insert_date_supplier"], errors="coerce")
    relations_all["insert_date_receiver"] = pd.to_datetime(relations_all["insert_date_receiver"], errors="coerce")

    product_relations = process_product_relations(relations_all, facility_lookup, events_supplier, events_receiver)
    ffb_relations = process_ffb_relations(relations_all)
    
    product_flow = process_product_flow(product_relations, facility_lookup)
    ffb_flow = process_ffb_flow(ffb_relations, facility_lookup)
    tolling_flow = process_tolling_flow(relations_all, facility_lookup)

    mill_ids = set(ffb_flow["mill"].astype(str).unique())

    # Exclude complex lookups that aren't dataframes or are small scalar sets
    # We will save lookups as SQLite tables or JSON config if needed.
    # facility_lookup is a DataFrame, so we save it.
    
    import json

    # ✅ PERFORMANCE: Save heavy DataFrames to SQLite ONLY.
    # Do NOT keep large DataFrames in APP_DATA — that doubles memory usage.
    # Services should query SQLite directly for large data.
    # In CSV-only mode: only cache small, frequently-accessed tables
    # Skip huge tables (relations_all, product_relations) to avoid OOM
    if is_sqlite_enabled():
        dataframes_to_save = {
            "master_facility": master_facility,
            "events_bc": events_bc,
            "links_bc": links_bc,
            "facility_lookup": facility_lookup,
            "relations_all": relations_all,
            "product_relations": product_relations,
            "product_flow": product_flow,
            "ffb_relations": ffb_relations,
            "ffb_flow": ffb_flow,
            "tolling_flow": tolling_flow,
        }
    else:
        # CSV-only mode: cache essential tables only.
        # Large tables (events_bc, links_bc) cached without copy to save RAM.
        # Derived tables (relations_all, product_relations) skipped entirely.
        dataframes_to_save = {
            "master_facility": master_facility,
            "facility_lookup": facility_lookup,
            "product_flow": product_flow,
            "ffb_flow": ffb_flow,
            "tolling_flow": tolling_flow,
        }
        # Cache large tables without copy to avoid doubling RAM usage
        save_to_csv_cache("events_bc", events_bc, copy=False)
        save_to_csv_cache("links_bc", links_bc, copy=False)

    # ✅ CSV-only mode: skip SQLite operations entirely
    if is_sqlite_enabled():
        # PERFORMANCE: Disable WAL/sync during bulk load using a direct
        # SQLite connection (bypasses the SQLAlchemy pool) so we don't
        # contend with pool connections that already set journal_mode=WAL.
        import sqlite3 as _sqlite3
        _db_path = engine.url.database
        _raw = _sqlite3.connect(_db_path)
        try:
            _raw.execute("PRAGMA journal_mode = OFF")
            _raw.execute("PRAGMA synchronous = OFF")
            _raw.commit()
        finally:
            _raw.close()
        # Dispose the pool so new connections pick up the changed journal_mode.
        engine.dispose()

    for table_name, df in dataframes_to_save.items():
        if not isinstance(df, pd.DataFrame):
            continue
        
        if is_sqlite_enabled():
            logger.info("Saving %s (%d rows) to SQLite...", table_name, len(df))
            t0 = time.time()
            # Serialize any complex types (list/dict/set) to JSON strings
            df_save = df.copy()
            for col in df_save.columns:
                if df_save[col].dtype == "object":
                    first_valid = df_save[col].dropna().iloc[0] if not df_save[col].dropna().empty else None
                    if isinstance(first_valid, (list, dict, set, tuple)):
                        df_save[col] = df_save[col].apply(
                            lambda x: json.dumps(list(x))
                            if isinstance(x, (set, tuple))
                            else json.dumps(x)
                            if isinstance(x, (list, dict))
                            else x
                        )
            # ✅ PERFORMANCE: Large chunksize + method="multi" = fewer round trips
            # chunksize=500 avoids "too many SQL variables" errors (SQLite
            # limit is 999 by default; 500 rows * ~9 cols = ~4500 vars per batch).
            df_save.to_sql(
                table_name, engine,
                if_exists="replace",
                index=False,
                chunksize=500,
                method="multi",
            )
            logger.info("  %s saved in %.1fs", table_name, time.time() - t0)
            # Free RAM immediately after saving
            del df_save
        else:
            # CSV-only mode: save to in-memory cache
            logger.info("Caching %s (%d rows) in memory (CSV-only mode)", table_name, len(df))
            save_to_csv_cache(table_name, df)

    # ✅ Restore WAL mode after bulk load (only if using SQLite)
    if is_sqlite_enabled():
        _raw = _sqlite3.connect(_db_path)
        try:
            _raw.execute("PRAGMA journal_mode = WAL")
            _raw.execute("PRAGMA synchronous = OFF")
            _raw.commit()
        finally:
            _raw.close()
        engine.dispose()

    # ✅ PERFORMANCE: Keep ONLY small lookup dicts in memory (< 100K entries each).
    # Large DataFrames are intentionally NOT stored in APP_DATA.
    set_app_data("facility_name_lookup", facility_name_lookup)
    set_app_data("facility_type_lookup", facility_type_lookup)
    set_app_data("facility_spec_lookup", facility_spec_lookup)
    set_app_data("plant_to_refinery", plant_to_refinery)
    set_app_data("mill_ids", mill_ids)
    # Keep a tiny events_bc subset for stock service (only columns it needs).
    # NOTE: key must be "events_bc_slim" (not "events_bc") because "events_bc"
    # is listed in DB_TABLES and set_app_data() would silently ignore it.
    events_bc_slim = events_bc[[c for c in ["unique_id", "product_name"] if c in events_bc.columns]].copy()
    set_app_data("events_bc_slim", events_bc_slim)
    # Mark data as fully loaded so health checks and services can gate on this.
    set_app_data("app_data_loaded", True)

    # Free the large DataFrames from this function's scope
    del relations_all, product_relations, ffb_relations, tolling_flow

    logger.info("load_application_data FINISHED")
    return APP_DATA