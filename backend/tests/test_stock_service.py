"""
Tests for stock allocation service.
"""
import pytest
from datetime import datetime
import pandas as pd

from app.services.stock_service import (
    allocate_stock,
    classify_slocs,
    get_stock_candidate_products,
    normalize_stock_product,
    is_sloc_eudr_active,
)


# ---------------------------------------------------------------------------
# normalize_stock_product
# ---------------------------------------------------------------------------

class TestNormalizeStockProduct:
    def test_cpo_from_material_type(self):
        assert normalize_stock_product("CPO", "") == "CPO"

    def test_rbdpo_from_material_type(self):
        assert normalize_stock_product("RBDPO", "") == "RBDPO"

    def test_rbdpko_from_material_type(self):
        assert normalize_stock_product("RBDPKO", "") == "RBDPKO"

    def test_pko_from_material_type(self):
        assert normalize_stock_product("PKO", "") == "PKO"

    def test_pk_from_material_type(self):
        assert normalize_stock_product("PK", "") == "PK"

    def test_pfad_from_material_type(self):
        assert normalize_stock_product("PFAD", "") == "PFAD"

    def test_olein_from_desc(self):
        assert normalize_stock_product("", "RBDOLN OLEIN") == "RBDOLN"

    def test_cpo_from_desc(self):
        assert normalize_stock_product("", "CRUDE PALM OIL") == "CPO"

    def test_none_for_unknown(self):
        result = normalize_stock_product("UNKNOWN_MAT", "UNKNOWN_DESC")
        assert result is None


# ---------------------------------------------------------------------------
# get_stock_candidate_products
# ---------------------------------------------------------------------------

class TestGetStockCandidateProducts:
    def test_cpo_maps_to_cpo(self):
        candidates = get_stock_candidate_products("CPO")
        assert "CPO" in candidates

    def test_rbdpo_returns_itself_only(self):
        # RBDPO is in REFINED_PRODUCTS — the function intentionally returns
        # only ["RBDPO"] without walking the process_map chain, because
        # refined products are never substituted with their raw input at
        # the stock allocation layer.
        candidates = get_stock_candidate_products("RBDPO")
        assert "RBDPO" in candidates
        assert len(candidates) == 1

    def test_unknown_product_returns_itself(self):
        candidates = get_stock_candidate_products("UNKNOWN_PRODUCT")
        assert "UNKNOWN_PRODUCT" in candidates


# ---------------------------------------------------------------------------
# is_sloc_eudr_active
# ---------------------------------------------------------------------------

class TestIsSlocEudrActive:
    def test_active_eudr(self):
        row = pd.Series({
            "eudr": True,
            "eudr_valid_from": datetime(2024, 1, 1),
            "eudr_valid_to": datetime(2025, 12, 31),
        })
        current = pd.Timestamp("2024-06-15")
        assert is_sloc_eudr_active(row, current) is True

    def test_expired_eudr(self):
        row = pd.Series({
            "eudr": True,
            "eudr_valid_from": datetime(2020, 1, 1),
            "eudr_valid_to": datetime(2021, 12, 31),
        })
        current = pd.Timestamp("2024-06-15")
        assert is_sloc_eudr_active(row, current) is False

    def test_eudr_false(self):
        row = pd.Series({
            "eudr": False,
            "eudr_valid_from": datetime(2024, 1, 1),
            "eudr_valid_to": datetime(2025, 12, 31),
        })
        current = pd.Timestamp("2024-06-15")
        assert is_sloc_eudr_active(row, current) is False

    def test_no_date_range(self):
        row = pd.Series({
            "eudr": True,
            "eudr_valid_from": None,
            "eudr_valid_to": None,
        })
        current = pd.Timestamp("2024-06-15")
        assert is_sloc_eudr_active(row, current) is False


# ---------------------------------------------------------------------------
# allocate_stock
# ---------------------------------------------------------------------------

