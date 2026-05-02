import pandas as pd
import numpy as np
import os

"""
NetPulse-Shield: Data Pre-processing Script
Dataset: UNSW-NB15 (Full Raw Set)
Source: https://research.unsw.edu.au/projects/unsw-nb15-dataset
Description: Nettoyage et préparation du dataset pour l'Isolation Forest et Llama 3.
"""

def prepare_final_dataset():
    # 1. CHARGEMENT DU DICTIONNAIRE DE COLONNES
    try:
        features_df = pd.read_csv('data/NUSW-NB15_features.csv', encoding='cp1252')
        column_names = features_df['Name'].str.strip().tolist()
    except FileNotFoundError:
        print("❌ Erreur : Fichier 'NUSW-NB15_features.csv' introuvable dans /data.")
        return
    except Exception as e:
        print(f"❌ Erreur lors du chargement des noms de colonnes : {e}")
        return

    # 2. CHARGEMENT DES DONNÉES BRUTES
    # On utilise low_memory=False pour gérer les types de données mixtes dans le dataset original
    input_file = 'data/UNSW-NB15_1.csv'
    if not os.path.exists(input_file):
        print(f"❌ Erreur : Le fichier {input_file} est introuvable.")
        return

    print("⏳ Chargement des données brutes...")
    try:
        raw_data = pd.read_csv(input_file, header=None, names=column_names, low_memory=False)
    except Exception as e:
        print(f"❌ Erreur lors du chargement des données : {e}")
        return
    
    initial_count = len(raw_data)
    
    if initial_count == 0:
        print("❌ Erreur : Le fichier source est vide.")
        return

    # 3. SÉLECTION DES "POWER FEATURES" & NETTOYAGE
    power_features = ['sttl', 'sbytes', 'dbytes', 'Sload', 'Dload', 'Label']
    
    # Vérification de la présence des colonnes requises
    missing_cols = [col for col in power_features if col not in raw_data.columns]
    if missing_cols:
        print(f"❌ Erreur : Colonnes manquantes : {missing_cols}")
        print(f"   Colonnes disponibles : {raw_data.columns.tolist()}")
        return
    
    # Création du DataFrame filtré
    clean_df = raw_data[power_features].copy()

    # --- ÉTAPES DE NETTOYAGE CRITIQUES ---
    # Suppression des doublons pour éviter les biais
    clean_df = clean_df.drop_duplicates()
    
    # Remplacement des valeurs infinies (fréquentes dans Sload/Dload) par NaN, puis suppression
    clean_df = clean_df.replace([np.inf, -np.inf], np.nan).dropna()
    # -------------------------------------
    
    if len(clean_df) == 0:
        print("❌ Erreur : Aucune donnée valide restante après nettoyage.")
        return

    # 4. ÉCHANTILLONNAGE & SAUVEGARDE
    # On prend 50 000 lignes pour garantir la fluidité du Dashboard Streamlit
    if len(clean_df) > 50000:
        final_set = clean_df.sample(n=50000, random_state=42)
    else:
        final_set = clean_df

    output_path = 'data/final_project_data.csv'
    try:
        final_set.to_csv(output_path, index=False)
    except Exception as e:
        print(f"❌ Erreur lors de l'écriture du fichier : {e}")
        return

    # 5. RÉSUMÉ TECHNIQUE
    print("\n✅ Nettoyage terminé avec succès !")
    print(f"📊 Résumé : {initial_count} lignes brutes ➔ {len(final_set)} lignes filtrées.")
    print(f"💾 Fichier prêt pour l'IA : {output_path}")

if __name__ == "__main__":
    prepare_final_dataset()