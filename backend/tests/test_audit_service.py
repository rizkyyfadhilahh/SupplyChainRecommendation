"""
Tests for audit logging service.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestAuditServiceCsvMode:
    """Tests for CSV-only mode (no SQLite) — audit ops are no-ops."""

    def test_log_config_change_skipped_in_csv_mode(self):
        with patch("app.services.audit_service.is_sqlite_enabled", return_value=False):
            from app.services.audit_service import log_config_change
            # Should not raise
            log_config_change(
                action="UPDATE",
                entity_type="conversion_map",
                old_value={"CPO": 0.20},
                new_value={"CPO": 0.25},
            )

    def test_get_audit_history_returns_empty_in_csv_mode(self):
        with patch("app.services.audit_service.is_sqlite_enabled", return_value=False):
            from app.services.audit_service import get_audit_history
            result = get_audit_history()
            assert result == []

    def test_get_audit_entry_returns_none_in_csv_mode(self):
        with patch("app.services.audit_service.is_sqlite_enabled", return_value=False):
            from app.services.audit_service import get_audit_entry
            result = get_audit_entry(1)
            assert result is None


class TestAuditServiceSqliteMode:
    """Tests for SQLite mode using mocked SessionLocal."""

    def _make_mock_row(self, **kwargs):
        row = MagicMock()
        row.id = kwargs.get("id", 1)
        row.timestamp = kwargs.get("timestamp", datetime(2024, 6, 15, tzinfo=timezone.utc))
        row.action = kwargs.get("action", "UPDATE")
        row.entity_type = kwargs.get("entity_type", "conversion_map")
        row.entity_id = kwargs.get("entity_id", None)
        row.old_value = kwargs.get("old_value", json.dumps({"CPO": 0.20}))
        row.new_value = kwargs.get("new_value", json.dumps({"CPO": 0.25}))
        row.user_id = kwargs.get("user_id", "system")
        row.request_id = kwargs.get("request_id", "req-123")
        row.ip_address = kwargs.get("ip_address", "127.0.0.1")
        return row

    def test_get_audit_history_returns_list(self):
        mock_row = self._make_mock_row()
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_row]
        mock_db.query.return_value = mock_query

        with patch("app.services.audit_service.is_sqlite_enabled", return_value=True), \
             patch("app.services.audit_service.SessionLocal", return_value=mock_db):
            from app.services.audit_service import get_audit_history
            result = get_audit_history()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["action"] == "UPDATE"
        assert result[0]["entity_type"] == "conversion_map"
        assert result[0]["old_value"] == {"CPO": 0.20}
        assert result[0]["new_value"] == {"CPO": 0.25}

    def test_get_audit_history_filters_by_entity_type(self):
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        with patch("app.services.audit_service.is_sqlite_enabled", return_value=True), \
             patch("app.services.audit_service.SessionLocal", return_value=mock_db):
            from app.services.audit_service import get_audit_history
            result = get_audit_history(entity_type="process_map")

        assert result == []
        # filter was called (entity_type filter applied)
        mock_query.filter.assert_called()

    def test_get_audit_entry_returns_dict_when_found(self):
        mock_row = self._make_mock_row(id=42)
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_row
        mock_db.query.return_value = mock_query

        with patch("app.services.audit_service.is_sqlite_enabled", return_value=True), \
             patch("app.services.audit_service.SessionLocal", return_value=mock_db):
            from app.services.audit_service import get_audit_entry
            result = get_audit_entry(42)

        assert result is not None
        assert result["id"] == 42
        assert result["action"] == "UPDATE"

    def test_get_audit_entry_returns_none_when_not_found(self):
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        with patch("app.services.audit_service.is_sqlite_enabled", return_value=True), \
             patch("app.services.audit_service.SessionLocal", return_value=mock_db):
            from app.services.audit_service import get_audit_entry
            result = get_audit_entry(999)

        assert result is None

    def test_log_config_change_handles_db_error_gracefully(self):
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("DB write error")

        with patch("app.services.audit_service.is_sqlite_enabled", return_value=True), \
             patch("app.services.audit_service.SessionLocal", return_value=mock_db):
            from app.services.audit_service import log_config_change
            # Should NOT raise — audit failures are non-fatal
            log_config_change(
                action="UPDATE",
                entity_type="conversion_map",
                new_value={"CPO": 0.25},
            )
