"""Chapter 13 schema — feature_store table.

Revision ID: 0003_ch13_schema
Revises: 0002_ch11_schema
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

from src.db.base import Base
import src.db.models  # noqa: F401

revision = "0003_ch13_schema"
down_revision = "0002_ch11_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feature_store")