class TestAllocateStock:
    def _make_sloc_state(self):
        return pd.DataFrame({
            "plant": ["1000", "1000", "2000"],
            "name1": ["Plant A", "Plant A", "Plant B"],
            "storagelocation": ["001", "002", "003"],
            "material": ["MAT001", "MAT002", "MAT003"],
            "material_type": ["CPO", "CPO", "CPO"],
            "materialdescription": ["Crude Palm Oil A", "Crude Palm Oil B", "Crude Palm Oil C"],
            "current_stock": [5000.0, 3000.0, 10000.0],
            "refinery_group": ["REF1", "REF1", "REF2"],
            "product_code": ["CPO", "CPO", "CPO"],
            "eudr": [True, False, True],
            "eudr_valid_from": [
                pd.Timestamp("2024-01-01"),
                pd.NaT,
                pd.Timestamp("2024-01-01"),
            ],
            "eudr_valid_to": [
                pd.Timestamp("2025-12-31"),
                pd.NaT,
                pd.Timestamp("2025-12-31"),
            ],
        })

    def test_fully_fulfilled(self):
        sloc_state = self._make_sloc_state()
        overview, updated = allocate_stock(
            sloc_state=sloc_state,
            refinery_group="REF1",
            requested_product="CPO",
            spec="ALL",
            demand_qty=1000.0,
            current_date=pd.Timestamp("2024-06-15"),
        )
        assert overview["summary"]["stock_status"] == "FULLY_FULFILLED"
        assert overview["summary"]["fulfilled_from_stock"] == 1000.0
        assert overview["summary"]["unmet_demand"] == 0.0

    def test_partially_fulfilled(self):
        sloc_state = self._make_sloc_state()
        overview, updated = allocate_stock(
            sloc_state=sloc_state,
            refinery_group="REF1",
            requested_product="CPO",
            spec="ALL",
            demand_qty=9000.0,  # total REF1 stock = 8000
            current_date=pd.Timestamp("2024-06-15"),
        )
        assert overview["summary"]["stock_status"] == "PARTIALLY_FULFILLED"
        assert overview["summary"]["fulfilled_from_stock"] == 8000.0
        assert overview["summary"]["unmet_demand"] == 1000.0

    def test_not_fulfilled_wrong_facility(self):
        sloc_state = self._make_sloc_state()
        overview, updated = allocate_stock(
            sloc_state=sloc_state,
            refinery_group="REF_NONEXISTENT",
            requested_product="CPO",
            spec="ALL",
            demand_qty=1000.0,
            current_date=pd.Timestamp("2024-06-15"),
        )
        assert overview["summary"]["stock_status"] == "NOT_FULFILLED"
        assert overview["summary"]["fulfilled_from_stock"] == 0.0

    def test_eudr_filter_only_picks_eudr_slocs(self):
        sloc_state = self._make_sloc_state()
        overview, updated = allocate_stock(
            sloc_state=sloc_state,
            refinery_group="REF1",
            requested_product="CPO",
            spec="EUDR",
            demand_qty=1000.0,
            current_date=pd.Timestamp("2024-06-15"),
        )
        # Only EUDR-active SLOCs should be selected
        for sloc in overview["selected_slocs"]:
            assert sloc["eudr_label"] is True

    def test_stock_state_mutated_correctly(self):
        sloc_state = self._make_sloc_state()
        overview, updated = allocate_stock(
            sloc_state=sloc_state,
            refinery_group="REF1",
            requested_product="CPO",
            spec="ALL",
            demand_qty=2000.0,
            current_date=pd.Timestamp("2024-06-15"),
        )
        # Total allocated must match demand
        total_allocated = sum(s["allocated_qty"] for s in overview["selected_slocs"])
        assert total_allocated == 2000.0

    def test_zero_quantity_order(self):
        sloc_state = self._make_sloc_state()
        overview, updated = allocate_stock(
            sloc_state=sloc_state,
            refinery_group="REF1",
            requested_product="CPO",
            spec="ALL",
            demand_qty=0.001,  # below any stock threshold
            current_date=pd.Timestamp("2024-06-15"),
        )
        # Should still run without error
        assert "summary" in overview
