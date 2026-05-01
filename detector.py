"""
detector.py - Network Anomaly Detector for NetPulse-Shield
Version : Expertise RST & Évaluation de Performance
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report

class NetworkAnomalyDetector:
    """Détecteur d'anomalies avec expertise en filtrage et évaluation."""

    def __init__(self, contamination='auto', n_estimators=100, model_path="models/netpulse_model.joblib"):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model_path = model_path
        self.scaler_path = model_path.replace(".joblib", "_scaler.joblib")
        
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.feature_columns = None
        
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            print(f"✅ Modèle et Scaler chargés depuis {self.model_path}")
        else:
            self.model = None # Sera initialisé pendant l'entraînement
            self.scaler = StandardScaler()
            print("🆕 Nouveau détecteur initialisé (en attente d'entraînement).")

    def preprocess(self, df: pd.DataFrame, training: bool = False) -> np.ndarray:
        # Sélection des colonnes numériques
        cols_to_exclude = ['Label', 'label', 'anomaly', 'is_anomaly', 'anomaly_score']
        self.feature_columns = [c for c in df.select_dtypes(include=[np.number]).columns 
                               if c not in cols_to_exclude]

        features = df[self.feature_columns].copy()
        
        # --- GESTION DES VALEURS INFINIES ET MANQUANTES ---
        features.replace([np.inf, -np.inf], np.nan, inplace=True)
        features.fillna(0, inplace=True)
        
        if training:
            return self.scaler.fit_transform(features)
        else:
            return self.scaler.transform(features)

    def train(self, X: np.ndarray, y_true: pd.Series = None) -> None:
        """Détermine la contamination et entraîne l'Isolation Forest."""
        
        # Calcul de la contamination réelle si Label est présent
        if self.contamination == 'auto' and y_true is not None:
            attack_count = (y_true == 1).sum()
            self.contamination = max(min(attack_count / len(y_true), 0.5), 0.01)
            print(f"📊 Contamination calculée depuis le dataset : {self.contamination:.4f}")
        elif self.contamination == 'auto':
            self.contamination = 0.05 # Valeur par défaut si aucun label n'est fourni

        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=42,
            n_jobs=-1 # Utilise tous les coeurs CPU
        )

        # FIXED: Removed 'f' prefix from string with no placeholders to pass Ruff F541
        print("🧠 Entraînement de l'Isolation Forest...")
        self.model.fit(X)
        
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        print("💾 Modèle et Scaler sauvegardés.")

    def evaluate(self, X: np.ndarray, y_true: pd.Series):
        """Calcule Precision, Recall et F1-score."""
        if y_true is None:
            return
            
        predictions = self.model.predict(X)
        # Mapping: Isolation Forest (-1 = Anomaly, 1 = Normal) 
        # vs Dataset (1 = Attack, 0 = Normal)
        y_pred = [1 if p == -1 else 0 for p in predictions]
        
        print("\n--- 📈 Model Performance Report ---")
        print(classification_report(y_true, y_pred, target_names=['Normal', 'Attack']))

    def analyze(self, df: pd.DataFrame, force_train: bool = False) -> pd.DataFrame:
        is_trained = self.model is not None and hasattr(self.model, "estimators_")
        
        # On passe y_true pour aider au calcul de la contamination
        y_true = df['Label'] if 'Label' in df.columns else None
        
        X = self.preprocess(df, training=(not is_trained or force_train))
        
        if not is_trained or force_train:
            self.train(X, y_true)
        
        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)

        results = df.copy()
        results["anomaly"] = predictions
        results["anomaly_score"] = scores
        results["is_anomaly"] = results["anomaly"] == -1
        
        # Évaluation finale
        if y_true is not None:
            self.evaluate(X, y_true)
            
        return results

if __name__ == "__main__":
    print("NetPulse-Shield — Network Anomaly Detector")
    print("=" * 50)

    data_path = os.path.join("data", "final_project_data.csv")
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        detector = NetworkAnomalyDetector(contamination='auto') 
        results = detector.analyze(df)

        anomalies = results[results["is_anomaly"]]
        print(f"\nTotal records      : {len(results)}")
        print(f"Anomalies detected : {len(anomalies)} ({len(anomalies) / len(results) * 100:.2f} %)")

        top_anomalies = anomalies.sort_values(by='anomaly_score').head(10)
        top_anomalies.to_csv('alerts.csv', index=False)
        print("\n✅ Alerts saved in 'alerts.csv'")
    else:
        print(f"❌ Error: {data_path} not found.")