"""
detector.py - Network Anomaly Detector for NetPulse-Shield
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, f1_score, precision_score, recall_score


class NetworkAnomalyDetector:
    def __init__(self, contamination='auto', n_estimators=100,
                 model_path="models/netpulse_model.joblib"):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model_path = model_path
        self.scaler_path = model_path.replace(".joblib", "_scaler.joblib")

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.feature_columns = None

        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            print(f"[OK] Model and Scaler loaded from {self.model_path}")
        else:
            self.model = None
            self.scaler = StandardScaler()
            print("[INFO] New detector initialized (awaiting training).")

    def preprocess(self, df: pd.DataFrame, training: bool = False) -> np.ndarray:
        cols_to_exclude = ['Label', 'label', 'anomaly', 'is_anomaly', 'anomaly_score']
        self.feature_columns = [
            c for c in df.select_dtypes(include=[np.number]).columns
            if c not in cols_to_exclude
        ]

        features = df[self.feature_columns].copy()
        features.replace([np.inf, -np.inf], np.nan, inplace=True)
        features.fillna(0, inplace=True)

        if training:
            return self.scaler.fit_transform(features)
        else:
            return self.scaler.transform(features)

    def train(self, X: np.ndarray, y_true: pd.Series = None) -> None:
        if self.contamination == 'auto' and y_true is not None:
            attack_rate = (y_true != 0).sum() / len(y_true)
            self.contamination = float(np.clip(attack_rate, 0.01, 0.5))
            print(f"[DATA] Contamination detected: {self.contamination:.4f} "
                  f"({self.contamination * 100:.2f}% of data)")
        elif self.contamination == 'auto':
            self.contamination = 0.05
            print(f"[INFO] No labels -- using default contamination: {self.contamination}")

        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=42,
            n_jobs=-1,
        )

        print("[INFO] Training Isolation Forest...")
        self.model.fit(X)

        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        print("[OK] Model and Scaler saved.")

    def evaluate(self, X: np.ndarray, y_true: pd.Series) -> dict:
        if y_true is None:
            print("[INFO] No labels provided -- skipping evaluation.")
            return {}

        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)

        y_pred = (predictions == -1).astype(int)
        y_true_bin = (y_true != 0).astype(int)

        y_scores = -scores

        precision  = precision_score(y_true_bin, y_pred, zero_division=0)
        recall     = recall_score(y_true_bin, y_pred, zero_division=0)
        f1         = f1_score(y_true_bin, y_pred, zero_division=0)
        roc_auc    = roc_auc_score(y_true_bin, y_scores)

        tn, fp, fn, tp = confusion_matrix(y_true_bin, y_pred).ravel()
        fpr = fp / max(tn + fp, 1)

        metrics = {
            "precision":           precision,
            "recall":              recall,
            "f1":                  f1,
            "roc_auc":             roc_auc,
            "false_positive_rate": fpr,
            "true_positives":      int(tp),
            "false_positives":     int(fp),
            "false_negatives":     int(fn),
            "true_negatives":      int(tn),
        }

        print("\n" + "=" * 50)
        print("[METRICS] Model Performance Report")
        print("=" * 50)
        print(classification_report(
            y_true_bin, y_pred, target_names=["Normal", "Attack"]
        ))
        print(f"  ROC-AUC Score      : {roc_auc:.4f}")
        print(f"  False Positive Rate: {fpr:.4f}  ({fp} normal flows wrongly flagged)")
        print("\n  Confusion Matrix:")
        print(f"    True  Negatives  (normal, correct) : {tn}")
        print(f"    False Positives  (normal, flagged)  : {fp}")
        print(f"    False Negatives  (attack,  missed)  : {fn}")
        print(f"    True  Positives  (attack,  caught)  : {tp}")
        print("=" * 50)

        return metrics

    def tune_contamination(
        self,
        df: pd.DataFrame,
        label_column: str = "Label",
        candidates: list = None,
    ) -> float:
        if candidates is None:
            candidates = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]

        y_all = (df[label_column] != 0).astype(int)

        train_df, val_df = train_test_split(
            df, test_size=0.2, random_state=42, stratify=y_all
        )

        X_train = self.preprocess(train_df, training=True)
        X_val   = self.scaler.transform(
            val_df[self.feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)
        )
        y_val   = (val_df[label_column] != 0).astype(int)

        best_f1, best_c = -1.0, candidates[0]

        print("\n[TUNE] Tuning contamination on validation split...")
        print(f"  {'contamination':>15} | {'precision':>10} | {'recall':>8} | {'f1':>8}")
        print("  " + "-" * 50)

        for c in candidates:
            model = IsolationForest(
                contamination=c, n_estimators=self.n_estimators,
                random_state=42, n_jobs=-1
            )
            model.fit(X_train)
            y_pred = (model.predict(X_val) == -1).astype(int)

            p = precision_score(y_val, y_pred, zero_division=0)
            r = recall_score(y_val, y_pred, zero_division=0)
            f = f1_score(y_val, y_pred, zero_division=0)

            marker = " <--" if f > best_f1 else ""
            print(f"  {c:>15.3f} | {p:>10.4f} | {r:>8.4f} | {f:>8.4f}{marker}")

            if f > best_f1:
                best_f1, best_c = f, c

        print(f"\n[OK] Best contamination: {best_c}  (F1 = {best_f1:.4f})")
        self.contamination = best_c
        return best_c

    def evaluate_unsupervised(self, df: pd.DataFrame) -> None:
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

        X_train = self.preprocess(train_df, training=True)
        self.train(X_train)

        X_test = self.scaler.transform(
            test_df[self.feature_columns]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        _, scores = self.model.predict(X_test), self.model.decision_function(X_test)

        flagged_pct = (scores < 0).mean() * 100

        print("\n" + "=" * 50)
        print("[METRICS] Anomaly Score Distribution (test set, no labels)")
        print("=" * 50)
        print(f"  Mean score   : {scores.mean():.4f}")
        print(f"  Std  score   : {scores.std():.4f}")
        print(f"  Min  score   : {scores.min():.4f}")
        print(f"  Max  score   : {scores.max():.4f}")
        print(f"  % flagged    : {flagged_pct:.2f}%  "
              f"(contamination={self.contamination})")
        print("=" * 50)

    def analyze(self, df: pd.DataFrame, force_train: bool = False) -> pd.DataFrame:
        is_trained = self.model is not None and hasattr(self.model, "estimators_")
        y_true = df['Label'] if 'Label' in df.columns else (df['label'] if 'label' in df.columns else None)

        X = self.preprocess(df, training=(not is_trained or force_train))

        if not is_trained or force_train:
            self.train(X, y_true)

        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)

        results = df.copy()
        results["anomaly"]      = predictions
        results["anomaly_score"] = scores
        results["is_anomaly"]   = results["anomaly"] == -1

        if y_true is not None:
            self.evaluate(X, y_true)

        return results


if __name__ == "__main__":
    print("NetPulse-Shield -- Network Anomaly Detector")
    print("=" * 50)

    data_candidates = [
        "data/processed/final_project_data.csv",
        "data/final_project_data.csv",
        "final_project_data.csv",
    ]
    data_path = None
    for p in data_candidates:
        if os.path.exists(p):
            data_path = p
            break

    if data_path is None:
        print(f"[ERROR] Cleaned dataset not found. Run clean_data.py first.")
        print(f"   Looked in: {data_candidates}")
        exit()

    df = pd.read_csv(data_path)
    has_labels = "Label" in df.columns or "label" in df.columns
    label_col = "Label" if "Label" in df.columns else ("label" if "label" in df.columns else None)

    print(f"[OK] Loaded {len(df):,} records from {data_path} "
          f"({'labels found' if has_labels else 'no labels'})")

    if has_labels:
        attack_count = (df[label_col] != 0).sum()
        normal_count = (df[label_col] == 0).sum()
        print(f"   Normal  : {normal_count:,} ({normal_count / len(df) * 100:.2f}%)")
        print(f"   Attacks : {attack_count:,} ({attack_count / len(df) * 100:.2f}%)")

    detector = NetworkAnomalyDetector(contamination='auto')

    if has_labels:
        best_c = detector.tune_contamination(df, label_column=label_col)
        detector.contamination = best_c

    results = detector.analyze(df, force_train=True)

    anomalies = results[results["is_anomaly"]]
    print(f"\nTotal records      : {len(results):,}")
    print(f"Anomalies detected : {len(anomalies):,} "
          f"({len(anomalies) / len(results) * 100:.2f}%)")

    sort_col = "anomaly_score"
    top_anomalies = anomalies.sort_values(by=sort_col).head(10)
    os.makedirs("data/outputs", exist_ok=True)
    top_anomalies.to_csv("data/outputs/alerts.csv", index=False)
    top_anomalies.to_csv("alerts.csv", index=False)
    print(f"\n[OK] Top 10 alerts saved to 'data/outputs/alerts.csv' and 'alerts.csv'")
