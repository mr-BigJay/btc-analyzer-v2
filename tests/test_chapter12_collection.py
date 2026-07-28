"""Chapter 12 — Data Collection & Exchange Integration Layer tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.collectors.contract import SCHEMA_VERSION, latency_ms, stamp_contract, stamp_timestamps
from src.collectors.events import EventBus, event_bus
from src.collectors.health import CollectorHealthStatus, HealthMonitor
from src.collectors.interface import ExchangeCollector
from src.collectors.metrics import PERFORMANCE_TARGETS, MetricsRegistry
from src.collectors.quarantine import QuarantineStore
from src.collectors.symbols import SymbolRegistry, symbol_registry
from src.collectors.typed import MacroCollector, VolatilityCollector
from src.pipeline.validation import DataValidator


def test_exchange_collector_interface_methods():
    assert hasattr(ExchangeCollector, "connect")
    assert hasattr(ExchangeCollector, "collect")
    assert hasattr(ExchangeCollector, "validate")
    assert hasattr(ExchangeCollector, "normalize")
    assert hasattr(ExchangeCollector, "publish")


def test_internal_data_contract_schema():
    raw = {
        "symbol": "BTCUSDT",
        "price": 65000.0,
        "timestamp": "2026-07-28T08:15:42.120Z",
    }
    contract = stamp_contract(raw, source="Binance", market="Futures")
    assert contract["schema_version"] == SCHEMA_VERSION
    assert contract["source"] == "Binance"
    assert contract["asset"] == "BTCUSDT"
    assert contract["market"] == "Futures"
    assert "payload" in contract
    assert contract["exchange_timestamp"]
    assert contract["collection_timestamp"]
    assert contract["processing_timestamp"]
    assert isinstance(contract["sequence"], int)


def test_timestamp_triad():
    stamped = stamp_timestamps(
        {"price": 1},
        exchange_timestamp="2026-07-28T08:15:40.000Z",
        collection_timestamp="2026-07-28T08:15:40.120Z",
    )
    assert stamped["exchange_timestamp"].endswith("Z") or "+" in stamped["exchange_timestamp"]
    assert stamped["collection_timestamp"]
    assert stamped["processing_timestamp"]
    lat = latency_ms(
        {
            "exchange_timestamp": "2026-07-28T08:15:40.000Z",
            "collection_timestamp": "2026-07-28T08:15:40.120Z",
        }
    )
    assert lat is not None
    assert 100 <= lat <= 150


def test_event_bus_publish_subscribe():
    bus = EventBus(history_size=50)
    seen: list[str] = []

    def handler(evt):
        seen.append(evt.event)

    bus.subscribe("market.futures.updated", handler)
    evt = bus.publish(
        "market.futures.updated",
        asset="BTCUSDT",
        payload={"price": 1},
        source="binance",
    )
    assert evt.event == "market.futures.updated"
    assert seen == ["market.futures.updated"]
    recent = bus.recent(limit=5)
    assert recent[-1]["asset"] == "BTCUSDT"


def test_symbol_registry_mappings():
    reg = SymbolRegistry()
    assert reg.to_internal("binance", "BTCUSDT") == "BTCUSDT"
    assert reg.to_internal("binance", "BTC/USDT") == "BTCUSDT"
    assert reg.to_internal("deribit", "BTC-PERPETUAL") == "BTCUSD_PERP"
    assert reg.to_internal("deribit", "BTC") == "BTCUSDT"
    assert reg.to_internal("coinex", "BTCUSDT") == "BTCUSDT"
    mappings = symbol_registry.list_mappings()
    assert any(m["provider"] == "binance" for m in mappings)


def test_quarantine_rejects_invalid():
    store = QuarantineStore(maxlen=10)
    v = DataValidator()
    payload = {
        "symbol": "BTCUSDT",
        "mark_price": float("nan"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "_required_fields": ["mark_price"],
    }
    report = v.validate("binance", payload)
    hard = [i for i in report.issues if i.severity == "error"]
    assert hard
    rec = store.add(source="binance", payload=payload, codes=[i.code for i in hard])
    assert store.count() == 1
    assert rec.id
    assert "INVALID_VALUE" in rec.codes


def test_health_state_machine():
    mon = HealthMonitor()
    h = mon.record_error("binance_futures", "timeout")
    assert h.status == CollectorHealthStatus.OFFLINE
    h = mon.record_success("binance_futures", latency_ms=90)
    assert h.status == CollectorHealthStatus.RECOVERING
    h = mon.record_success("binance_futures", latency_ms=80)
    assert h.status == CollectorHealthStatus.HEALTHY
    snap = mon.snapshot()
    assert "overall" in snap
    assert "binance_futures" in snap["collectors"]


def test_metrics_dqs_contribution_and_targets():
    assert PERFORMANCE_TARGETS["spot_latency_ms"] == 250.0
    reg = MetricsRegistry()
    reg.record("binance", success=True, latency_ms=92, validation_ms=3, normalization_ms=2)
    reg.record("binance", success=True, latency_ms=100, validation_ms=4, normalization_ms=1)
    dqs = reg.dqs_contribution()
    assert dqs["availability"] == 1.0
    assert dqs["score_hint"] >= 50
    snap = reg.snapshot()
    assert "targets" in snap


def test_macro_collector_does_not_fabricate():
    out = MacroCollector().collect()
    assert out.collector_type == "Macro"
    macro = out.results["macro"]
    assert macro.data is not None
    data = macro.data if isinstance(macro.data, dict) else {}
    # Must not invent CPI/DXY numbers
    assert data.get("cpi") is None
    assert data.get("dxy") is None
    assert data.get("feed_configured") is False


def test_volatility_collector_degrades_without_cache():
    out = VolatilityCollector().collect()
    assert out.collector_type == "Volatility"
    assert "volatility" in out.results


def test_collection_status_api_includes_ch12_fields():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    r = client.get("/api/v1/collection/status")
    assert r.status_code == 200
    body = r.json()
    data = body.get("data") or body
    assert "health" in data
    assert "metrics" in data
    assert "quarantine_count" in data
    assert "collector_types" in data
    assert set(data["collector_types"]) >= {"spot", "futures", "options", "volatility", "macro"}
