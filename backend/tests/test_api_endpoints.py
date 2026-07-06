"""
Tests for API endpoints (health, options, auth guards).
These tests do NOT require CSV data to be loaded — they test the
endpoint contract, auth, and schema validation layers only.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.config import API_KEY

_API_KEY = API_KEY or "test-api-key"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": _API_KEY}


# ---------------------------------------------------------------------------
# Health endpoints (no auth required)
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_data_returns_status_field(self, client):
        response = client.get("/health/data")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "app_data_loaded" in data
        assert data["status"] in ("ready", "initializing")


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_trace_requires_api_key(self, client):
        response = client.post("/api/trace", json={"orders": []})
        assert response.status_code == 401

    def test_sloc_master_requires_api_key(self, client):
        response = client.get("/api/sloc-master")
        assert response.status_code == 401

    def test_gap_analysis_requires_api_key(self, client):
        response = client.post("/api/gap-analysis", json={"buyer_name": "A", "facility": "B"})
        assert response.status_code == 401

    def test_drilldown_buyers_requires_api_key(self, client):
        response = client.get("/api/drilldown/buyers")
        assert response.status_code == 401

    def test_wrong_api_key_returns_401(self, client):
        response = client.get(
            "/api/sloc-master",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Input validation (Pydantic schema layer)
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_trace_empty_orders_rejected(self, client, auth_headers):
        """orders list must have at least 1 item."""
        response = client.post("/api/trace", json={"orders": []}, headers=auth_headers)
        assert response.status_code == 422

    def test_trace_negative_quantity_rejected(self, client, auth_headers):
        response = client.post(
            "/api/trace",
            json={"orders": [{"facility": "REF1", "product": "CPO", "quantity": -100}]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_trace_zero_quantity_rejected(self, client, auth_headers):
        response = client.post(
            "/api/trace",
            json={"orders": [{"facility": "REF1", "product": "CPO", "quantity": 0}]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_trace_too_many_orders_rejected(self, client, auth_headers):
        """max 50 orders per batch."""
        orders = [{"facility": "REF1", "product": "CPO", "quantity": 1000}] * 51
        response = client.post("/api/trace", json={"orders": orders}, headers=auth_headers)
        assert response.status_code == 422

    def test_trace_invalid_spec_rejected(self, client, auth_headers):
        response = client.post(
            "/api/trace",
            json={"orders": [{"facility": "REF1", "product": "CPO", "quantity": 1000, "spec": "INVALID"}]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_trace_invalid_metric_rejected(self, client, auth_headers):
        response = client.post(
            "/api/trace",
            json={"orders": [{"facility": "REF1", "product": "CPO", "quantity": 1000, "recommendation_metric": "INVALID"}]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_gap_analysis_empty_buyer_rejected(self, client, auth_headers):
        response = client.post(
            "/api/gap-analysis",
            json={"buyer_name": "", "facility": "REF1"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_sloc_config_empty_items_rejected(self, client, auth_headers):
        response = client.post(
            "/api/sloc-config",
            json={"items": []},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Options endpoint
# ---------------------------------------------------------------------------

class TestOptionsEndpoint:
    def test_options_returns_expected_keys(self, client, auth_headers):
        response = client.get("/api/options", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "refineries" in data
        assert "products" in data
        assert "buyers" in data
        assert "recommendation_metrics" in data
        assert isinstance(data["refineries"], list)
        assert isinstance(data["products"], list)

    def test_recommendation_metrics_values(self, client, auth_headers):
        response = client.get("/api/options", headers=auth_headers)
        data = response.json()
        metrics = data.get("recommendation_metrics", [])
        assert "VOLUME" in metrics
        assert "LOWEST_PCF" in metrics


# ---------------------------------------------------------------------------
# Rate limiting (slowapi)
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_health_accessible_without_rate_limit(self, client):
        """Health endpoint should always respond 200."""
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200
