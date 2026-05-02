"""
detector.py - Network Anomaly Detector for NetPulse-Shield
Version : Expertise RST & Évaluation de Performance
"""
import os
import joblib
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
# ✅ Single line — Ruff is happy
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, f1_score, precision_score, recall_score

# Configure logging for production-grade monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkAnomalyDetector:
    """Détecteur d'anomalies avec expertise en filtrage et évaluation."""

    def __init__(self, contamination='auto', n_estimators=100,
                 model_path="models/netpulse_model.joblib",
                 persist_to_db: bool = False,
                 db_path: str = "sqlite:///alerts.db"):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model_path = model_path
        self.persist_to_db = persist_to_db
        self.db_path = db_path
        self.scaler_path = model_path.replace(".joblib", "_scaler.joblib")

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.feature_columns = None
        self.features_path = model_path.replace(".joblib", "_features.joblib")
        self.metadata_path = model_path.replace(".joblib", "_metadata.json")
        self.model_metadata = {}
        
        # Try to load existing model with backward compatibility and graceful fallback
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                
                # Load feature columns (new approach)
                if os.path.exists(self.features_path):
                    self.feature_columns = joblib.load(self.features_path)
                    logger.info(f"Loaded feature columns from {self.features_path}")
                else:
                    logger.warning(
                        f"Feature columns file not found at {self.features_path}. "
                        "Will recalculate on next training. This is normal for legacy models."
                    )
                
                # Load metadata if available
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r') as f:
                        self.model_metadata = json.load(f)
                    logger.info(
                        f"Model loaded from {self.model_metadata.get('created_at', 'unknown date')} "
                        f"with {len(self.feature_columns or [])} features"
                    )
                else:
                    logger.warning(
                        f"Metadata file not found at {self.metadata_path}. "
                        "This is normal for legacy models (created before version 2.0)."
                    )
                
                logger.info(f"✅ Model and Scaler loaded successfully from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}. Initializing fresh detector.")
                self.model = None
                self.scaler = StandardScaler()
        else:
            self.model = None
            self.scaler = StandardScaler()
            logger.info("🔆 New detector initialized (awaiting training).")

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def preprocess(self, df: pd.DataFrame, training: bool = False) -> np.ndarray:
        """Preprocess input data with schema validation and defensive checks."""
        if df is None or len(df) == 0:
            raise ValueError("Input dataframe is empty or None.")
        
        cols_to_exclude = ['Label', 'label', 'anomaly', 'is_anomaly', 'anomaly_score']
        
        # During training: discover features; during prediction: use saved features
        if training or self.feature_columns is None:
            self.feature_columns = [
                c for c in df.select_dtypes(include=[np.number]).columns
                if c not in cols_to_exclude
            ]
            if training:
                logger.info(f"Training: discovered {len(self.feature_columns)} numeric features")
        
        if not self.feature_columns:
            raise ValueError(
                f"No numeric features found. Available columns: {df.columns.tolist()}. "
                "Expected at least one numeric column for training."
            )

        # Schema validation: check for missing columns and extra columns
        missing_cols = [c for c in self.feature_columns if c not in df.columns]
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        extra_cols = [c for c in numeric_cols if c not in self.feature_columns and c not in cols_to_exclude]
        
        if missing_cols:
            error_msg = (
                f"Schema mismatch: Missing {len(missing_cols)} required columns: {missing_cols}. "
                f"Expected: {self.feature_columns}. Available: {df.columns.tolist()}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if extra_cols and not training:
            logger.warning(
                f"Schema drift detected: Input has {len(extra_cols)} extra numeric columns "
                f"not seen during training: {extra_cols}. These will be ignored."
            )

        features = df[self.feature_columns].copy()
        features.replace([np.inf, -np.inf], np.nan, inplace=True)
        features.fillna(0, inplace=True)

        if training:
            return self.scaler.fit_transform(features)
        else:
            return self.scaler.transform(features)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, X: np.ndarray, y_true: pd.Series = None) -> None:
        """Détermine la contamination réelle et entraîne l'Isolation Forest."""

        if self.contamination == 'auto' and y_true is not None:
            # Use the true attack rate from the labels
            attack_rate = (y_true != 0).sum() / len(y_true)
            self.contamination = float(np.clip(attack_rate, 0.01, 0.5))
            logger.info(f"📊 Detected real contamination: {self.contamination:.4f} "
                  f"({self.contamination * 100:.2f}% of data)")
        elif self.contamination == 'auto':
            self.contamination = 0.05
            logger.warning(f"No labels found — using default contamination: {self.contamination}")

        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=42,
            n_jobs=-1,
        )

        logger.info("🧠 Training Isolation Forest...")
        self.model.fit(X)

        # Save model artifacts
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        joblib.dump(self.feature_columns, self.features_path)
        
        # Save metadata for versioning and audit trail
        self.model_metadata = {
            "created_at": datetime.now().isoformat(),
            "contamination": float(self.contamination),
            "n_estimators": self.n_estimators,
            "feature_columns": self.feature_columns,
            "n_features": len(self.feature_columns),
            "model_version": "2.0",
        }
        with open(self.metadata_path, 'w') as f:
            json.dump(self.model_metadata, f, indent=2)
        
        logger.info(
            f"💾 Model, Scaler, Features, and Metadata saved. "
            f"({len(self.feature_columns)} features, contamination={self.contamination})"
        )

    # ------------------------------------------------------------------
    # Evaluation (Fix #1 — labeled data)
    # ------------------------------------------------------------------

    def evaluate(self, X: np.ndarray, y_true: pd.Series) -> dict:
        """
        Compute and print full evaluation metrics against ground-truth labels.

        Expects y_true to be binary: 0 = normal, 1 = attack.
        Returns a dict with precision, recall, f1, roc_auc, and false_positive_rate.
        """
        if y_true is None:
            print("⚠️  No labels provided — skipping evaluation.")
            return {}

        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)

        # Isolation Forest: -1 → attack (1), 1 → normal (0)
        y_pred = (predictions == -1).astype(int)
        y_true_bin = (y_true != 0).astype(int)

        # Anomaly score: lower = more anomalous → negate for ROC
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
        print("📈  Model Performance Report")
        print("=" * 50)
        print(classification_report(
            y_true_bin, y_pred, target_names=["Normal", "Attack"]
        ))
        print(f"  ROC-AUC Score      : {roc_auc:.4f}")
        print(f"  False Positive Rate: {fpr:.4f}  ({fp} normal flows wrongly flagged)")
        print("\n  Confusion Matrix:")
        print(f"    True  Negatives  (normal, correct) : {tn}")
        print(f"    False Positives  (normal, flagged)  : {fp}  ← analyst alert fatigue")
        print(f"    False Negatives  (attack,  missed)  : {fn}  ← missed threats")
        print(f"    True  Positives  (attack,  caught)  : {tp}")
        print("=" * 50)

        return metrics

    # ------------------------------------------------------------------
    # Contamination tuning (Fix #2)
    # ------------------------------------------------------------------

    def tune_contamination(
        self,
        df: pd.DataFrame,
        label_column: str = "Label",
        candidates: list = None,
    ) -> float:
        """
        Try multiple contamination values on a held-out validation split.
        Sets self.contamination to the value that maximises F1 and re-trains.
        Returns the best contamination value found.
        """
        if candidates is None:
            candidates = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]

        y_all = (df[label_column] != 0).astype(int)

        # 80/20 split — tune on the validation portion
        train_df, val_df = train_test_split(
            df, test_size=0.2, random_state=42, stratify=y_all
        )

        X_train = self.preprocess(train_df, training=True)
        val_features = val_df[self.feature_columns].copy()
        val_features.replace([np.inf, -np.inf], np.nan, inplace=True)
        val_features.fillna(0, inplace=True)
        X_val = self.scaler.transform(val_features)
        y_val = (val_df[label_column] != 0).astype(int)

        best_f1, best_c = -1.0, candidates[0]

        print("\n🔍 Tuning contamination parameter on validation split...")
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

            marker = " ←" if f > best_f1 else ""
            print(f"  {c:>15.3f} | {p:>10.4f} | {r:>8.4f} | {f:>8.4f}{marker}")

            if f > best_f1:
                best_f1, best_c = f, c

        print(f"\n✅ Best contamination: {best_c}  (F1 = {best_f1:.4f})")
        self.contamination = best_c
        return best_c

    # ------------------------------------------------------------------
    # Unsupervised sanity check (Fix #3 — no labels)
    # ------------------------------------------------------------------

    def evaluate_unsupervised(self, df: pd.DataFrame) -> None:
        """
        When no labels exist, split 80/20, train on the majority partition,
        and report anomaly score statistics on the held-out set.
        Helps verify the model isn't flagging randomly.
        """
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

        X_train = self.preprocess(train_df, training=True)
        self.train(X_train)

        test_features = test_df[self.feature_columns].copy()
        test_features.replace([np.inf, -np.inf], np.nan, inplace=True)
        test_features.fillna(0, inplace=True)
        X_test = self.scaler.transform(test_features)
        _, scores = self.model.predict(X_test), self.model.decision_function(X_test)

        flagged_pct = (scores < 0).mean() * 100

        print("\n" + "=" * 50)
        print("📊  Anomaly Score Distribution (test set, no labels)")
        print("=" * 50)
        print(f"  Mean score   : {scores.mean():.4f}")
        print(f"  Std  score   : {scores.std():.4f}")
        print(f"  Min  score   : {scores.min():.4f}  ← most anomalous")
        print(f"  Max  score   : {scores.max():.4f}  ← most normal")
        print(f"  % flagged    : {flagged_pct:.2f}%  "
              f"(contamination={self.contamination})")
        print("=" * 50)

    # ------------------------------------------------------------------
    # Main analysis method
    # ------------------------------------------------------------------

    def analyze(self, df: pd.DataFrame, force_train: bool = False) -> pd.DataFrame:
        """Analyze dataframe for anomalies with defensive validation and logging."""
        if df is None or len(df) == 0:
            raise ValueError("Input dataframe is empty or None. Cannot analyze.")
        
        is_trained = self.model is not None and hasattr(self.model, "estimators_")
        y_true = df['Label'] if 'Label' in df.columns else None

        # Schema validation before preprocessing
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols_to_exclude = ['Label', 'label', 'anomaly', 'is_anomaly', 'anomaly_score']
        available_features = [c for c in numeric_cols if c not in cols_to_exclude]
        
        if not available_features:
            error_msg = (
                f"No numeric features available for analysis. "
                f"Columns: {df.columns.tolist()}. "
                f"Please provide numeric data columns."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Analyzing {len(df)} rows with {len(available_features)} numeric features")

        X = self.preprocess(df, training=(not is_trained or force_train))

        if not is_trained or force_train:
            logger.info("Model not trained or force_train=True. Training now...")
            self.train(X, y_true)
            logger.info("Training complete.")
        else:
            logger.info(f"Using existing model (trained on {len(self.feature_columns)} features)")

        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)

        results = df.copy()
        results["anomaly"]      = predictions
        results["anomaly_score"] = scores
        results["is_anomaly"]   = results["anomaly"] == -1
        
        n_anomalies = results["is_anomaly"].sum()
        logger.info(f"Detection complete: {n_anomalies} anomalies found ({100*n_anomalies/len(results):.2f}%)")

        if y_true is not None:
            self.evaluate(X, y_true)

        # Persist alerts to DB if requested (only anomalous rows)
        if self.persist_to_db:
            try:
                from db import persist_alerts_from_df

                alerts_df = results[results["is_anomaly"]].copy()
                if len(alerts_df) > 0:
                    inserted = persist_alerts_from_df(alerts_df, db_path=self.db_path)
                    logger.info(f"💾 Persisted {inserted} alerts to DB: {self.db_path}")
                else:
                    logger.info("No anomalies to persist.")
            except Exception as e:
                logger.warning(f"Failed to persist alerts to DB: {e}")

        return results


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    print("NetPulse-Shield — Network Anomaly Detector")
    print("=" * 50)

    data_path = os.path.join("data", "final_project_data.csv")

    if not os.path.exists(data_path):
        print(f"❌ Error: {data_path} not found.")
        exit()

    df = pd.read_csv(data_path)
    has_labels = "Label" in df.columns

    print(f"📂 Loaded {len(df):,} records — "
          f"{'labels found ✅' if has_labels else 'no labels ⚠️'}")

    if has_labels:
        attack_count  = (df["Label"] != 0).sum()
        normal_count  = (df["Label"] == 0).sum()
        print(f"   Normal  : {normal_count:,} ({normal_count / len(df) * 100:.2f}%)")
        print(f"   Attacks : {attack_count:,} ({attack_count / len(df) * 100:.2f}%)")

    # --- Step 1: tune contamination (only when labels available) ------
    detector = NetworkAnomalyDetector(contamination='auto')

    if has_labels:
        best_c = detector.tune_contamination(df, label_column="Label")
        # Override with the tuned value before full run
        detector.contamination = best_c

    # --- Step 2: full analysis + evaluation ---------------------------
    results = detector.analyze(df, force_train=True)

    anomalies = results[results["is_anomaly"]]
    print(f"\nTotal records      : {len(results):,}")
    print(f"Anomalies detected : {len(anomalies):,} "
          f"({len(anomalies) / len(results) * 100:.2f}%)")

    # --- Step 3: save top alerts --------------------------------------
    sort_col = "anomaly_score"
    top_anomalies = anomalies.sort_values(by=sort_col).head(10)
    top_anomalies.to_csv("alerts.csv", index=False)
    print("\n✅ Top 10 alerts saved to 'alerts.csv'")