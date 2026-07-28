"""Loguru-based logging (Ch.5 §5.2 / §5.10)."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

from loguru import logger

from src.config import settings

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _patcher(record: dict) -> None:
    record["extra"].setdefault("module_name", record.get("name", "app"))
    record["extra"].setdefault("correlation_id", correlation_id_var.get() or "-")
    # Ch.19 §19.15 — never log secrets / tokens
    try:
        from src.security.secrets import mask_secrets

        msg = record.get("message")
        if isinstance(msg, str):
            record["message"] = mask_secrets(msg)
    except Exception:  # noqa: BLE001
        pass


def setup_logging() -> None:
    """Configure Loguru + intercept stdlib loggers."""
    logger.remove()
    logger.configure(patcher=_patcher)
    level = settings.log_level.upper()
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "cid={extra[correlation_id]} | "
            "<cyan>{extra[module_name]}</cyan> | "
            "{message}"
        ),
        enqueue=False,
    )
    logs_dir = settings.data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        logs_dir / "btc_analyzer.log",
        rotation="10 MB",
        retention="14 days",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | cid={extra[correlation_id]} | {message}",
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "apscheduler", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = [_InterceptHandler()]
        logging.getLogger(name).propagate = False


def get_logger(module: str = "app"):
    return logger.bind(module_name=module)
