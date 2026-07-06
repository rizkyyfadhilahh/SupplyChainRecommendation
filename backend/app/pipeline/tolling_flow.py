import pandas as pd
import numpy as np
from app.pipeline.utils import vectorize_normalize_trace_product, vectorize_normalize_facility_type, vectorize_normalize_spec_value

def process_tolling_flow(relations_all: pd.DataFrame, facility_lookup: pd.DataFrame) -> pd.DataFrame:
    tolling_relations_raw = relations_all[
        (relations_all["movement_type_supplier"] == 961) &
        (relations_all["movement_type_receiver"] == 601)
    ].copy()

    if not tolling_relations_raw.empty:
        tolling_relations_raw["supplier_product"] = (
            tolling_relations_raw["product_name_supplier"]
            .pipe(vectorize_normalize_trace_product)
        )

        tolling_relations_raw["receiver_product"] = (
            tolling_relations_raw["product_name_receiver"]
            .pipe(vectorize_normalize_trace_product)
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
            .pipe(vectorize_normalize_facility_type)
        )

        tolling_flow["facility_type"] = (
            tolling_flow["facility_type"]
            .fillna("")
            .astype(str)
            .pipe(vectorize_normalize_facility_type)
        )

        tolling_flow["supplier_spec"] = (
            tolling_flow["supplier_spec"]
            .fillna("")
            .astype(str)
            .pipe(vectorize_normalize_spec_value)
        )

        tolling_flow["facility_spec"] = (
            tolling_flow["facility_spec"]
            .fillna("")
            .astype(str)
            .pipe(vectorize_normalize_spec_value)
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

    return tolling_flow
