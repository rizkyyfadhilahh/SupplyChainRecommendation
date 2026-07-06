"""
Audit logging service for domain config changes.
Writes a record to the audit_logs SQLite table on every CREATE / UPDATE / DELETE / RELOAD.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.csv_only_mode import is_sqlite_enabled

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    timestamp   = Column(DateTime(timezone=True), nullable=False)
    action      = Column(String(50),  nullable=False)   # CREATE | UPDATE | DELETE | RELOAD | ROLLBACK
    entity_type = Column(String(100), nullable=False)   # conversion_map | process_map | etc.
    entity_id   = Column(String(255), nullable=True)    # optional key
    old_value   = Column(Text, nullable=True)           # JSON string
    new_value   = Column(Text, nullable=True)           # JSON string
    request_id  = Column(String(100), nullable=True)
    user_id     = Column(String(255), nullable=True)    # future: from JWT
    ip_address  = Column(String(50),  nullable=True)


def ensure_audit_table() -> None:
    """Create audit_logs table if it does not exist yet. Safe to call multiple times."""
    if not is_sqlite_enabled():
        return
    try:
        Base.metadata.create_all(engine, tables=[AuditLog.__table__], checkfirst=True)
        logger.debug("audit_logs table ready")
    except Exception as exc:
        logger.warning("Could not create audit_logs table: %s", exc)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def log_config_change(
    action: str,
    entity_type: str,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    entity_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Persist one audit record.  Non-fatal: logs a warning on failure so the
    main request is never broken by an audit write error.
    Skipped in CSV-only mode (no SQLite available).
    """
    if not is_sqlite_enabled():
        logger.debug("Audit log skipped (CSV-only mode): %s %s", action, entity_type)
        return

    db: Session = SessionLocal()
    try:
        entry = AuditLog(
            timestamp   = datetime.now(tz=timezone.utc),
            action      = str(action).upper()[:50],
            entity_type = str(entity_type)[:100],
            entity_id   = str(entity_id)[:255] if entity_id else None,
            old_value   = json.dumps(old_value, default=str) if old_value is not None else None,
            new_value   = json.dumps(new_value, default=str) if new_value is not None else None,
            request_id  = str(request_id)[:100] if request_id else None,
            user_id     = str(user_id)[:255] if user_id else "system",
            ip_address  = str(ip_address)[:50] if ip_address else None,
        )
        db.add(entry)
        db.commit()
        logger.info(
            "Audit: action=%s entity_type=%s entity_id=%s request_id=%s",
            action, entity_type, entity_id, request_id,
        )
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc, exc_info=True)
        db.rollback()
    finally:
        db.close()


def get_audit_history(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
) -> list:
    """
    Return audit log entries as plain dicts, newest first.
    Returns [] in CSV-only mode.
    """
    if not is_sqlite_enabled():
        return []

    db: Session = SessionLocal()
    try:
        query = db.query(AuditLog)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if action:
            query = query.filter(AuditLog.action == action.upper())

        rows = query.order_by(AuditLog.id.desc()).limit(min(limit, 500)).all()

        return [
            {
                "id":          row.id,
                "timestamp":   row.timestamp.isoformat() if row.timestamp else None,
                "action":      row.action,
                "entity_type": row.entity_type,
                "entity_id":   row.entity_id,
                "old_value":   json.loads(row.old_value) if row.old_value else None,
                "new_value":   json.loads(row.new_value) if row.new_value else None,
                "user_id":     row.user_id,
                "request_id":  row.request_id,
                "ip_address":  row.ip_address,
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("Failed to query audit log: %s", exc)
        return []
    finally:
        db.close()


def get_audit_entry(audit_id: int) -> Optional[dict]:
    """Return a single audit entry by id, or None if not found."""
    if not is_sqlite_enabled():
        return None

    db: Session = SessionLocal()
    try:
        row = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
        if not row:
            return None
        return {
            "id":          row.id,
            "timestamp":   row.timestamp.isoformat() if row.timestamp else None,
            "action":      row.action,
            "entity_type": row.entity_type,
            "entity_id":   row.entity_id,
            "old_value":   json.loads(row.old_value) if row.old_value else None,
            "new_value":   json.loads(row.new_value) if row.new_value else None,
            "user_id":     row.user_id,
            "request_id":  row.request_id,
        }
    except Exception as exc:
        logger.warning("Failed to fetch audit entry %d: %s", audit_id, exc)
        return None
    finally:
        db.close()