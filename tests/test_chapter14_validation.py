"""Chapter 14 — Backtesting & Continuous Validation tests."""

from __future__ import annotations

from src.validation.archive import PredictionArchive, archive_from_ai_report
from src.validation.calibration import calibration_table, confidence_bin
from src.validation.contracts import HORIZONS, ValidationObject
from src.validation.drift import detect_performance_drift
from src.validation.failures import categorize_failure
from src.validation.governance import approve_validation, build_validation_object
from src.validation.metrics import aggregate_outcome_metrics, classification_scores, confusion_from_directions, trading_metrics
from src.validation.outcomes import bias_matches, classify_direction, evaluate_prediction
from src.validation.paper import PaperTradingLedger
from src.validation.replay import replay_series, simple_bias_predictor
from src.validation.shadow import compare_engines
from src.validation.walk_forward import walk_forward_folds
from src.validation.engine import ValidationEngine
from src.validation.contracts import PredictionRecord


def _synth_closes(n: int = 200, start: float = 60000.0) -> list[float]:
    closes = []
    px = start
    for i in range(n):
        px = px * (1.0 + (0.002 if (i // 10) % 2 == 0 else -0.0015))
        closes.append(px)
    return closes


def test_horizons_defined():
    assert HORIZONS == ("1h", "4h", "24h", "7d")


def test_no_lookahead_replay_only_uses_visible_history():
    closes = _synth_closes(120)
    seen_lengths = []

    def predict(visible, idx):
        seen_lengths.append(len(visible))
        assert len(visible) == idx + 1
        return simple_bias_predictor(visible, idx)

    result = replay_series(closes, predict_fn=predict, step=20, min_history=30, archive=False)
    assert result.ok
    assert seen_lengths
    assert max(seen_lengths) < len(closes)  # never saw full future series as "visible" at last predict? 
    # last predict may be near end but visible is closes[:i+1] with i < len-2
    assert all(L < len(closes) for L in seen_lengths)


def test_outcome_evaluation_and_metrics():
    closes = _synth_closes(80)
    pred = PredictionRecord(
        market_bias="Bullish",
        confidence=80,
        primary_scenario="Bullish Continuation",
        risk_level="Moderate",
        entry_price=closes[40],
        market_regime="Trend",
        layer_scores={"Technical": 50, "Spot": 40},
    )
    outcomes = evaluate_prediction(pred, closes=closes, entry_idx=40, bars_per_hour=1.0)
    assert {o.horizon for o in outcomes} == set(HORIZONS)
    rows = []
    for o in outcomes:
        d = o.to_dict()
        d["market_bias"] = pred.market_bias
        d["predicted_bias"] = pred.market_bias
        d["confidence"] = pred.confidence
        d["market_regime"] = pred.market_regime
        d["layer_scores"] = pred.layer_scores
        rows.append(d)
    metrics = aggregate_outcome_metrics(rows, horizon="24h")
    assert "accuracy" in metrics
    assert metrics["sample_size"] >= 1


def test_classification_and_trading_metrics():
    cm = confusion_from_directions(["Bullish", "Bullish", "Bearish"], ["Bullish", "Bearish", "Bearish"])
    scores = classification_scores(cm)
    assert scores["accuracy"] > 0
    tm = trading_metrics([0.01, -0.005, 0.02, -0.01])
    assert tm["win_rate"] == 50.0
    assert tm["expectancy"] is not None


def test_calibration_bins():
    assert confidence_bin(85) == "80–89"
    table = calibration_table([(92, True), (91, True), (85, True), (84, False), (70, True), (65, False)])
    assert table["label"] in {"Excellent", "Good", "Moderate", "Poor"}
    assert "90–100" in table["bins"]


def test_walk_forward_folds_sequential():
    folds = walk_forward_folds(200, train_size=80, valid_size=20, step=20)
    assert folds
    for f in folds:
        assert f.train_end == f.valid_start
        assert f.valid_end <= 200


def test_paper_trade_no_real_orders():
    ledger = PaperTradingLedger()
    pred = PredictionRecord(
        market_bias="Bullish",
        entry_price=65000,
        trading_plan={
            "preferred_direction": "long",
            "entry_zone": [65000, 65100],
            "stop_loss_zone": 64000,
            "target_levels": [66000, 67000],
        },
    )
    trade = ledger.open_from_prediction(pred)
    assert trade is not None
    closes = [65000 + i * 50 for i in range(30)]
    highs = [c + 20 for c in closes]
    lows = [c - 20 for c in closes]
    closed = ledger.simulate_exit(trade, highs=highs, lows=lows, closes=closes, start_idx=0, max_bars=20)
    assert closed.exit_reason in {"target", "stop_loss", "time_exit"}
    assert closed.mfe is not None
    assert closed.mae is not None


def test_drift_and_failure_categorization():
    d = detect_performance_drift(70, 85)
    assert d.drift_detected
    assert d.status in {"watch", "review"}
    fail = categorize_failure(data_quality=0.4, return_pct=0.05, conflicts=["a"])
    assert fail["primary"] in fail["all"]


def test_governance_requires_evidence():
    obj = build_validation_object(
        {"accuracy": 86.0, "precision": 84.0, "recall": 82.0, "f1_score": 83.0, "sample_size": 40},
        engine_version="1.1",
        validation_period="2026-Q2",
        method="historical_backtest",
        calibration_label="Excellent",
    )
    approved = approve_validation(obj, approver="qa", notes="ok")
    assert approved.approved is True
    assert approved.approval_record is not None

    weak = build_validation_object(
        {"accuracy": 50.0, "precision": 40.0, "recall": 40.0, "f1_score": 40.0, "sample_size": 5},
        engine_version="1.0",
        validation_period="2026-Q1",
        method="historical_backtest",
        calibration_label="Poor",
    )
    rejected = approve_validation(weak, approver="qa")
    assert rejected.approved is False


def test_immutable_archive_append():
    arch = PredictionArchive(memory_maxlen=10)
    r1 = arch.append(PredictionRecord(market_bias="Bullish", confidence=80))
    r2 = arch.append(PredictionRecord(market_bias="Bearish", confidence=70))
    assert r1.prediction_id != r2.prediction_id
    listed = arch.list(limit=5)
    assert len(listed) >= 2


def test_validation_engine_backtest_end_to_end():
    eng = ValidationEngine()
    report = eng.backtest(_synth_closes(160), step=15, min_history=40, engine_version="1.0")
    assert "validation_object" in report
    vo = report["validation_object"]
    assert "accuracy" in vo
    assert vo["schema_version"]
    assert "dashboard" in report
    assert "metrics_by_horizon" in report


def test_shadow_compare_and_ai_archive_bridge():
    prod = [{"horizon": "24h", "direction_correct": True, "direction_actual": "Bullish", "predicted_bias": "Bullish", "market_bias": "Bullish", "return_pct": 0.01}] * 25
    cand = [{"horizon": "24h", "direction_correct": True, "direction_actual": "Bullish", "predicted_bias": "Bullish", "market_bias": "Bullish", "return_pct": 0.01}] * 22 + [
        {"horizon": "24h", "direction_correct": False, "direction_actual": "Bearish", "predicted_bias": "Bullish", "market_bias": "Bullish", "return_pct": -0.01}
    ] * 3
    # Make candidate clearly better
    cand = [{"horizon": "24h", "direction_correct": True, "direction_actual": "Bullish", "predicted_bias": "Bullish", "market_bias": "Bullish", "return_pct": 0.01}] * 30
    prod = [
        {"horizon": "24h", "direction_correct": i % 2 == 0, "direction_actual": "Bullish", "predicted_bias": "Bullish", "market_bias": "Bullish", "return_pct": 0.01}
        for i in range(30)
    ]
    cmp = compare_engines(prod, cand, horizon="24h")
    assert "promotion_recommended" in cmp

    rec = archive_from_ai_report(
        {
            "symbol": "BTCUSDT",
            "market_bias": "Bullish",
            "confidence": 77,
            "primary_scenario": "Bullish Continuation",
            "risk_level": "Moderate",
            "scoring": {"layer_scores": {"Technical": 30}, "confidence_score": 77},
            "trading_plan": {"preferred_direction": "no_trade"},
        }
    )
    assert rec.prediction_id
    assert rec.market_bias == "Bullish"


def test_bias_match_helpers():
    assert bias_matches("Strong Bullish", "Bullish")
    assert classify_direction(0.02) == "Bullish"
    assert classify_direction(-0.02) == "Bearish"


def test_validation_api_backtest():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    r = client.get("/api/v1/validation/status")
    assert r.status_code == 200
    body = r.json()["data"]
    assert "methods" in body
    r2 = client.post("/api/v1/validation/backtest", json={"closes": _synth_closes(100), "step": 20})
    assert r2.status_code == 200
    assert "validation_object" in r2.json()["data"]
