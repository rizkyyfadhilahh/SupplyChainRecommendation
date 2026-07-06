import pandas as pd
from typing import Dict, Any
from app.pipeline.utils import normalize_facility_type, vectorize_normalize_facility_type, vectorize_normalize_spec_value
from app.state import get_app_data

def process_ffb_relations(relations_all: pd.DataFrame) -> pd.DataFrame:
    ffb_relations_raw = relations_all[
        (relations_all["movement_type_receiver"] == 101) &
        (relations_all["product_name_receiver"] == "FFB")
    ].copy()

    ffb_relations = (
        ffb_relations_raw[
            ["qty", "plant_receiver", "estate_receiver", "vendor_receiver", "insert_date_supplier", "insert_date_receiver"]
        ]
        .rename(
            columns={
                "plant_receiver": "mill",
                "qty": "quantity",
            }
        )
        .copy()
    )

    ffb_relations["mill"] = ffb_relations["mill"].fillna("").astype(str).str.strip()
    ffb_relations["estate_receiver"] = ffb_relations["estate_receiver"].fillna("").astype(str).str.strip()
    ffb_relations["vendor_receiver"] = (
        pd.to_numeric(ffb_relations["vendor_receiver"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", "")
        .str.strip()
    )

    facility_type_lookup = get_app_data("facility_type_lookup", {})

    def resolve_ffb_supplier(est_rec, vend_rec) -> dict:
        estate_id = str(est_rec).strip() if est_rec is not None else ""
        vendor_id = str(vend_rec).strip() if vend_rec is not None else ""

        estate_type = normalize_facility_type(
            facility_type_lookup.get(estate_id, "UNKNOWN")
        )

        if estate_id and estate_type == "ESTATE":
            return {
                "supplier": estate_id,
                "supplier_source_kind": "ESTATE",
                "raw_estate_receiver": estate_id,
                "raw_vendor_receiver": vendor_id,
                "ffb_resolution_rule": "ESTATE_VALID_USE_ESTATE",
            }

        if vendor_id:
            return {
                "supplier": vendor_id,
                "supplier_source_kind": "VENDOR",
                "raw_estate_receiver": estate_id,
                "raw_vendor_receiver": vendor_id,
                "ffb_resolution_rule": (
                    "ESTATE_UNKNOWN_USE_VENDOR"
                    if estate_id
                    else "NO_ESTATE_USE_VENDOR"
                ),
            }

        if estate_id:
            return {
                "supplier": estate_id,
                "supplier_source_kind": "UNKNOWN_ESTATE",
                "raw_estate_receiver": estate_id,
                "raw_vendor_receiver": vendor_id,
                "ffb_resolution_rule": "ESTATE_UNKNOWN_NO_VENDOR_USE_ESTATE_AS_UNKNOWN",
            }

        return {
            "supplier": "",
            "supplier_source_kind": "UNKNOWN",
            "raw_estate_receiver": estate_id,
            "raw_vendor_receiver": vendor_id,
            "ffb_resolution_rule": "NO_SUPPLIER",
        }

    ffb_resolution_data = [
        resolve_ffb_supplier(est, vend)
        for est, vend in zip(
            ffb_relations["estate_receiver"],
            ffb_relations["vendor_receiver"]
        )
    ]
    ffb_resolution = pd.DataFrame(ffb_resolution_data, index=ffb_relations.index)

    ffb_relations = pd.concat([ffb_relations, ffb_resolution], axis=1)
    ffb_relations["supplier"] = ffb_relations["supplier"].fillna("").astype(str).str.strip()

    ffb_relations = ffb_relations[
        (ffb_relations["mill"] != "") &
        (ffb_relations["supplier"] != "")
    ].copy()

    return ffb_relations

def process_ffb_flow(ffb_relations: pd.DataFrame, facility_lookup: pd.DataFrame) -> pd.DataFrame:
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

    ffb_flow["total_supply"] = ffb_flow.groupby("mill")["quantity"].transform("sum")
    ffb_flow["probability"] = ffb_flow["quantity"] / ffb_flow["total_supply"]

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

    ffb_flow["mill"] = ffb_flow["mill"].astype(str)
    ffb_flow["supplier"] = ffb_flow["supplier"].astype(str)
    ffb_flow["supplier_source_kind"] = ffb_flow["supplier_source_kind"].fillna("").astype(str).str.upper()

    ffb_flow["mill_type"] = ffb_flow["mill_type"].fillna("").astype(str).pipe(vectorize_normalize_facility_type)
    ffb_flow["supplier_type"] = ffb_flow["supplier_type"].fillna("").astype(str).pipe(vectorize_normalize_facility_type)

    ffb_flow["mill_spec"] = ffb_flow["mill_spec"].fillna("").astype(str).pipe(vectorize_normalize_spec_value)
    ffb_flow["supplier_spec"] = ffb_flow["supplier_spec"].fillna("").astype(str).pipe(vectorize_normalize_spec_value)

    ffb_flow = ffb_flow.loc[:, ~ffb_flow.columns.duplicated()]

    return ffb_flow
