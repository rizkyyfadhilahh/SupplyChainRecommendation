from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from threading import Lock

from app.config import (
    TEMP_DIR,
    VENDOR_PARTNER_PCA_PRODUCTS,
    facility_groups,
)

from app.utils import (
    find_first_existing,
    read_csv_required,
    normalize_columns,
    normalize_facility_type,
    normalize_spec_value,
    normalize_trace_product,
    is_valid_value,
)

APP_DATA: Dict[str, Any] = {}

def set_app_data(key: str, value: Any) -> None:
    APP_DATA[key] = value


def get_app_data(key: str, default: Optional[Any] = None) -> Any:
    return APP_DATA.get(key, default)


def get_all_app_data() -> Dict[str, Any]:
    return APP_DATA


def require_app_data(key: str) -> Any:
    if key not in APP_DATA:
        raise RuntimeError(f"Application data '{key}' is not loaded")
    return APP_DATA[key]

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

def load_application_data() -> Dict[str, Any]:
    APP_DATA.clear()

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
        master_facility["facility_type"] = master_facility["facility_type"].apply(normalize_facility_type)
    if "specification" in master_facility.columns:
        master_facility["specification"] = master_facility["specification"].apply(normalize_spec_value)

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

    if "insert_date" not in events_bc.columns:
        events_bc["insert_date"] = pd.NaT

    events_supplier = events_bc.rename(
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

    events_receiver = events_bc.rename(
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

    relations_all = (
        links_bc
        .merge(events_supplier, on="event1_id", how="left")
        .merge(events_receiver, on="event2_id", how="left")
    )

    relations_all["insert_date_supplier"] = pd.to_datetime(relations_all["insert_date_supplier"], errors="coerce")
    relations_all["insert_date_receiver"] = pd.to_datetime(relations_all["insert_date_receiver"], errors="coerce")

    product_relations_base = relations_all[
        (relations_all["movement_type_supplier"] == 601) &
        (relations_all["movement_type_receiver"] == 101)
    ].copy()

    product_relations_base["vendor_receiver"] = (
        pd.to_numeric(product_relations_base["vendor_receiver"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", "")
        .str.strip()
    )
    product_relations_base["plant_supplier"] = product_relations_base["plant_supplier"].fillna("").astype(str).str.strip()
    product_relations_base["plant_receiver"] = product_relations_base["plant_receiver"].fillna("").astype(str).str.strip()

    product_relations_base["partner_pca_supplier"] = (
        product_relations_base["partner_pca_supplier"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    if "spb_receiver" not in product_relations_base.columns:
        product_relations_base["spb_receiver"] = ""

    product_relations_base["spb_receiver"] = (
        product_relations_base["spb_receiver"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    def resolve_vendor_grouping(row):

        product = normalize_trace_product(
            row.get("product_name_supplier", "")
        )

        vendor_id = str(
            row.get("vendor_receiver", "")
        ).strip()

        vendor_id_clean = str(vendor_id).lstrip("0").strip()

        partner_pca = str(
            row.get("partner_pca_supplier", "")
        ).strip()

        plant_supplier = str(
            row.get("plant_supplier", "")
        ).strip()

        spb_receiver = str(
        row.get("spb_receiver", "")
        ).strip()

        vendor_valid = is_supported_vendor_id(vendor_id_clean)
        vendor_is_internal = is_internal_vendor_id(vendor_id_clean)
        vendor_is_external = is_external_vendor_id(vendor_id_clean)

        pca_valid = is_valid_value(partner_pca)
        plant_supplier_valid = is_valid_value(plant_supplier)

        vendor_name = facility_name_lookup.get(
            vendor_id_clean,
            vendor_id_clean
        )

        if product in VENDOR_PARTNER_PCA_PRODUCTS:
            pca_type = (
                get_facility_type_safe(partner_pca)
                if pca_valid
                else ""
            )

            pca_name = (
                get_facility_name_safe(partner_pca)
                if pca_valid
                else ""
            )

            plant_supplier_type = (
                get_facility_type_safe(plant_supplier)
                if plant_supplier_valid
                else ""
            )

            if vendor_valid and pca_valid:
                resolved_type = pca_type or "UNKNOWN"

                return pd.Series({
                    "resolved_vendor_supplier": partner_pca,
                    "resolved_vendor_supplier_name": pca_name or partner_pca,
                    "vendor_resolution_rule": f"{product}_VENDOR_PARTNER_PCA_USE_PARTNER_PCA_AS_{resolved_type}",
                    "raw_vendor_id_for_resolution": vendor_id_clean,
                    "raw_vendor_name_for_resolution": vendor_name,
                    "resolved_supplier_type_for_resolution": resolved_type,
                })

            if vendor_valid and not pca_valid:

                if vendor_is_internal:
                    spb_facility = resolve_spb_facility(spb_receiver)

                    if is_valid_value(spb_facility["facility_id"]):
                        return pd.Series({
                            "resolved_vendor_supplier": spb_facility["facility_id"],
                            "resolved_vendor_supplier_name": spb_facility["facility_name"],
                            "vendor_resolution_rule": f"{product}_INTERNAL_VENDOR_NO_PARTNER_PCA_USE_SPB_FACILITY_{spb_facility['facility_type']}",
                            "raw_vendor_id_for_resolution": vendor_id_clean,
                            "raw_vendor_name_for_resolution": vendor_name,
                            "resolved_supplier_type_for_resolution": spb_facility["facility_type"],
                        })

                    return pd.Series({
                        "resolved_vendor_supplier": "",
                        "resolved_vendor_supplier_name": "",
                        "vendor_resolution_rule": f"{product}_INTERNAL_VENDOR_NO_PARTNER_PCA_INVALID_SPB_DROP",
                        "raw_vendor_id_for_resolution": vendor_id_clean,
                        "raw_vendor_name_for_resolution": vendor_name,
                        "resolved_supplier_type_for_resolution": "DROPPED",
                    })

                if vendor_is_external and plant_supplier_type != "MILL":
                    return pd.Series({
                        "resolved_vendor_supplier": vendor_id_clean,
                        "resolved_vendor_supplier_name": vendor_name,
                        "vendor_resolution_rule": f"{product}_EXTERNAL_VENDOR_NO_PARTNER_PCA_PLANT_{plant_supplier_type or 'UNKNOWN'}_KEEP_VENDOR",
                        "raw_vendor_id_for_resolution": vendor_id_clean,
                        "raw_vendor_name_for_resolution": vendor_name,
                        "resolved_supplier_type_for_resolution": "VENDOR",
                    })

                return pd.Series({
                    "resolved_vendor_supplier": "",
                    "resolved_vendor_supplier_name": "",
                    "vendor_resolution_rule": f"{product}_VENDOR_NO_PARTNER_PCA_PLANT_MILL_OR_UNSUPPORTED_DROP",
                    "raw_vendor_id_for_resolution": vendor_id_clean,
                    "raw_vendor_name_for_resolution": vendor_name,
                    "resolved_supplier_type_for_resolution": "DROPPED",
                })

            return pd.Series({
                "resolved_vendor_supplier": "",
                "resolved_vendor_supplier_name": "",
                "vendor_resolution_rule": "CPO_PKO_NO_VENDOR_NO_VENDOR_EDGE",
                "raw_vendor_id_for_resolution": vendor_id_clean,
                "raw_vendor_name_for_resolution": vendor_name,
                "resolved_supplier_type_for_resolution": "UNKNOWN",
            })

        if vendor_valid:
            return pd.Series({
                "resolved_vendor_supplier": vendor_id_clean,
                "resolved_vendor_supplier_name": vendor_name,
                "vendor_resolution_rule": "GENERAL_VENDOR",
                "raw_vendor_id_for_resolution": vendor_id_clean,
                "raw_vendor_name_for_resolution": vendor_name,
                "resolved_supplier_type_for_resolution": "VENDOR",
            })

        return pd.Series({
            "resolved_vendor_supplier": "",
            "resolved_vendor_supplier_name": "",
            "vendor_resolution_rule": "NO_VALID_VENDOR",
            "raw_vendor_id_for_resolution": vendor_id_clean,
            "raw_vendor_name_for_resolution": vendor_name,
            "resolved_supplier_type_for_resolution": "UNKNOWN",
        })

    vendor_resolution = product_relations_base.apply(
        resolve_vendor_grouping,
        axis=1
    )

    product_relations_base = pd.concat(
        [product_relations_base, vendor_resolution],
        axis=1,
    )




    ffb_relations_raw = relations_all[
        (relations_all["movement_type_receiver"] == 101) &
        (relations_all["product_name_receiver"] == "FFB")
    ].copy()

    ffb_relations = (
        ffb_relations_raw[
            ["qty", "plant_receiver", "estate_receiver", "vendor_receiver","insert_date_supplier",
                "insert_date_receiver",]
        ]
        .rename(
            columns={
                "plant_receiver": "mill",
                "qty": "quantity",
            }
        )
        .copy()
    )

    ffb_relations["mill"] = (
        ffb_relations["mill"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    ffb_relations["estate_receiver"] = (
        ffb_relations["estate_receiver"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    ffb_relations["vendor_receiver"] = (
        pd.to_numeric(ffb_relations["vendor_receiver"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", "")
        .str.strip()
    )

    def resolve_ffb_supplier(row: pd.Series) -> pd.Series:
        estate_id = str(row.get("estate_receiver", "")).strip()
        vendor_id = str(row.get("vendor_receiver", "")).strip()

        estate_type = normalize_facility_type(
            facility_type_lookup.get(estate_id, "UNKNOWN")
        )

        if estate_id and estate_type == "ESTATE":
            return pd.Series({
                "supplier": estate_id,
                "supplier_source_kind": "ESTATE",
                "raw_estate_receiver": estate_id,
                "raw_vendor_receiver": vendor_id,
                "ffb_resolution_rule": "ESTATE_VALID_USE_ESTATE",
            })

        if vendor_id:
            return pd.Series({
                "supplier": vendor_id,
                "supplier_source_kind": "VENDOR",
                "raw_estate_receiver": estate_id,
                "raw_vendor_receiver": vendor_id,
                "ffb_resolution_rule": (
                    "ESTATE_UNKNOWN_USE_VENDOR"
                    if estate_id
                    else "NO_ESTATE_USE_VENDOR"
                ),
            })

        if estate_id:
            return pd.Series({
                "supplier": estate_id,
                "supplier_source_kind": "UNKNOWN_ESTATE",
                "raw_estate_receiver": estate_id,
                "raw_vendor_receiver": vendor_id,
                "ffb_resolution_rule": "ESTATE_UNKNOWN_NO_VENDOR_USE_ESTATE_AS_UNKNOWN",
            })

        return pd.Series({
            "supplier": "",
            "supplier_source_kind": "UNKNOWN",
            "raw_estate_receiver": estate_id,
            "raw_vendor_receiver": vendor_id,
            "ffb_resolution_rule": "NO_SUPPLIER",
        })


    ffb_resolution = ffb_relations.apply(resolve_ffb_supplier, axis=1)

    ffb_relations = pd.concat(
        [ffb_relations, ffb_resolution],
        axis=1,
    )

    ffb_relations["supplier"] = (
        ffb_relations["supplier"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    ffb_relations = ffb_relations[
        (ffb_relations["mill"] != "") &
        (ffb_relations["supplier"] != "")
    ].copy()

    ffb_flow = (
        ffb_relations
        .groupby(["mill", "supplier", "supplier_source_kind"], as_index=False)
        .agg(
            quantity=("quantity", "sum"),
            raw_estate_receivers=(
                "raw_estate_receiver",
                lambda x: sorted(set(str(v) for v in x if str(v).strip() != ""))[:10],
            ),
            raw_vendor_receivers=(
                "raw_vendor_receiver",
                lambda x: sorted(set(str(v) for v in x if str(v).strip() != ""))[:10],
            ),
            ffb_resolution_rules=(
                "ffb_resolution_rule",
                lambda x: "+".join(
                    sorted(set(str(v) for v in x if str(v).strip() != ""))
                ),
            ),
        )
    )
    product_relations_physical_base = product_relations_base.copy()

    mask_vendor_partner_pca_product = (
        product_relations_physical_base["product_name_supplier"].apply(normalize_trace_product).isin(VENDOR_PARTNER_PCA_PRODUCTS)
        &
        product_relations_physical_base["vendor_receiver"].fillna("").astype(str).str.strip().ne("")
        &
        product_relations_physical_base["partner_pca_supplier"].fillna("").astype(str).str.strip().ne("")
    )

    product_relations_physical_base.loc[
        mask_vendor_partner_pca_product,
        "plant_supplier"
    ] = product_relations_physical_base.loc[
        mask_vendor_partner_pca_product,
        "partner_pca_supplier"
    ]

    product_relations_physical = (
        product_relations_physical_base[["plant_supplier", "plant_receiver", "product_name_supplier", "qty"]]
        .rename(
            columns={
                "plant_supplier": "supplier",
                "plant_receiver": "facility",
                "product_name_supplier": "product",
                "qty": "quantity",
            }
        )
        .copy()
    )
    product_relations_physical["supplier_source_kind"] = "PHYSICAL"

    product_relations_physical["resolved_vendor_supplier_name"] = ""
    product_relations_physical["vendor_resolution_rule"] = "PHYSICAL"
    product_relations_physical["raw_vendor_id_for_resolution"] = ""
    product_relations_physical["raw_vendor_name_for_resolution"] = ""
    product_relations_physical["resolved_supplier_type_for_resolution"] = "PHYSICAL"


    product_relations_vendor = (
        product_relations_base[
            product_relations_base["resolved_vendor_supplier"].fillna("").astype(str).str.strip() != ""
        ]
        [[
            "resolved_vendor_supplier",
            "resolved_vendor_supplier_name",
            "vendor_resolution_rule",
            "raw_vendor_id_for_resolution",
            "raw_vendor_name_for_resolution",
            "resolved_supplier_type_for_resolution",
            "plant_receiver",
            "product_name_supplier",
            "qty",
        ]]
        .rename(
            columns={
                "resolved_vendor_supplier": "supplier",
                "plant_receiver": "facility",
                "product_name_supplier": "product",
                "qty": "quantity",
            }
        )
        .copy()
    )

    product_relations_vendor["supplier_source_kind"] = product_relations_vendor[
        "resolved_supplier_type_for_resolution"
    ].fillna("VENDOR").astype(str).str.upper()

    vendor_cpo_pko_receipt_raw = relations_all[
        (relations_all["movement_type_receiver"] == 101)
        &
        (
            relations_all["product_name_receiver"]
            .apply(normalize_trace_product)
            .isin(VENDOR_PARTNER_PCA_PRODUCTS)
        )
    ].copy()

    product_relations_vendor_101_only = (
        vendor_cpo_pko_receipt_raw[
            [
                "qty",
                "plant_supplier",
                "plant_receiver",
                "partner_pca_supplier",
                "spb_receiver",
                "vendor_receiver",
                "product_name_receiver",
            ]
        ]
        .rename(
            columns={
                "plant_supplier": "plant_supplier",
                "plant_receiver": "facility",
                "partner_pca_supplier": "partner_pca",
                "spb_receiver": "spb",
                "vendor_receiver": "vendor_id",
                "product_name_receiver": "product",
                "qty": "quantity",
            }
        )
        .copy()
    )

    product_relations_vendor_101_only["vendor_id"] = (
        pd.to_numeric(product_relations_vendor_101_only["vendor_id"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", "")
        .str.strip()
    )

    product_relations_vendor_101_only["partner_pca"] = (
        product_relations_vendor_101_only["partner_pca"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    product_relations_vendor_101_only["plant_supplier"] = (
        product_relations_vendor_101_only["plant_supplier"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    product_relations_vendor_101_only["facility"] = (
        product_relations_vendor_101_only["facility"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    product_relations_vendor_101_only["product"] = (
        product_relations_vendor_101_only["product"]
        .apply(normalize_trace_product)
    )

    product_relations_vendor_101_only["quantity"] = pd.to_numeric(
        product_relations_vendor_101_only["quantity"],
        errors="coerce"
    ).fillna(0.0)

    product_relations_vendor_101_only["partner_pca_type"] = (
        product_relations_vendor_101_only["partner_pca"]
        .map(lambda x: get_facility_type_safe(x) if is_valid_value(x) else "")
    )

    product_relations_vendor_101_only["partner_pca_name"] = (
        product_relations_vendor_101_only["partner_pca"]
        .map(lambda x: get_facility_name_safe(x) if is_valid_value(x) else "")
    )

    product_relations_vendor_101_only["plant_supplier_type"] = (
        product_relations_vendor_101_only["plant_supplier"]
        .map(lambda x: get_facility_type_safe(x) if is_valid_value(x) else "")
    )

    product_relations_vendor_101_only["spb"] = (
        product_relations_vendor_101_only["spb"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    def resolve_vendor_receipt_101_supplier(row: pd.Series) -> pd.Series:
        vendor_id = str(row.get("vendor_id", "")).strip()
        vendor_name = facility_name_lookup.get(vendor_id, vendor_id)

        partner_pca = str(row.get("partner_pca", "")).strip()
        partner_pca_type = str(row.get("partner_pca_type", "")).strip()
        partner_pca_name = str(row.get("partner_pca_name", "")).strip()

        plant_supplier_type = str(row.get("plant_supplier_type", "")).strip()

        vendor_valid = is_supported_vendor_id(vendor_id)
        spb_value = str(row.get("spb", "")).strip()
        vendor_is_internal = is_internal_vendor_id(vendor_id)
        vendor_is_external = is_external_vendor_id(vendor_id)
        pca_valid = is_valid_value(partner_pca)

        if vendor_valid and pca_valid:
            resolved_type = partner_pca_type or "UNKNOWN"

            return pd.Series({
                "supplier": partner_pca,
                "resolved_vendor_supplier_name": partner_pca_name or partner_pca,
                "vendor_resolution_rule": f"{str(row.get('product', '')).upper()}_VENDOR_101_PARTNER_PCA_USE_PARTNER_PCA_AS_{resolved_type}",
                "raw_vendor_id_for_resolution": vendor_id,
                "raw_vendor_name_for_resolution": vendor_name,
                "resolved_supplier_type_for_resolution": resolved_type,
            })

        if vendor_valid and not pca_valid:

            product_code = str(row.get("product", "")).upper()

            if vendor_is_internal:
                spb_facility = resolve_spb_facility(spb_value)

                if is_valid_value(spb_facility["facility_id"]):
                    return pd.Series({
                        "supplier": spb_facility["facility_id"],
                        "resolved_vendor_supplier_name": spb_facility["facility_name"],
                        "vendor_resolution_rule": f"{product_code}_INTERNAL_VENDOR_101_NO_PARTNER_PCA_USE_SPB_FACILITY_{spb_facility['facility_type']}",
                        "raw_vendor_id_for_resolution": vendor_id,
                        "raw_vendor_name_for_resolution": vendor_name,
                        "resolved_supplier_type_for_resolution": spb_facility["facility_type"],
                    })

                return pd.Series({
                    "supplier": "",
                    "resolved_vendor_supplier_name": "",
                    "vendor_resolution_rule": f"{product_code}_INTERNAL_VENDOR_101_NO_PARTNER_PCA_INVALID_SPB_DROP",
                    "raw_vendor_id_for_resolution": vendor_id,
                    "raw_vendor_name_for_resolution": vendor_name,
                    "resolved_supplier_type_for_resolution": "DROPPED",
                })

            if vendor_is_external and plant_supplier_type != "MILL":
                return pd.Series({
                    "supplier": vendor_id,
                    "resolved_vendor_supplier_name": vendor_name,
                    "vendor_resolution_rule": f"{product_code}_EXTERNAL_VENDOR_101_NO_PARTNER_PCA_PLANT_{plant_supplier_type or 'UNKNOWN'}_KEEP_VENDOR",
                    "raw_vendor_id_for_resolution": vendor_id,
                    "raw_vendor_name_for_resolution": vendor_name,
                    "resolved_supplier_type_for_resolution": "VENDOR",
                })

            return pd.Series({
                "supplier": "",
                "resolved_vendor_supplier_name": "",
                "vendor_resolution_rule": f"{product_code}_VENDOR_101_NO_PARTNER_PCA_PLANT_MILL_OR_UNSUPPORTED_DROP",
                "raw_vendor_id_for_resolution": vendor_id,
                "raw_vendor_name_for_resolution": vendor_name,
                "resolved_supplier_type_for_resolution": "DROPPED",
            })

        return pd.Series({
            "supplier": "",
            "resolved_vendor_supplier_name": "",
            "vendor_resolution_rule": "CPO_PKO_VENDOR_101_NO_VALID_VENDOR",
            "raw_vendor_id_for_resolution": vendor_id,
            "raw_vendor_name_for_resolution": vendor_name,
            "resolved_supplier_type_for_resolution": "UNKNOWN",
        })

    vendor_101_resolution = product_relations_vendor_101_only.apply(
        resolve_vendor_receipt_101_supplier,
        axis=1,
    )

    product_relations_vendor_101_only = pd.concat(
        [product_relations_vendor_101_only, vendor_101_resolution],
        axis=1,
    )

    product_relations_vendor_101_only = product_relations_vendor_101_only[
        (product_relations_vendor_101_only["supplier"].fillna("").astype(str).str.strip() != "")
        &
        (product_relations_vendor_101_only["facility"] != "")
        &
        (product_relations_vendor_101_only["product"].isin(VENDOR_PARTNER_PCA_PRODUCTS))
        &
        (product_relations_vendor_101_only["quantity"] > 0)
    ].copy()

    product_relations_vendor_101_only["supplier_source_kind"] = (
        product_relations_vendor_101_only["resolved_supplier_type_for_resolution"]
        .fillna("VENDOR")
        .astype(str)
        .str.upper()
    )

    product_relations = pd.concat(
        [
            product_relations_physical,
            product_relations_vendor,
            product_relations_vendor_101_only,
        ],
        ignore_index=True,
    )

    product_flow = (
        product_relations
        .groupby(["facility", "product", "supplier", "supplier_source_kind"], as_index=False)
        .agg(
            quantity=("quantity", "sum"),
            raw_vendor_ids=(
                "raw_vendor_id_for_resolution",
                lambda x: sorted(set(str(v) for v in x if str(v).strip() != ""))[:10]
                if "raw_vendor_id_for_resolution" in product_relations.columns
                else []
            ),
            raw_vendor_names=(
                "raw_vendor_name_for_resolution",
                lambda x: sorted(set(str(v) for v in x if str(v).strip() != ""))[:10]
                if "raw_vendor_name_for_resolution" in product_relations.columns
                else []
            ),
            vendor_resolution_rules=(
                "vendor_resolution_rule",
                lambda x: sorted(set(str(v) for v in x if str(v).strip() != ""))[:10]
                if "vendor_resolution_rule" in product_relations.columns
                else []
            ),
        )
    )

    product_flow["facility"] = product_flow["facility"].fillna("").astype(str).str.strip()
    product_flow["supplier"] = product_flow["supplier"].fillna("").astype(str).str.strip()
    product_flow["supplier_source_kind"] = product_flow["supplier_source_kind"].fillna("").astype(str).str.upper()

    product_flow = product_flow[
        (product_flow["facility"] != "") &
        (product_flow["supplier"] != "")
    ].copy()

    product_flow["product"] = product_flow["product"].apply(normalize_trace_product)

    product_flow["total_supply"] = product_flow.groupby(["facility", "product"])["quantity"].transform("sum")
    product_flow["probability"] = product_flow["quantity"]  / product_flow["total_supply"]

    ffb_flow["total_supply"] = ffb_flow.groupby("mill")["quantity"].transform("sum")
    ffb_flow["probability"] = ffb_flow["quantity"] / ffb_flow["total_supply"]

    product_flow = (
        product_flow
        .merge(facility_lookup, left_on="supplier", right_on="facility_id", how="left")
        .rename(columns={
            "facility_name": "supplier_name",
            "facility_type": "supplier_type",
            "specification": "supplier_spec",
        })
        .drop(columns=["facility_id"])
    )

    product_flow = (
        product_flow
        .merge(facility_lookup, left_on="facility", right_on="facility_id", how="left")
        .rename(columns={
            "facility_name": "facility_name",
            "facility_type": "facility_type",
            "specification": "facility_spec",
        })
        .drop(columns=["facility_id"])
    )

    ffb_flow = (
        ffb_flow
        .merge(facility_lookup, left_on="supplier", right_on="facility_id", how="left")
        .rename(columns={
            "facility_name": "supplier_name",
            "facility_type": "supplier_type",
            "specification": "supplier_spec",
        })
        .drop(columns=["facility_id"])
    )

    ffb_flow = (
        ffb_flow
        .merge(facility_lookup, left_on="mill", right_on="facility_id", how="left")
        .rename(columns={
            "facility_name": "mill_name",
            "facility_type": "mill_type",
            "specification": "mill_spec",
        })
        .drop(columns=["facility_id"])
    )


    product_flow["facility"] = product_flow["facility"].astype(str)
    product_flow["supplier"] = product_flow["supplier"].astype(str)
    product_flow["supplier_type"] = product_flow["supplier_type"].fillna("").astype(str).apply(normalize_facility_type)
    product_flow["supplier_spec"] = product_flow["supplier_spec"].fillna("").astype(str).apply(normalize_spec_value)

    product_flow.loc[
        product_flow["supplier"].astype(str).str.startswith("100")
        &
        product_flow["supplier_source_kind"].astype(str).str.upper().eq("VENDOR"),
        "supplier_type"
    ] = "VENDOR"

    ffb_flow["mill"] = ffb_flow["mill"].astype(str)
    ffb_flow["supplier"] = ffb_flow["supplier"].astype(str)
    ffb_flow["supplier_source_kind"] = ffb_flow["supplier_source_kind"].fillna("").astype(str).str.upper()

    ffb_flow["mill_type"] = ffb_flow["mill_type"].fillna("").astype(str).apply(normalize_facility_type)
    ffb_flow["supplier_type"] = ffb_flow["supplier_type"].fillna("").astype(str).apply(normalize_facility_type)

    ffb_flow["mill_spec"] = ffb_flow["mill_spec"].fillna("").astype(str).apply(normalize_spec_value)
    ffb_flow["supplier_spec"] = ffb_flow["supplier_spec"].fillna("").astype(str).apply(normalize_spec_value)

    product_flow = product_flow.loc[:, ~product_flow.columns.duplicated()]
    ffb_flow = ffb_flow.loc[:, ~ffb_flow.columns.duplicated()]

    tolling_relations_raw = relations_all[
        (relations_all["movement_type_supplier"] == 961) &
        (relations_all["movement_type_receiver"] == 601)
    ].copy()

    if not tolling_relations_raw.empty:
        tolling_relations_raw["supplier_product"] = (
            tolling_relations_raw["product_name_supplier"]
            .apply(normalize_trace_product)
        )

        tolling_relations_raw["receiver_product"] = (
            tolling_relations_raw["product_name_receiver"]
            .apply(normalize_trace_product)
        )

        tolling_relations_raw["plant_supplier"] = (
            tolling_relations_raw["plant_supplier"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        tolling_relations_raw["plant_receiver"] = (
            tolling_relations_raw["plant_receiver"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        tolling_relations_raw["qty"] = pd.to_numeric(
            tolling_relations_raw["qty"],
            errors="coerce"
        ).fillna(0.0)

        tolling_relations_raw = tolling_relations_raw[
            (tolling_relations_raw["supplier_product"] == "CPO") &
            (tolling_relations_raw["receiver_product"] == "CPO") &
            (tolling_relations_raw["plant_supplier"] != "") &
            (tolling_relations_raw["plant_receiver"] != "") &
            (tolling_relations_raw["qty"] > 0)
        ].copy()

        tolling_flow = (
            tolling_relations_raw
            .rename(
                columns={
                    "plant_supplier": "supplier",
                    "plant_receiver": "facility",
                    "supplier_product": "product",
                    "qty": "quantity",
                }
            )
            [["facility", "product", "supplier", "quantity"]]
            .copy()
        )

        tolling_flow = (
            tolling_flow
            .groupby(["facility", "product", "supplier"], as_index=False)
            .agg(quantity=("quantity", "sum"))
        )
    else:
        tolling_flow = pd.DataFrame(
            columns=["facility", "product", "supplier", "quantity"]
        )

    if not tolling_flow.empty:
        tolling_flow = (
            tolling_flow
            .merge(facility_lookup, left_on="supplier", right_on="facility_id", how="left")
            .rename(columns={
                "facility_name": "supplier_name",
                "facility_type": "supplier_type",
                "specification": "supplier_spec",
            })
            .drop(columns=["facility_id"])
        )

        tolling_flow = (
            tolling_flow
            .merge(facility_lookup, left_on="facility", right_on="facility_id", how="left")
            .rename(columns={
                "facility_name": "facility_name",
                "facility_type": "facility_type",
                "specification": "facility_spec",
            })
            .drop(columns=["facility_id"])
        )

        tolling_flow["facility"] = tolling_flow["facility"].astype(str).str.strip()
        tolling_flow["supplier"] = tolling_flow["supplier"].astype(str).str.strip()
        tolling_flow["product"] = tolling_flow["product"].astype(str).str.upper().str.strip()

        tolling_flow["supplier_type"] = (
            tolling_flow["supplier_type"]
            .fillna("")
            .astype(str)
            .apply(normalize_facility_type)
        )

        tolling_flow["facility_type"] = (
            tolling_flow["facility_type"]
            .fillna("")
            .astype(str)
            .apply(normalize_facility_type)
        )

        tolling_flow["supplier_spec"] = (
            tolling_flow["supplier_spec"]
            .fillna("")
            .astype(str)
            .apply(normalize_spec_value)
        )

        tolling_flow["facility_spec"] = (
            tolling_flow["facility_spec"]
            .fillna("")
            .astype(str)
            .apply(normalize_spec_value)
        )

        tolling_flow = tolling_flow[
            (tolling_flow["supplier_type"] == "MILL") &
            (tolling_flow["facility_type"] == "MILL") &
            (tolling_flow["product"] == "CPO")
        ].copy()

        if not tolling_flow.empty:
            tolling_flow["total_supply"] = (
                tolling_flow
                .groupby(["facility", "product"])["quantity"]
                .transform("sum")
            )

            tolling_flow["probability"] = np.where(
                tolling_flow["total_supply"] > 0,
                tolling_flow["quantity"] / tolling_flow["total_supply"],
                0.0,
            )

            tolling_flow["supplier_source_kind"] = "TOLLING_PROCESSING_MILL"
            tolling_flow["selection_priority"] = 0
    else:
        tolling_flow["supplier_name"] = ""
        tolling_flow["supplier_type"] = ""
        tolling_flow["supplier_spec"] = ""
        tolling_flow["facility_name"] = ""
        tolling_flow["facility_type"] = ""
        tolling_flow["facility_spec"] = ""
        tolling_flow["probability"] = 0.0
        tolling_flow["supplier_source_kind"] = "TOLLING_PROCESSING_MILL"
        tolling_flow["selection_priority"] = 0

    mill_ids = set(ffb_flow["mill"].astype(str).unique())

    set_app_data("master_facility", master_facility)
    set_app_data("events_bc", events_bc)
    set_app_data("links_bc", links_bc)
    set_app_data("facility_lookup", facility_lookup)
    set_app_data("facility_name_lookup", facility_name_lookup)
    set_app_data("facility_type_lookup", facility_type_lookup)
    set_app_data("facility_spec_lookup", facility_spec_lookup)
    set_app_data("plant_to_refinery", plant_to_refinery)
    set_app_data("relations_all", relations_all)
    set_app_data("product_relations", product_relations)
    set_app_data("product_flow", product_flow)
    set_app_data("ffb_relations", ffb_relations)
    set_app_data("ffb_flow", ffb_flow)
    set_app_data("tolling_flow", tolling_flow)
    set_app_data("mill_ids", mill_ids)

    return APP_DATA