"""Tests for the network anomaly detector using realistic CSV-shaped data."""

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
