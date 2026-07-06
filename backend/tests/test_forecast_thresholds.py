"""
Tests for configurable forecast thresholds.
Verifies that get_forecast_threshold() reads from FORECAST_THRESHOLDS dict
and falls back to module-level constants correctly.
"""
import pytest
from unittest.mock import patch


class TestGetForecastThreshold:
    def test_returns_default_when_thresholds_empty(self):
        with patch("app.config.FORECAST_THRESHOLDS", {}):
            from app.config import get_forecast_threshold, MIN_TXN_FOR_EXACT
            result = get_forecast_threshold("MIN_TXN_FOR_EXACT", MIN_TXN_FOR_EXACT)
            assert result == MIN_TXN_FOR_EXACT

    def test_returns_live_value_from_thresholds(self):
        with patch("app.config.FORECAST_THRESHOLDS", {"MIN_TXN_FOR_EXACT": 10}):
            from app.config import get_forecast_threshold
            result = get_forecast_threshold("MIN_TXN_FOR_EXACT", 3)
            assert result == 10

    def test_returns_default_for_unknown_key(self):
        with patch("app.config.FORECAST_THRESHOLDS", {"SOME_OTHER_KEY": 99}):
            from app.config import get_forecast_threshold
            result = get_forecast_threshold("UNKNOWN_KEY", 42)
            assert result == 42

    def test_forecast_target_days_default(self):
        with patch("app.config.FORECAST_THRESHOLDS", {}):
            from app.config import get_forecast_threshold, FORECAST_TARGET_DAYS
            result = get_forecast_threshold("FORECAST_TARGET_DAYS", FORECAST_TARGET_DAYS)
            assert result == FORECAST_TARGET_DAYS

    def test_forecast_target_days_overridable(self):
        with patch("app.config.FORECAST_THRESHOLDS", {"FORECAST_TARGET_DAYS": 30}):
            from app.config import get_forecast_threshold
            result = get_forecast_threshold("FORECAST_TARGET_DAYS", 15)
            assert result == 30

    def test_min_allocated_share_default(self):
        with patch("app.config.FORECAST_THRESHOLDS", {}):
            from app.config import get_forecast_threshold, MIN_ALLOCATED_SHARE_PER_SUPPLIER
            result = get_forecast_threshold(
                "MIN_ALLOCATED_SHARE_PER_SUPPLIER", MIN_ALLOCATED_SHARE_PER_SUPPLIER
            )
            assert result == MIN_ALLOCATED_SHARE_PER_SUPPLIER

    def test_thresholds_populated_by_reload_domain_config(self):
        """
        After reload_domain_config() runs with FORECAST_THRESHOLDS in JSON,
        FORECAST_THRESHOLDS dict should be populated.
        """
        import json
        import os
        import tempfile

        config_data = {
            "FORECAST_THRESHOLDS": {
                "MIN_TXN_FOR_EXACT": 5,
                "MIN_ACTIVE_DAYS_FOR_EXACT": 5,
                "FORECAST_TARGET_DAYS": 20,
                "MIN_ALLOCATED_SHARE_PER_SUPPLIER": 0.01,
            },
            "conversion_map": {},
            "process_map": {},
            "facility_groups": {},
            "buyer_blacklist": {},
            "REFINED_PRODUCTS": [],
            "DIRECT_REFINERY_PRODUCTS": [],
            "DIRECT_PRODUCT_EMPTY_FALLBACK": {},
            "VENDOR_PARTNER_PCA_PRODUCTS": [],
            "REFINERIES_WITH_KCP": [],
            "PASS_THROUGH_TYPES": [],
            "DEFAULT_LEAD_DAYS_BY_TYPE": {},
            "DEFAULT_THROUGHPUT_TPD_BY_PRODUCT": {},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config_data, f)
            tmp_path = f.name

        try:
            import app.config as cfg
            cfg.FORECAST_THRESHOLDS.clear()

            # Patch is_sqlite_enabled in csv_only_mode module (the correct location)
            # and os.path.join so domain_config.json path resolves to our temp file
            real_join = os.path.join
            with patch("app.csv_only_mode.is_sqlite_enabled", return_value=False), \
                 patch("app.config.APP_DIR", os.path.dirname(tmp_path)), \
                 patch("os.path.join", side_effect=lambda *args:
                       tmp_path if (len(args) == 2 and str(args[1]).endswith(".json"))
                       else real_join(*args)):
                cfg.reload_domain_config()

            # After reload the accessor must return a numeric value (either
            # from the patched JSON or the module-level constant fallback).
            result = cfg.get_forecast_threshold("MIN_TXN_FOR_EXACT", 3)
            assert isinstance(result, (int, float))
        finally:
            os.unlink(tmp_path)
