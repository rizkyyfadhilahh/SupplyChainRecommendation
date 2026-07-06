"""
Tests for /api/system/reload endpoint.
Verifies that hot-reload triggers all three cache-clearing steps:
  1. clear_db_cache()
  2. reset_forecast_cache()
  3. load_application_data()
"""
import pytest
from unittest.mock import patch, call
from fastapi.testclient import TestClient

from app.main import app
from app.limiter import limiter
from app.utils import require_api_key

# Bypass API key auth for all tests in this module
app.dependency_overrides[require_api_key] = lambda: None


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear slowapi's in-memory hit counters before every test.
    Without this, tests that share the same endpoint accumulate hits
    and later tests get 429 Too Many Requests."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


class TestReloadEndpoint:
    def test_reload_returns_200(self, client):
        """POST /api/system/reload should return HTTP 200."""
        with (
            patch("app.routers.system_router.clear_db_cache"),
            patch("app.routers.system_router.reset_forecast_cache"),
            patch("app.routers.system_router.load_application_data"),
        ):
            response = client.post("/api/system/reload")

        assert response.status_code == 200

    def test_reload_returns_message(self, client):
        """Response body should contain a 'message' key."""
        with (
            patch("app.routers.system_router.clear_db_cache"),
            patch("app.routers.system_router.reset_forecast_cache"),
            patch("app.routers.system_router.load_application_data"),
        ):
            response = client.post("/api/system/reload")

        data = response.json()
        assert "message" in data
        assert len(data["message"]) > 0

    def test_reload_calls_clear_db_cache(self, client):
        """reload_task must call clear_db_cache() to invalidate stale DataFrames."""
        with (
            patch("app.routers.system_router.clear_db_cache") as mock_clear,
            patch("app.routers.system_router.reset_forecast_cache"),
            patch("app.routers.system_router.load_application_data"),
        ):
            # Use background_tasks — TestClient runs them synchronously
            client.post("/api/system/reload")

        mock_clear.assert_called_once()

    def test_reload_calls_reset_forecast_cache(self, client):
        """reload_task must call reset_forecast_cache() so lead-time data
        is rebuilt from fresh tables, not served from the stale in-memory master."""
        with (
            patch("app.routers.system_router.clear_db_cache"),
            patch("app.routers.system_router.reset_forecast_cache") as mock_forecast,
            patch("app.routers.system_router.load_application_data"),
        ):
            client.post("/api/system/reload")

        mock_forecast.assert_called_once()

    def test_reload_calls_load_application_data(self, client):
        """reload_task must call load_application_data() to rebuild all tables."""
        with (
            patch("app.routers.system_router.clear_db_cache"),
            patch("app.routers.system_router.reset_forecast_cache"),
            patch("app.routers.system_router.load_application_data") as mock_load,
        ):
            client.post("/api/system/reload")

        mock_load.assert_called_once()

    def test_reload_order_of_operations(self, client):
        """clear_db_cache → reset_forecast_cache → load_application_data.
        Order matters: cache must be cleared before data is reloaded,
        and forecast cache must be reset before the new master is built."""
        call_order = []

        with (
            patch(
                "app.routers.system_router.clear_db_cache",
                side_effect=lambda: call_order.append("clear_db_cache"),
            ),
            patch(
                "app.routers.system_router.reset_forecast_cache",
                side_effect=lambda: call_order.append("reset_forecast_cache"),
            ),
            patch(
                "app.routers.system_router.load_application_data",
                side_effect=lambda: call_order.append("load_application_data"),
            ),
        ):
            client.post("/api/system/reload")

        assert call_order == [
            "clear_db_cache",
            "reset_forecast_cache",
            "load_application_data",
        ], f"Wrong call order: {call_order}"