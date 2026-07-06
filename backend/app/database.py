import logging
import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.config import TEMP_DIR
from app.csv_only_mode import is_sqlite_enabled

logger = logging.getLogger(__name__)

# Using SQLite for local / low-memory footprints
# In production with PostgreSQL, just change this URL to:
# "postgresql://user:password@server/dbname"
DATABASE_URL = f"sqlite:///{os.path.join(TEMP_DIR, 'supply_chain.db')}"

_IS_SQLITE = "sqlite" in DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _IS_SQLITE else {},
    # Connection pooling for concurrent requests
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Optimize SQLite for read-heavy supply chain workloads."""
    if not _IS_SQLITE:
        return
    cursor = dbapi_connection.cursor()
    # Durability tradeoff: speed > safety (acceptable for derived data)
    cursor.execute("PRAGMA synchronous = OFF")
    # WAL mode: concurrent readers don't block writer
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA temp_store = MEMORY")
    # 128 MB page cache
    cursor.execute("PRAGMA cache_size = -131072")
    # 256 MB memory-mapped I/O — biggest single win for read-heavy loads
    cursor.execute("PRAGMA mmap_size = 268435456")
    # Larger pages reduce I/O for wide rows (supply chain data)
    cursor.execute("PRAGMA page_size = 8192")
    # Wait up to 30s for a lock instead of failing immediately
    cursor.execute("PRAGMA busy_timeout = 30000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_performance_indexes() -> None:
    """Create indexes on hot query paths. Safe to call multiple times (IF NOT EXISTS)."""
    if not _IS_SQLITE or not is_sqlite_enabled():
        return
    indexes = [
        # facility_lookup — used in every stock allocation
        "CREATE INDEX IF NOT EXISTS idx_fl_refinery_product ON facility_lookup(refinery_group, product_code)",
        "CREATE INDEX IF NOT EXISTS idx_fl_plant ON facility_lookup(plant)",
        # product_flow — traced per supplier
        "CREATE INDEX IF NOT EXISTS idx_pf_supplier_product ON product_flow(supplier_id, product)",
        "CREATE INDEX IF NOT EXISTS idx_pf_receiver ON product_flow(receiver_id)",
        # ffb_flow — queried by mill and estate
        "CREATE INDEX IF NOT EXISTS idx_ffb_mill ON ffb_flow(mill)",
        "CREATE INDEX IF NOT EXISTS idx_ffb_estate ON ffb_flow(estate)",
        # product_relations — heavy join table
        "CREATE INDEX IF NOT EXISTS idx_pr_receiver ON product_relations(plant_receiver, product_name_receiver)",
        "CREATE INDEX IF NOT EXISTS idx_pr_supplier ON product_relations(plant_supplier)",
        # events_bc — large table, filter by plant/product
        "CREATE INDEX IF NOT EXISTS idx_events_plant ON events_bc(plant)",
        "CREATE INDEX IF NOT EXISTS idx_events_product ON events_bc(product_name)",
    ]
    try:
        with engine.connect() as conn:
            for ddl in indexes:
                conn.execute(text(ddl))
            conn.commit()
        logger.info("Performance indexes ensured.")
    except Exception as exc:
        # Non-fatal: table may not exist yet on first boot
        logger.warning("Could not create indexes (will retry after data load): %s", exc)
