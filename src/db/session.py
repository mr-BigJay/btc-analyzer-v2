"""Database session / engine factory (Ch.4 §4.2, §4.11).

PostgreSQL is the primary production database.
SQLite remains supported for local development and unit tests.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.db.base import Base

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _engine_kwargs() -> dict[str, Any]:
    url = settings.database_url
    kwargs: dict[str, Any] = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Connection pooling for PostgreSQL (Ch.4 §4.11)
        kwargs.update(
            {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_pre_ping": True,
            }
        )
    return kwargs


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.database_url, **_engine_kwargs())
        if settings.database_url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _fk_on(dbapi_conn, _):  # noqa: ANN001
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
        logger.info("DB engine ready dialect=%s", _engine.dialect.name)
    return _engine


def get_session() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def init_db(*, seed: bool = True) -> None:
    """Create schema (and seed reference data). Prefer Alembic in production."""
    # Import models so metadata is populated
    import src.db.models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(engine)
    if seed:
        from src.db.seed import seed_reference_data

        seed_reference_data()


def reset_engine() -> None:
    """Test helper — dispose engine so a new URL can be bound."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
