"""
detector.py - Network Anomaly Detector for NetPulse-Shield
Version optimisée : Persistance du modèle & Flexibilité
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class NetworkAnomalyDetector:
    """Détecteur d'anomalies basé sur Isolation Forest avec sauvegarde automatique."""

    def __init__(self, contamination=0.1, n_estimators=100, model_path="models/netpulse_model.joblib"):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model_path = model_path
        self.scaler_path = model_path.replace(".joblib", "_scaler.joblib")
        
        # Création du dossier models s'il n'existe pas
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        self.feature_columns = None
        
        # Tentative de chargement d'un modèle existant
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            print(f"✅ Modèle et Scaler chargés depuis {self.model_path}")
        else:
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42,
            )
            self.scaler = StandardScaler()
            print("🆕 Aucun modèle trouvé. Nouveau détecteur initialisé.")

    def preprocess(self, df: pd.DataFrame, feature_columns: list | None = None, training: bool = False) -> np.ndarray:
        if feature_columns is not None:
            self.feature_columns = feature_columns
        else:
            cols_to_exclude = ['label', 'anomaly', 'is_anomaly', 'anomaly_score']
            self.feature_columns = [c for c in df.select_dtypes(include=[np.number]).columns 
                                   if c not in cols_to_exclude]

        features = df[self.feature_columns].fillna(0)
        
        if training:
            return self.scaler.fit_transform(features)
        else:
            return self.scaler.transform(features)

    def train(self, X: np.ndarray) -> None:
        """Entraîne le modèle et le sauvegarde sur le disque."""
        print(f"🧠 Entraînement de l'Isolation Forest (contamination={self.contamination})...")
        self.model.fit(X)
        
        # Sauvegarde du modèle et du scaler
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        print(f"💾 Modèle sauvegardé avec succès dans : {self.model_path}")

    def detect(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)
        return predictions, scores

    def analyze(self, df: pd.DataFrame, force_train: bool = False) -> pd.DataFrame:
        """Exécute la pipeline complète. Entraîne seulement si nécessaire ou forcé."""
        # Si le modèle n'a jamais été entraîné ou si on force l'entraînement
        is_trained = hasattr(self.model, "estimators_")
        
        X = self.preprocess(df, training=(not is_trained or force_train))
        
        if not is_trained or force_train:
            self.train(X)
        
        predictions, scores = self.detect(X)

        results = df.copy()
        results["anomaly"] = predictions
        results["anomaly_score"] = scores
        results["is_anomaly"] = results["anomaly"] == -1
        return results

# --- Point d'entrée principal ---

if __name__ == "__main__":
    print("NetPulse-Shield — Network Anomaly Detector")
    print("=" * 50)

    data_path = os.path.join("data", "final_project_data.csv")

    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        print(f"Erreur : {data_path} non trouvé.")
        exit()

    # On peut maintenant changer la contamination facilement ici
    detector = NetworkAnomalyDetector(contamination=0.05) 
    
    # L'analyse va charger le modèle s'il existe, sinon il va l'entraîner
    results = detector.analyze(df)

    anomalies = results[results["is_anomaly"]]

    print(f"\nTotal enregistrements : {len(results)}")
    print(f"Anomalies détectées    : {len(anomalies)} ({len(anomalies) / len(results) * 100:.1f} %)")

    # Sauvegarde des alertes pour le module solver/remediator
    top_anomalies = anomalies.sort_values(by='anomaly_score').head(10)
    top_anomalies.to_csv('alerts.csv', index=False)
    
    print("\n✅ Détection terminée. Alertes sauvegardées dans 'alerts.csv'")