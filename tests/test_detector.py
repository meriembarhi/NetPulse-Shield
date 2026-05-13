"""Tests for the network anomaly detector using realistic CSV-shaped data."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from detector import NetworkAnomalyDetector


FIXTURES_DIR = Path(__file__).parent / "fixtures"
DETECTOR_FIXTURE = FIXTURES_DIR / "detector_sample.csv"


def load_detector_fixture() -> pd.DataFrame:
    return pd.read_csv(DETECTOR_FIXTURE)


def make_detector(tmp_path: Path, contamination: float = 0.1) -> NetworkAnomalyDetector:
    model_path = tmp_path / "netpulse_model.joblib"
    # Disable DB persistence during unit tests to avoid filesystem side-effects
    return NetworkAnomalyDetector(
        contamination=contamination,
        model_path=str(model_path),
        persist_to_db=False,
    )


def test_analyze_realistic_csv_columns_and_shape(tmp_path):
    df = load_detector_fixture()
    detector = make_detector(tmp_path)

    results = detector.analyze(df, force_train=True)

    assert len(results) == len(df)
    assert "anomaly" in results.columns
    assert "anomaly_score" in results.columns
    assert "is_anomaly" in results.columns
    assert results["anomaly_score"].notna().all()


def test_analyze_handles_infinities_and_missing_values(tmp_path):
    df = load_detector_fixture().copy()
    df.loc[0, "Sload"] = np.inf
    df.loc[1, "Dload"] = -np.inf
    df.loc[2, "sbytes"] = np.nan

    detector = make_detector(tmp_path)
    results = detector.analyze(df, force_train=True)

    assert len(results) == len(df)
    assert results["anomaly_score"].notna().all()
    assert results["is_anomaly"].dtype == bool


def test_analyze_requires_at_least_one_numeric_feature(tmp_path):
    df = pd.DataFrame({"Label": [0, 1, 0]})
    detector = make_detector(tmp_path)

    with pytest.raises(ValueError):
        detector.analyze(df, force_train=True)


def test_analyze_writes_metrics_json_when_labels_present(tmp_path):
    df = load_detector_fixture()
    detector = make_detector(tmp_path)
    out = tmp_path / "out" / "metrics.json"
    detector.analyze(df, force_train=True, metrics_output_path=str(out))

    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "timestamp" in payload
    assert payload["n_rows"] == len(df)
    assert "metrics" in payload
    assert "f1" in payload["metrics"]
    assert "confusion_matrix" in payload["metrics"]
    assert payload["metrics"]["confusion_matrix"]["counts"] == [
        [payload["metrics"]["true_negatives"], payload["metrics"]["false_positives"]],
        [payload["metrics"]["false_negatives"], payload["metrics"]["true_positives"]],
    ]


def test_analyze_metrics_json_includes_lof_when_compare_lof(tmp_path):
    df = load_detector_fixture()
    detector = make_detector(tmp_path)
    out = tmp_path / "with_lof.json"
    detector.analyze(
        df,
        force_train=True,
        metrics_output_path=str(out),
        compare_lof=True,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "baselines" in payload
    assert "local_outlier_factor" in payload["baselines"]
    assert payload["baselines"]["local_outlier_factor"]["method"] == "local_outlier_factor"


def test_analyze_flags_clear_outlier(tmp_path):
    """Isolation Forest should flag an extreme point among near-duplicate normals."""
    rng = np.random.default_rng(42)
    n_normal = 60
    base = rng.normal(0.0, 1.0, size=(n_normal, 3))
    df = pd.DataFrame(base, columns=["f1", "f2", "f3"])
    df["Label"] = 0
    outlier = pd.DataFrame([{"f1": 1e9, "f2": -1e9, "f3": 1e9, "Label": 0}])
    df = pd.concat([df, outlier], ignore_index=True)
    # One benign-labeled row so evaluate() sees both label values (avoids ROC undefined warnings).
    df.loc[n_normal // 2, "Label"] = 1

    detector = make_detector(tmp_path, contamination=0.15)
    results = detector.analyze(df, force_train=True)

    assert results["is_anomaly"].sum() >= 1
    assert bool(results.loc[len(df) - 1, "is_anomaly"]) is True


def test_tune_contamination_returns_a_default_candidate(tmp_path):
    df = load_detector_fixture()
    detector = make_detector(tmp_path, contamination=0.1)
    best = detector.tune_contamination(df, label_column="Label")
    default_candidates = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
    assert best in default_candidates
    assert isinstance(best, float)
