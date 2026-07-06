import pytest
import pandas as pd
from app.data_loader import set_app_data
from fastapi.testclient import TestClient
from app.main import app
from app.utils import require_api_key

app.dependency_overrides[require_api_key] = lambda: None

@pytest.fixture(autouse=True)
def mock_app_data():
    set_app_data("events_bc", pd.DataFrame(columns=["plant", "storagelocation", "material", "quantity", "documentdate"]))
    set_app_data("relations_all", pd.DataFrame())
    set_app_data("facility_lookup", {})
    set_app_data("facility_type_lookup", {})

client = TestClient(app)

def test_get_sloc_master():
    response = client.get("/api/sloc-master")
    assert response.status_code == 200
    assert "sloc_master" in response.json()

def test_sloc_config():
    response = client.post(
        "/api/sloc-config",
        json={"items": [{"plant": "1000", "storagelocation": "A100", "material": "CPO", "eudr": True}]}
    )
    assert response.status_code == 200

def test_stock_refresh():
    response = client.post("/api/stock-refresh")
    assert response.status_code == 200
