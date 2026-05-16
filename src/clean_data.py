import os
import numpy as np
import pandas as pd


def prepare_final_dataset():
    features_path = "data/NUSW-NB15_features.csv"
    raw_data_path = "data/UNSW-NB15_1.csv"
    output_paths = [
        "data/processed/final_project_data.csv",
        "data/final_project_data.csv",
    ]

    for p in output_paths:
        if os.path.exists(p):
            df = pd.read_csv(p)
            print(f"\n[OK] Cleaned data already exists: {p}")
            print(f"[DATA] {len(df):,} rows, {len(df.columns)} columns")
            print(f"[INFO] Columns: {list(df.columns)}")
            return

    if not os.path.exists(features_path):
        print(f"\n[WARN] Dictionary file not found: {features_path}")
        print("[INFO] Using preprocessed data from data/ directory if available")
        return

    if not os.path.exists(raw_data_path):
        print(f"\n[WARN] Raw dataset file not found: {raw_data_path}")
        print("[INFO] Using preprocessed data from data/ directory if available")
        return

    features_df = pd.read_csv(features_path, encoding="cp1252")
    column_names = features_df["Name"].astype(str).str.strip().str.lower().tolist()
    raw_data = pd.read_csv(raw_data_path, header=None, names=column_names, low_memory=False)
    initial_count = len(raw_data)

    power_features = ["sttl", "sbytes", "dbytes", "sload", "dload", "label"]
    missing_columns = [col for col in power_features if col not in raw_data.columns]
    if missing_columns:
        print("Available columns:", list(raw_data.columns))
        raise KeyError(f"Missing columns: {missing_columns}")

    clean_df = raw_data[power_features].copy()
    for col in power_features:
        clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")
    clean_df = clean_df.drop_duplicates()
    clean_df = clean_df.replace([np.inf, -np.inf], np.nan)
    clean_df = clean_df.dropna()

    if len(clean_df) > 50000:
        final_set = clean_df.sample(n=50000, random_state=42)
    else:
        final_set = clean_df

    os.makedirs("data", exist_ok=True)
    out_path = output_paths[1]
    final_set.to_csv(out_path, index=False)

    print(f"\n[OK] Cleaning complete!")
    print(f"[DATA] {initial_count:,} raw rows -> {len(final_set):,} cleaned rows")
    print(f"[INFO] Saved to: {out_path}")


if __name__ == "__main__":
    prepare_final_dataset()
