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
    set_app_data("relations_all", pd.DataFrame(columns=["supplier", "facility", "product", "supplier_type", "lead_time_days"]))
    set_app_data("facility_lookup", {})
    set_app_data("facility_type_lookup", {})

client = TestClient(app)

def test_trace():
    payload = {
        "orders": [
            {
                "facility": "Lubuk Gaung Refinery",
                "product": "CPO",
                "quantity": 100.0,
                "recommendation_metric": "VOLUME"
            }
        ]
    }
    response = client.post("/api/trace", json=payload)
    assert response.status_code == 200
    assert "results" in response.json()
