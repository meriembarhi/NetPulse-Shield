"""
detector.py - Network Anomaly Detector for NetPulse-Shield
Corrected Version
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class NetworkAnomalyDetector:
    """Isolation Forest-based detector for network traffic anomalies."""

    def __init__(self, contamination=0.1, n_estimators=100, random_state=42):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
        )
        self.scaler = StandardScaler()
        self.feature_columns = None

    def preprocess(self, df: pd.DataFrame, feature_columns: list | None = None) -> np.ndarray:
        if feature_columns is not None:
            self.feature_columns = feature_columns
        else:
            # Select numeric columns, excluding 'label' or 'anomaly' if they exist
            cols_to_exclude = ['label', 'anomaly', 'is_anomaly', 'anomaly_score']
            self.feature_columns = [c for c in df.select_dtypes(include=[np.number]).columns 
                                   if c not in cols_to_exclude]

        features = df[self.feature_columns].fillna(0)
        return self.scaler.fit_transform(features)

    def train(self, X: np.ndarray) -> None:
        self.model.fit(X)

    def detect(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)
        return predictions, scores

    def analyze(self, df: pd.DataFrame, feature_columns: list | None = None) -> pd.DataFrame:
        X = self.preprocess(df, feature_columns)
        self.train(X)
        predictions, scores = self.detect(X)

        results = df.copy()
        results["anomaly"] = predictions
        results["anomaly_score"] = scores
        results["is_anomaly"] = results["anomaly"] == -1
        return results

# --- Main Entry Point ---

if __name__ == "__main__":
    print("NetPulse-Shield — Network Anomaly Detector")
    print("=" * 50)

    data_path = os.path.join("data", "final_project_data.csv")

    if os.path.exists(data_path):
        print(f"Loading data from {data_path} …")
        df = pd.read_csv(data_path)
    else:
        print(f"Error: {data_path} not found. Please ensure your data is in the data folder.")
        exit()

    # Initialize and run the detector
    detector = NetworkAnomalyDetector(contamination=0.1)
    results = detector.analyze(df)

    # Filter for anomalies
    anomalies = results[results["is_anomaly"]]

    print(f"\nTotal records analysed : {len(results)}")
    print(f"Anomalies detected     : {len(anomalies)}  ({len(anomalies) / len(results) * 100:.1f} %)")

    # 1. Sort by Sload to find the most aggressive threats
    if 'Sload' in anomalies.columns:
        top_anomalies = anomalies.sort_values(by='Sload', ascending=False).head(10)
    else:
        top_anomalies = anomalies.head(10)

    # 2. Save to alerts.csv for the remediator to read
    top_anomalies.to_csv('alerts.csv', index=False)
    
    print("\n✅ Detection complete.")
    print("🚨 Top 10 critical alerts saved to 'alerts.csv'")

    # Display top 5 for visual confirmation
    display_cols = [c for c in ["sttl", "sbytes", "Sload", "Dload", "anomaly_score"] if c in anomalies.columns]
    print("\nTop 5 anomalies (lowest score = most anomalous):")
    print(anomalies.nsmallest(5, "anomaly_score")[display_cols].to_string(index=False))