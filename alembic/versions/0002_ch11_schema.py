"""Chapter 11 schema extensions — intelligence store + column adds.

Revision ID: 0002_ch11_schema
Revises: 0001_ch04_schema
Create Date: 2026-07-27

Notes:
- PostgreSQL production may further partition futures_data / spot_data by month.
- SQLite (local/tests) uses create_all + ALTER ADD COLUMN; no native partitioning.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect, text

from src.db.base import Base
import src.db.models  # noqa: F401

revision = "0002_ch11_schema"
down_revision = "0001_ch04_schema"
branch_labels = None
depends_on = None


_COLUMN_ADDS: dict[str, list[tuple[str, str]]] = {
    "exchanges": [
        ("api_status", "VARCHAR(32) DEFAULT 'unknown' NOT NULL"),
        ("last_sync", "TIMESTAMP"),
    ],
    "symbols": [
        ("public_id", "VARCHAR(36)"),
    ],
    "technical_indicators": [
        ("signal", "VARCHAR(32)"),
        ("ema_values", "TEXT"),
        ("engine_version", "VARCHAR(32)"),
        ("calculation_version", "VARCHAR(32)"),
    ],
    "market_structure": [
        ("higher_high", "BOOLEAN"),
        ("higher_low", "BOOLEAN"),
        ("lower_high", "BOOLEAN"),
        ("lower_low", "BOOLEAN"),
        ("bos", "BOOLEAN"),
        ("choch", "BOOLEAN"),
    ],
}


def _existing_columns(bind, table: str) -> set[str]:
    insp = inspect(bind)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    # Create any missing Ch.11 tables
    Base.metadata.create_all(bind=bind)

    for table, cols in _COLUMN_ADDS.items():
        existing = _existing_columns(bind, table)
        for name, ddl in cols:
            if name in existing:
                continue
            bind.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))

    # Backfill public_id for existing symbols if null/empty (SQLite-friendly)
    try:
        bind.execute(
            text(
                "UPDATE symbols SET public_id = lower(hex(randomblob(4)) || '-' || "
                "hex(randomblob(2)) || '-' || hex(randomblob(2)) || '-' || "
                "hex(randomblob(2)) || '-' || hex(randomblob(6))) "
                "WHERE public_id IS NULL OR public_id = ''"
            )
        )
    except Exception:
        # PostgreSQL / other dialects: use gen_random_uuid if available
        try:
            bind.execute(
                text(
                    "UPDATE symbols SET public_id = gen_random_uuid()::text "
                    "WHERE public_id IS NULL OR public_id = ''"
                )
            )
        except Exception:
            pass


def downgrade() -> None:
    # Drop Ch.11-only tables; leave additive columns (safe rollback for shared DBs).
    bind = op.get_bind()
    for table in (
        "alerts",
        "reports",
        "ai_decisions",
        "market_scores",
        "liquidity_zones",
        "volatility_data",
        "options_data",
        "futures_data",
        "spot_data",
    ):
        bind.execute(text(f"DROP TABLE IF EXISTS {table}"))
