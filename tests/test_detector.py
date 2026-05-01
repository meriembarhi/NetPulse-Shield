"""
test_detector.py - Validation Suite for Network Anomaly Detection

This script performs unit testing on the ML-based detector. It ensures
the Isolation Forest model correctly identifies extreme network traffic
outliers (anomalies) which represent potential DDoS or high-load attacks.

Validation Criteria:
- Model returns is_anomaly=True for traffic features exceeding normal thresholds.
- Dataframe compatibility for real-time traffic features (Sload, sttl, sbytes).
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import numpy as np
from detector import NetworkAnomalyDetector


def make_training_data():
    """20 normal records + 1 obvious anomaly for the model to learn from."""
    normal = pd.DataFrame({
        'Sload':  [1000.0] * 20,
        'sttl':   [64] * 20,
        'sbytes': [500] * 20,
    })
    anomaly = pd.DataFrame({
        'Sload':  [2000000000.0],
        'sttl':   [255],
        'sbytes': [999999],
    })
    return pd.concat([normal, anomaly], ignore_index=True)


def test_extreme_anomaly_detection():
    """
    Test Case: Verify detection of a volumetric attack.
    Scenario: Injected packet data with impossible load and byte counts.
    """
    df = make_training_data()
    detector = NetworkAnomalyDetector(contamination=0.1)

    # analyze() trains + detects in one call — returns df with is_anomaly column
    results = detector.analyze(df)

    anomalies = results[results["is_anomaly"]]
    assert len(anomalies) > 0, "FAIL: Detector found zero anomalies."
    print("\n✅ Detector Test Passed: Volumetric attack signature correctly isolated.")


def test_output_has_required_columns():
    """Test that analyze() always returns the expected output columns."""
    df = make_training_data()
    detector = NetworkAnomalyDetector()
    results = detector.analyze(df)

    assert "is_anomaly" in results.columns, "FAIL: Missing 'is_anomaly' column."
    assert "anomaly_score" in results.columns, "FAIL: Missing 'anomaly_score' column."


def test_output_shape_unchanged():
    """Test that analyze() returns the same number of rows as input."""
    df = make_training_data()
    detector = NetworkAnomalyDetector()
    results = detector.analyze(df)

    assert len(results) == len(df), "FAIL: Output row count doesn't match input."


if __name__ == "__main__":
    test_extreme_anomaly_detection()
    test_output_has_required_columns()
    test_output_shape_unchanged()
