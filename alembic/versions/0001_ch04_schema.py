"""Initial Chapter 4 schema — six domains with FK integrity.

Revision ID: 0001_ch04_schema
Revises:
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

from src.db.base import Base
import src.db.models  # noqa: F401

revision = "0001_ch04_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
