"""Admin GUI console API tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_admin_test.db")
ADMIN_DIR = Path("/tmp/btc_analyzer_admin_data")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""
os.environ["APP_ENV"] = "testing"
os.environ["API_RATE_LIMIT_PER_MINUTE"] = "2000"

# Isolate admin store under tmp by pointing data_dir via monkeypatch after import is hard;
# instead clear admin files relative to settings after init.

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402
from src.config import settings  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402


def _reset_admin_store():
    admin = settings.data_dir / "admin"
    admin.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "auth.json", "sessions.json"):
        p = admin / name
        if p.exists():
            p.unlink()


def setup_module():
    reset_engine()
    init_db(seed=True)
    _reset_admin_store()


def test_admin_bootstrap_config_and_ops():
    _reset_admin_store()
    client = TestClient(app)

    st = client.get("/api/v1/admin/status")
    assert st.status_code == 200
    assert st.json()["data"]["setup_complete"] is False
    assert st.json()["data"]["gui"] is True

    # config blocked before setup
    denied = client.get("/api/v1/admin/config")
    assert denied.status_code == 403

    boot = client.post(
        "/api/v1/admin/bootstrap",
        json={
            "password": "AdminPass123",
            "config": {
                "api_jwt_secret": "unit-test-jwt-secret-value",
                "timezone": "UTC",
                "default_symbol": "BTCUSDT",
            },
        },
    )
    assert boot.status_code == 200
    token = boot.json()["data"]["token"]
    assert token

    headers = {"X-Admin-Token": token}
    cfg = client.get("/api/v1/admin/config", headers=headers)
    assert cfg.status_code == 200
    groups = cfg.json()["data"]["groups"]
    assert groups
    assert cfg.json()["data"]["setup_complete"] is True

    upd = client.put(
        "/api/v1/admin/config",
        headers=headers,
        json={"values": {"log_level": "INFO", "telegram_chat_id": "12345"}},
    )
    assert upd.status_code == 200
    assert "telegram_chat_id" in upd.json()["data"]["updated_keys"]

    health_op = client.post("/api/v1/admin/ops/health", headers=headers)
    assert health_op.status_code == 200
    assert health_op.json()["data"]["ok"] is True

    # frontend shell
    root = Path(__file__).resolve().parents[1] / "frontend"
    assert (root / "admin.html").exists()
    html = (root / "admin.html").read_text(encoding="utf-8")
    assert "پنل مدیریت" in html
    assert "btn-bootstrap" in html
