from fastapi.testclient import TestClient
from app.main import app
from app.utils import require_api_key

app.dependency_overrides[require_api_key] = lambda: None
client = TestClient(app)

def test_gap_options():
    response = client.get("/api/options")
    assert response.status_code == 200
    assert "refineries" in response.json()

def test_analyze_gap():
    response = client.post(
        "/api/gap-analysis",
        json={"buyer_name": "Neste Oil", "facility": "Lubuk Gaung Refinery"}
    )
    assert response.status_code == 200

def test_gap_fulfillment():
    response = client.post(
        "/api/gap-fulfillment",
        json={"buyer_name": "Neste Oil", "facility": "Lubuk Gaung Refinery"}
    )
    assert response.status_code == 200
