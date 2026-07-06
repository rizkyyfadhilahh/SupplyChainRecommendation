from fastapi.testclient import TestClient
from app.main import app
from app.utils import require_api_key

app.dependency_overrides[require_api_key] = lambda: None
client = TestClient(app)

def test_drilldown_buyers():
    response = client.get("/api/buyers")
    assert response.status_code == 200
    assert "buyers" in response.json()

def test_drilldown_capacity_heatmap():
    response = client.get("/api/capacity-heatmap")
    assert response.status_code == 200

def test_drilldown_product_context():
    # buyer Neste Oil exists
    response = client.post(
        "/api/product-context",
        json={"buyer_id": "Neste Oil", "product_code": "CPO"}
    )
    assert response.status_code in [200, 404]

def test_drilldown_resolve_gap():
    response = client.post(
        "/api/resolve-gap",
        json={"buyer_id": "Neste Oil", "product_code": "CPO"}
    )
    assert response.status_code in [200, 404]
