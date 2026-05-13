"""Tests for optional LOF baseline (same X as Isolation Forest)."""

from pathlib import Path

import pandas as pd

from baselines import evaluate_lof


FIXTURES_DIR = Path(__file__).parent / "fixtures"
DETECTOR_FIXTURE = FIXTURES_DIR / "detector_sample.csv"


def test_evaluate_lof_returns_expected_keys():
    df = pd.read_csv(DETECTOR_FIXTURE)
    y = df["Label"]
    X = df.drop(columns=["Label"]).to_numpy(dtype=float)
    out = evaluate_lof(X, y, contamination=0.1)

    assert out["method"] == "local_outlier_factor"
    assert "precision" in out
    assert "confusion_matrix" in out
    assert out["n_neighbors"] >= 2
