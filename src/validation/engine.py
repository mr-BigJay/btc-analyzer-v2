"""Validation Engine — backtesting & continuous evaluation (Ch.14)."""

from __future__ import annotations

from typing import Any, Sequence

from src.logging_setup import get_logger
from src.validation.archive import archive_from_ai_report, prediction_archive
from src.validation.calibration import calibration_table, probability_calibration
from src.validation.contracts import ValidationMethod, utc_now_iso
from src.validation.dashboard import build_dashboard
from src.validation.drift import detect_performance_drift, merge_drift_reports
from src.validation.failures import categorize_failure
from src.validation.governance import approve_validation, build_validation_object
from src.validation.metrics import aggregate_outcome_metrics
from src.validation.outcomes import evaluate_prediction
from src.validation.paper import paper_ledger
from src.validation.regimes import layer_contribution, regime_accuracy
from src.validation.replay import replay_series, simple_bias_predictor
from src.validation.shadow import compare_engines
from src.validation.walk_forward import summarize_fold_metrics, walk_forward_folds

log = get_logger("validation.engine")


class ValidationEngine:
    """Orchestrates replay, evaluation, calibration, drift, and governance."""

    def backtest(
        self,
        closes: Sequence[float],
        *,
        step: int = 12,
        min_history: int = 30,
        bars_per_hour: float = 1.0,
        engine_version: str = "1.0",
        feature_version: str | None = None,
        timestamps: Sequence[str] | None = None,
        use_simple_predictor: bool = True,
        predict_fn=None,
    ) -> dict[str, Any]:
        fn = predict_fn or (simple_bias_predictor if use_simple_predictor else simple_bias_predictor)
        result = replay_series(
            closes,
            predict_fn=fn,
            step=step,
            min_history=min_history,
            bars_per_hour=bars_per_hour,
            timestamps=timestamps,
            engine_version=engine_version,
            feature_version=feature_version,
            archive=True,
        )
        report = self.evaluate_outcomes(result.outcomes, engine_version=engine_version, method=ValidationMethod.HISTORICAL.value)
        report["replay"] = result.to_dict()
        return report

    def walk_forward(
        self,
        closes: Sequence[float],
        *,
        train_size: int = 80,
        valid_size: int = 20,
        step: int | None = None,
        engine_version: str = "1.0",
    ) -> dict[str, Any]:
        folds = walk_forward_folds(len(closes), train_size=train_size, valid_size=valid_size, step=step)
        fold_metrics = []
        all_outcomes: list[dict[str, Any]] = []
        for fold in folds:
            # Only history through validation end is visible; predictions start after min_history
            segment = list(closes[: fold.valid_end])
            replay = replay_series(
                segment,
                predict_fn=simple_bias_predictor,
                step=max(1, valid_size // 4),
                min_history=max(10, min(train_size, len(segment) // 2)),
                engine_version=engine_version,
                archive=False,
            )
            # Restrict to outcomes from validation window indices
            valid_outcomes = []
            for point in replay.points:
                if fold.valid_start <= point.index < fold.valid_end:
                    valid_outcomes.extend(point.outcomes)
            if not valid_outcomes:
                valid_outcomes = list(replay.outcomes)
            m = aggregate_outcome_metrics(valid_outcomes, horizon="24h")
            m["fold"] = fold.to_dict()
            fold_metrics.append(m)
            all_outcomes.extend(valid_outcomes)

        summary = summarize_fold_metrics(fold_metrics)
        report = self.evaluate_outcomes(
            all_outcomes,
            engine_version=engine_version,
            method=ValidationMethod.WALK_FORWARD.value,
        )
        report["walk_forward"] = summary
        report["folds"] = [f.to_dict() for f in folds]
        return report

    def evaluate_outcomes(
        self,
        outcomes: list[dict[str, Any]],
        *,
        engine_version: str = "1.0",
        method: str = ValidationMethod.CONTINUOUS.value,
        validation_period: str | None = None,
        baseline_accuracy: float | None = None,
    ) -> dict[str, Any]:
        by_horizon = {h: aggregate_outcome_metrics(outcomes, horizon=h) for h in ("1h", "4h", "24h", "7d")}
        primary = by_horizon.get("24h") or aggregate_outcome_metrics(outcomes)

        pairs = []
        prob_pairs = []
        for o in outcomes:
            if o.get("direction_correct") is None:
                continue
            conf = float(o.get("confidence") or 50)
            pairs.append((conf, bool(o["direction_correct"])))
            # Use continuation probability if present on nested payload
            dist = o.get("probability_distribution") or {}
            if isinstance(dist, dict) and dist:
                prob = float(next(iter(dist.values())))
                prob_pairs.append((prob, bool(o["direction_correct"])))

        calib = calibration_table(pairs) if pairs else {"bins": {}, "label": "Moderate", "avg_gap": None}
        prob_calib = probability_calibration(prob_pairs) if prob_pairs else {"bins": {}, "avg_gap": None}
        regimes = regime_accuracy(outcomes)
        layers = layer_contribution(outcomes)

        baseline = baseline_accuracy if baseline_accuracy is not None else float(primary.get("accuracy") or 0)
        # Compare first half vs second half as recent drift proxy
        mid = max(1, len(outcomes) // 2)
        recent = aggregate_outcome_metrics(outcomes[mid:], horizon="24h")
        drift = detect_performance_drift(float(recent.get("accuracy") or 0), baseline)
        drift = merge_drift_reports([drift])

        failures = []
        for o in outcomes:
            if o.get("direction_correct") is False:
                failures.append(
                    {
                        "prediction_id": o.get("prediction_id"),
                        "horizon": o.get("horizon"),
                        **categorize_failure(return_pct=o.get("return_pct")),
                    }
                )

        period = validation_period or utc_now_iso()[:10]
        obj = build_validation_object(
            primary,
            engine_version=engine_version,
            validation_period=period,
            method=method,
            calibration_label=str(calib.get("label") or "Moderate"),
            regime_results=regimes,
            layer_contribution=layers,
            calibration_bins=calib.get("bins") or {},
            drift_detected=drift.drift_detected,
            drift_status=drift.status,
        )

        dashboard = build_dashboard(
            metrics=primary,
            calibration=calib,
            regime_results=regimes,
            layer_contribution=layers,
            drift=drift.to_dict(),
            failures=failures[-20:],
        )

        log.info(
            "validation method={} accuracy={} calib={} drift={}",
            method,
            primary.get("accuracy"),
            calib.get("label"),
            drift.status,
        )
        return {
            "validation_object": obj.to_dict(),
            "metrics_by_horizon": by_horizon,
            "primary_metrics": primary,
            "calibration": calib,
            "probability_calibration": prob_calib,
            "regime_results": regimes,
            "layer_contribution": layers,
            "drift": drift.to_dict(),
            "failures": failures[-50:],
            "dashboard": dashboard,
        }

    def continuous_from_report(
        self,
        report: dict[str, Any],
        *,
        closes: Sequence[float] | None = None,
        entry_idx: int | None = None,
    ) -> dict[str, Any]:
        """Archive every published prediction; optionally score when outcomes available."""
        rec = archive_from_ai_report(report, source="continuous")
        paper = paper_ledger.open_from_prediction(rec)
        result: dict[str, Any] = {"prediction": rec.to_dict(), "paper_trade": paper.to_dict() if paper else None}
        if closes is not None and entry_idx is not None:
            outcomes = [o.to_dict() for o in evaluate_prediction(rec, closes=closes, entry_idx=entry_idx)]
            for o in outcomes:
                o["market_bias"] = rec.market_bias
                o["predicted_bias"] = rec.market_bias
                o["confidence"] = rec.confidence
                o["market_regime"] = rec.market_regime
                o["layer_scores"] = rec.layer_scores
            result["evaluation"] = self.evaluate_outcomes(outcomes, method=ValidationMethod.CONTINUOUS.value)
        return result

    def version_compare(
        self,
        production_outcomes: list[dict[str, Any]],
        candidate_outcomes: list[dict[str, Any]],
        *,
        horizon: str = "24h",
    ) -> dict[str, Any]:
        return compare_engines(production_outcomes, candidate_outcomes, horizon=horizon)

    def approve(self, validation_object: dict[str, Any], *, approver: str, notes: str = "") -> dict[str, Any]:
        from src.validation.contracts import ValidationObject

        fields = {f.name for f in ValidationObject.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        obj = ValidationObject(**{k: v for k, v in validation_object.items() if k in fields})
        return approve_validation(obj, approver=approver, notes=notes).to_dict()

    def dashboard(self) -> dict[str, Any]:
        return build_dashboard()
