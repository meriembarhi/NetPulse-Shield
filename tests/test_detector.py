"""
test_detector.py - Validation Suite for Network Anomaly Detection

This script performs unit testing on the ML-based detector. It ensures 
the Isolation Forest model correctly identifies extreme network traffic 
outliers (anomalies) which represent potential DDoS or high-load attacks.

Validation Criteria:
- Model returns -1 (Anomaly) for traffic features exceeding normal thresholds.
- Dataframe compatibility for real-time traffic features (Sload, sttl, sbytes).
"""

import pandas as pd
import pytest
from detector import NetworkAnomalyDetector

def test_extreme_anomaly_detection():
    """
    Test Case: Verify detection of a volumetric attack.
    Scenario: Injected packet data with impossible load and byte counts.
    """
    detector = NetworkAnomalyDetector()
    
    # Simulating a high-volume volumetric attack signature
    extreme_data = pd.DataFrame([{
        'Sload': 2000000000, # Extremely high source load
        'sttl': 255,        # Maximum Time-To-Live
        'sbytes': 999999    # Massive byte count per flow
    }])
    
    # Scikit-learn Isolation Forest returns -1 for anomalies
    prediction = detector.predict(extreme_data)
    
    assert prediction[0] == -1, "FAIL: The detector did not flag the extreme volumetric signature."
    print("\n✅ Detector Test Passed: Volumetric attack signature correctly isolated.")

if __name__ == "__main__":
    test_extreme_anomaly_detection()