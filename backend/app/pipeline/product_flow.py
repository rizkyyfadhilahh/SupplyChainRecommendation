import pandas as pd
import numpy as np
from typing import Dict, Any

from app.config import VENDOR_PARTNER_PCA_PRODUCTS
from app.state import get_app_data
from app.pipeline.utils import (
    normalize_facility_type,
    vectorize_normalize_facility_type,
    vectorize_normalize_spec_value,
    vectorize_normalize_trace_product,
    is_valid_value,
    is_supported_vendor_id,
    is_internal_vendor_id,
    is_external_vendor_id,
    resolve_spb_facility,
    get_facility_type_safe,
    get_facility_name_safe
)
from app.utils import normalize_trace_product

def process_product_relations(relations_all: pd.DataFrame, facility_lookup: pd.DataFrame, events_supplier: pd.DataFrame, events_receiver: pd.DataFrame) -> pd.DataFrame:
    facility_name_lookup = get_app_data("facility_name_lookup", {})
    
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

    def resolve_vendor_grouping(prod_supplier, vend_receiver, pca_supplier, plant_supp, spb_rec) -> dict:

        product = normalize_trace_product(prod_supplier)
        vendor_id = str(vend_receiver).strip() if vend_receiver is not None else ""
        vendor_id_clean = vendor_id.lstrip("0").strip()
        partner_pca = str(pca_supplier).strip() if pca_supplier is not None else ""
        plant_supplier = str(plant_supp).strip() if plant_supp is not None else ""
        spb_receiver = str(spb_rec).strip() if spb_rec is not None else ""

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

                return {
                    "resolved_vendor_supplier": partner_pca,
                    "resolved_vendor_supplier_name": pca_name or partner_pca,
                    "vendor_resolution_rule": f"{product}_VENDOR_PARTNER_PCA_USE_PARTNER_PCA_AS_{resolved_type}",
                    "raw_vendor_id_for_resolution": vendor_id_clean,
                    "raw_vendor_name_for_resolution": vendor_name,
                    "resolved_supplier_type_for_resolution": resolved_type,
                }

            if vendor_valid and not pca_valid:

                if vendor_is_internal:
                    spb_facility = resolve_spb_facility(spb_receiver)

                    if is_valid_value(spb_facility["facility_id"]):
                        return {
                            "resolved_vendor_supplier": spb_facility["facility_id"],
                            "resolved_vendor_supplier_name": spb_facility["facility_name"],
                            "vendor_resolution_rule": f"{product}_INTERNAL_VENDOR_NO_PARTNER_PCA_USE_SPB_FACILITY_{spb_facility['facility_type']}",
                            "raw_vendor_id_for_resolution": vendor_id_clean,
                            "raw_vendor_name_for_resolution": vendor_name,
                            "resolved_supplier_type_for_resolution": spb_facility["facility_type"],
                        }

                    return {
                        "resolved_vendor_supplier": "",
                        "resolved_vendor_supplier_name": "",
                        "vendor_resolution_rule": f"{product}_INTERNAL_VENDOR_NO_PARTNER_PCA_INVALID_SPB_DROP",
                        "raw_vendor_id_for_resolution": vendor_id_clean,
                        "raw_vendor_name_for_resolution": vendor_name,
                        "resolved_supplier_type_for_resolution": "DROPPED",
                    }

                if vendor_is_external and plant_supplier_type != "MILL":
                    return {
                        "resolved_vendor_supplier": vendor_id_clean,
                        "resolved_vendor_supplier_name": vendor_name,
                        "vendor_resolution_rule": f"{product}_EXTERNAL_VENDOR_NO_PARTNER_PCA_PLANT_{plant_supplier_type or 'UNKNOWN'}_KEEP_VENDOR",
                        "raw_vendor_id_for_resolution": vendor_id_clean,
                        "raw_vendor_name_for_resolution": vendor_name,
                        "resolved_supplier_type_for_resolution": "VENDOR",
                    }

                return {
                    "resolved_vendor_supplier": "",
                    "resolved_vendor_supplier_name": "",
                    "vendor_resolution_rule": f"{product}_VENDOR_NO_PARTNER_PCA_PLANT_MILL_OR_UNSUPPORTED_DROP",
                    "raw_vendor_id_for_resolution": vendor_id_clean,
                    "raw_vendor_name_for_resolution": vendor_name,
                    "resolved_supplier_type_for_resolution": "DROPPED",
                }

            return {
                "resolved_vendor_supplier": "",
                "resolved_vendor_supplier_name": "",
                "vendor_resolution_rule": "CPO_PKO_NO_VENDOR_NO_VENDOR_EDGE",
                "raw_vendor_id_for_resolution": vendor_id_clean,
                "raw_vendor_name_for_resolution": vendor_name,
                "resolved_supplier_type_for_resolution": "UNKNOWN",
            }

        if vendor_valid:
            return {
                "resolved_vendor_supplier": vendor_id_clean,
                "resolved_vendor_supplier_name": vendor_name,
                "vendor_resolution_rule": "GENERAL_VENDOR",
                "raw_vendor_id_for_resolution": vendor_id_clean,
                "raw_vendor_name_for_resolution": vendor_name,
                "resolved_supplier_type_for_resolution": "VENDOR",
            }

        return {
            "resolved_vendor_supplier": "",
            "resolved_vendor_supplier_name": "",
            "vendor_resolution_rule": "NO_VALID_VENDOR",
            "raw_vendor_id_for_resolution": vendor_id_clean,
            "raw_vendor_name_for_resolution": vendor_name,
            "resolved_supplier_type_for_resolution": "UNKNOWN",
        }

    vendor_resolution_data = [
        resolve_vendor_grouping(prod, vend, pca, plant, spb)
        for prod, vend, pca, plant, spb in zip(
            product_relations_base["product_name_supplier"],
            product_relations_base["vendor_receiver"],
            product_relations_base["partner_pca_supplier"],
            product_relations_base["plant_supplier"],
            product_relations_base["spb_receiver"]
        )
    ]
    vendor_resolution = pd.DataFrame(vendor_resolution_data, index=product_relations_base.index)

    product_relations_base = pd.concat(
        [product_relations_base, vendor_resolution],
        axis=1,
    )

    product_relations_physical_base = product_relations_base.copy()

    mask_vendor_partner_pca_product = (
        product_relations_physical_base["product_name_supplier"].pipe(vectorize_normalize_trace_product).isin(VENDOR_PARTNER_PCA_PRODUCTS)
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
            .pipe(vectorize_normalize_trace_product)
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

    product_relations_vendor_101_only["partner_pca"] = product_relations_vendor_101_only["partner_pca"].fillna("").astype(str).str.strip()
    product_relations_vendor_101_only["plant_supplier"] = product_relations_vendor_101_only["plant_supplier"].fillna("").astype(str).str.strip()
    product_relations_vendor_101_only["facility"] = product_relations_vendor_101_only["facility"].fillna("").astype(str).str.strip()
    product_relations_vendor_101_only["product"] = product_relations_vendor_101_only["product"].pipe(vectorize_normalize_trace_product)
    product_relations_vendor_101_only["quantity"] = pd.to_numeric(product_relations_vendor_101_only["quantity"], errors="coerce").fillna(0.0)
    
    product_relations_vendor_101_only["partner_pca_type"] = product_relations_vendor_101_only["partner_pca"].map(lambda x: get_facility_type_safe(x) if is_valid_value(x) else "")
    product_relations_vendor_101_only["partner_pca_name"] = product_relations_vendor_101_only["partner_pca"].map(lambda x: get_facility_name_safe(x) if is_valid_value(x) else "")
    product_relations_vendor_101_only["plant_supplier_type"] = product_relations_vendor_101_only["plant_supplier"].map(lambda x: get_facility_type_safe(x) if is_valid_value(x) else "")
    product_relations_vendor_101_only["spb"] = product_relations_vendor_101_only["spb"].fillna("").astype(str).str.strip()

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

    return product_relations

def process_product_flow(product_relations: pd.DataFrame, facility_lookup: pd.DataFrame) -> pd.DataFrame:
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

    product_flow["product"] = product_flow["product"].pipe(vectorize_normalize_trace_product)

    product_flow["total_supply"] = product_flow.groupby(["facility", "product"])["quantity"].transform("sum")
    product_flow["probability"] = product_flow["quantity"]  / product_flow["total_supply"]

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

    product_flow["facility"] = product_flow["facility"].astype(str)
    product_flow["supplier"] = product_flow["supplier"].astype(str)
    product_flow["supplier_type"] = product_flow["supplier_type"].fillna("").astype(str).pipe(vectorize_normalize_facility_type)
    product_flow["supplier_spec"] = product_flow["supplier_spec"].fillna("").astype(str).pipe(vectorize_normalize_spec_value)

    product_flow.loc[
        product_flow["supplier"].astype(str).str.startswith("100")
        &
        product_flow["supplier_source_kind"].astype(str).str.upper().eq("VENDOR"),
        "supplier_type"
    ] = "VENDOR"
    
    product_flow = product_flow.loc[:, ~product_flow.columns.duplicated()]

    return product_flow
