"""
detector.py - Network Anomaly Detector for NetPulse-Shield

Uses scikit-learn's Isolation Forest algorithm to identify anomalous
network traffic patterns that may indicate security threats such as
DDoS attacks, port scans, or data exfiltration attempts.
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
        """
        Initialise the detector.

        Parameters
        ----------
        contamination : float
            Expected proportion of anomalies in the dataset (0 < contamination < 0.5).
        n_estimators : int
            Number of trees in the Isolation Forest ensemble.
        random_state : int
            Seed for reproducibility.
        """
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
        )
        self.scaler = StandardScaler()
        self.feature_columns = None

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load network traffic data from a CSV file."""
        return pd.read_csv(filepath)

    def preprocess(
        self, df: pd.DataFrame, feature_columns: list | None = None
    ) -> np.ndarray:
        """
        Select numeric features, fill missing values, and scale them.

        Parameters
        ----------
        df : pd.DataFrame
            Raw traffic data.
        feature_columns : list[str] | None
            Explicit list of columns to use.  If *None*, all numeric
            columns are selected automatically.

        Returns
        -------
        np.ndarray
            Scaled feature matrix ready for model input.
        """
        if feature_columns is not None:
            self.feature_columns = feature_columns
        else:
            self.feature_columns = df.select_dtypes(
                include=[np.number]
            ).columns.tolist()

        features = df[self.feature_columns].fillna(0)
        return self.scaler.fit_transform(features)

    # ------------------------------------------------------------------
    # Model operations
    # ------------------------------------------------------------------

    def train(self, X: np.ndarray) -> None:
        """Fit the Isolation Forest on a pre-processed feature matrix."""
        self.model.fit(X)

    def detect(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Run anomaly detection on pre-processed features.

        Returns
        -------
        predictions : np.ndarray
            +1 for normal traffic, -1 for anomalous traffic.
        scores : np.ndarray
            Anomaly scores (lower = more anomalous).
        """
        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)
        return predictions, scores

    def analyze(
        self, df: pd.DataFrame, feature_columns: list | None = None
    ) -> pd.DataFrame:
        """
        Full pipeline: preprocess → train → detect → annotate.

        Adds three columns to a copy of *df*:
          - ``anomaly``       : raw Isolation Forest label (+1 / -1)
          - ``anomaly_score`` : continuous anomaly score
          - ``is_anomaly``    : boolean flag (True = anomalous)

        Parameters
        ----------
        df : pd.DataFrame
            Raw traffic data.
        feature_columns : list[str] | None
            Columns to use as features (auto-detected if *None*).

        Returns
        -------
        pd.DataFrame
            Annotated copy of the input DataFrame.
        """
        X = self.preprocess(df, feature_columns)
        self.train(X)
        predictions, scores = self.detect(X)

        results = df.copy()
        results["anomaly"] = predictions
        results["anomaly_score"] = scores
        results["is_anomaly"] = results["anomaly"] == -1
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_model(self, filepath: str) -> None:
        """Persist the trained model, scaler, and feature list to disk."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "features": self.feature_columns,
            },
            filepath,
        )
        print(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """Restore a previously saved model from disk."""
        data = joblib.load(filepath)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_columns = data["features"]
        print(f"Model loaded from {filepath}")


# ---------------------------------------------------------------------------
# Sample-data generator
# ---------------------------------------------------------------------------


def generate_sample_data(n_samples: int = 500, anomaly_rate: float = 0.05) -> pd.DataFrame:
    """
    Generate synthetic network-traffic data for demonstration purposes.

    Normal traffic resembles everyday HTTP/HTTPS/SSH flows.  Anomalous
    traffic simulates DDoS bursts and port-scan patterns.

    Parameters
    ----------
    n_samples : int
        Total number of traffic records to generate.
    anomaly_rate : float
        Fraction of records that should be anomalous (0 < rate < 1).

    Returns
    -------
    pd.DataFrame
        Shuffled DataFrame with columns:
        packet_size, duration, src_port, dst_port,
        bytes_sent, packets_per_second.
    """
    rng = np.random.default_rng(42)
    n_normal = int(n_samples * (1 - anomaly_rate))
    n_anomaly = n_samples - n_normal

    normal = pd.DataFrame(
        {
            "packet_size": rng.normal(500, 100, n_normal),
            "duration": rng.exponential(1.0, n_normal),
            "src_port": rng.choice([80, 443, 8080, 22, 21], n_normal),
            "dst_port": rng.integers(1024, 65535, n_normal),
            "bytes_sent": rng.normal(1000, 200, n_normal),
            "packets_per_second": rng.normal(10, 3, n_normal),
        }
    )

    # Anomalous traffic: very high packet rates and large transfers
    anomalies = pd.DataFrame(
        {
            "packet_size": rng.normal(1400, 50, n_anomaly),
            "duration": rng.exponential(0.01, n_anomaly),
            "src_port": rng.integers(1024, 65535, n_anomaly),
            "dst_port": rng.integers(1, 1024, n_anomaly),
            "bytes_sent": rng.normal(50_000, 5_000, n_anomaly),
            "packets_per_second": rng.normal(500, 100, n_anomaly),
        }
    )

    df = pd.concat([normal, anomalies], ignore_index=True).sample(
        frac=1, random_state=42
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("NetPulse-Shield — Network Anomaly Detector")
    print("=" * 50)

    data_path = os.path.join("data", "sample_traffic.csv")

    if os.path.exists(data_path):
        print(f"Loading data from {data_path} …")
        df = pd.read_csv(data_path)
    else:
        print("Generating sample traffic data …")
        df = generate_sample_data(n_samples=500)
        os.makedirs("data", exist_ok=True)
        df.to_csv(data_path, index=False)
        print(f"Sample data saved to {data_path}")

    detector = NetworkAnomalyDetector(contamination=0.1)
    results = detector.analyze(df)

    anomalies = results[results["is_anomaly"]]
    print(f"\nTotal records analysed : {len(results)}")
    print(f"Anomalies detected     : {len(anomalies)}  ({len(anomalies) / len(results) * 100:.1f} %)")

    display_cols = [c for c in ["packet_size", "duration", "bytes_sent", "packets_per_second", "anomaly_score"] if c in anomalies.columns]
    print("\nTop 5 anomalies (lowest score = most anomalous):")
    print(anomalies.nsmallest(5, "anomaly_score")[display_cols].to_string(index=False))
