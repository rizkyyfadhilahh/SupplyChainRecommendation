"""
Pytest fixtures for test suite.
Shared fixtures for mocking data and test client setup.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime

from app.main import app
from app.config import API_KEY


@pytest.fixture
def client():
    """Test client with API key header."""
    client = TestClient(app)
    client.headers = {"X-API-Key": API_KEY or "test-api-key"}
    return client


@pytest.fixture
def client_no_auth():
    """Test client without API key (for testing auth failures)."""
    return TestClient(app)


@pytest.fixture
def mock_sloc_master():
    """Mock SLOC master data for stock allocation tests."""
    return pd.DataFrame({
        "plant": ["1000", "1000", "2000"],
        "name1": ["Plant A", "Plant A", "Plant B"],
        "storagelocation": ["001", "002", "003"],
        "material": ["MAT001", "MAT002", "MAT003"],
        "material_type": ["CPO", "CPO", "RBDPO"],
        "materialdescription": ["Crude Palm Oil", "Crude Palm Oil", "Refined"],
        "current_stock": [5000.0, 3000.0, 10000.0],
        "refinery_group": ["REF1", "REF1", "REF2"],
        "product_code": ["CPO", "CPO", "RBDPO"],
        "eudr": [True, False, True],
        "eudr_valid_from": [datetime(2024, 1, 1), None, datetime(2024, 1, 1)],
        "eudr_valid_to": [datetime(2025, 12, 31), None, datetime(2025, 12, 31)],
        "eudr_active_today": [True, False, True],
        "eligible": [True, True, True],
        "eligibility_reason": ["EUDR active", "No EUDR", "EUDR active"],
    })


@pytest.fixture
def mock_app_data_loaded(monkeypatch):
    """Mock app_data_loaded flag to simulate data already loaded."""
    from app.state import APP_DATA
    APP_DATA["app_data_loaded"] = True
    APP_DATA["plant_to_refinery"] = {"1000": "REF1", "2000": "REF2"}
    APP_DATA["facility_name_lookup"] = {"1000": "Plant A", "2000": "Plant B"}
    APP_DATA["facility_type_lookup"] = {"1000": "MILL", "2000": "REFINERY"}
    yield
    APP_DATA.clear()


@pytest.fixture
def mock_trace_result():
    """Mock trace result for recommendation engine tests."""
    return {
        "order_index": 1,
        "facility": "REF1",
        "product": "CPO",
        "quantity": 10000.0,
        "spec": "ALL",
        "buyer": "BUYER1",
        "stock_overview": {
            "summary": {
                "fulfilled_from_stock": 5000.0,
                "unmet_demand": 5000.0,
                "stock_status": "PARTIALLY_FULFILLED",
            },
            "selected_slocs": [],
        },
        "recommendation_options": [
            {
                "option_type": "Historical Volume-Based Recommendation",
                "total_estimated_days": 15,
                "tree": [
                    {
                        "level": 0,
                        "supplier_id": "SUPP1",
                        "supplier_name": "Supplier One",
                        "supplier_type": "MILL",
                        "product": "CPO",
                        "quantity": 5000.0,
                    }
                ],
                "forecast_summary": {
                    "unmet_demand_qty": 5000.0,
                    "allocated_root_qty": 5000.0,
                    "total_estimated_days": 15,
                },
            }
        ],
    }
