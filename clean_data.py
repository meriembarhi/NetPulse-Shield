import pandas as pd
import numpy as np
import os

"""
NetPulse-Shield: Data preprocessing script
Dataset: UNSW-NB15 (full raw set)
Source: https://research.unsw.edu.au/projects/unsw-nb15-dataset
Description: Prepares the dataset for Isolation Forest and downstream remediation.
"""

def prepare_final_dataset():
    # 1. Load the column-name dictionary
    try:
        features_df = pd.read_csv('data/NUSW-NB15_features.csv', encoding='cp1252')
        column_names = features_df['Name'].str.strip().tolist()
    except FileNotFoundError:
        print("❌ Error: 'NUSW-NB15_features.csv' was not found in /data.")
        return
    except Exception as e:
        print(f"❌ Error loading column names: {e}")
        return

    # 2. Load raw data
    # low_memory=False helps with mixed data types in the original dataset
    input_file = 'data/UNSW-NB15_1.csv'
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} was not found.")
        return

    print("⏳ Loading raw data...")
    try:
        raw_data = pd.read_csv(input_file, header=None, names=column_names, low_memory=False)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    initial_count = len(raw_data)
    
    if initial_count == 0:
        print("❌ Error: the source file is empty.")
        return

    # 3. Select the key features and clean the data
    power_features = ['sttl', 'sbytes', 'dbytes', 'Sload', 'Dload', 'Label']
    
    # Check that the required columns are present
    missing_cols = [col for col in power_features if col not in raw_data.columns]
    if missing_cols:
        print(f"❌ Error: missing columns: {missing_cols}")
        print(f"   Available columns: {raw_data.columns.tolist()}")
        return
    
    # Build the filtered dataframe
    clean_df = raw_data[power_features].copy()

    # --- Critical cleaning steps ---
    # Drop duplicates to reduce bias
    clean_df = clean_df.drop_duplicates()
    
    # Replace infinite values (common in Sload/Dload) with NaN, then drop them
    clean_df = clean_df.replace([np.inf, -np.inf], np.nan).dropna()
    # -------------------------------------
    
    if len(clean_df) == 0:
        print("❌ Error: no valid data remains after cleaning.")
        return

    # 4. Sample and save
    # Keep up to 50,000 rows to keep the Streamlit dashboard responsive
    if len(clean_df) > 50000:
        final_set = clean_df.sample(n=50000, random_state=42)
    else:
        final_set = clean_df

    output_path = 'data/final_project_data.csv'
    try:
        final_set.to_csv(output_path, index=False)
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return

    # 5. Technical summary
    print("\n✅ Cleaning completed successfully!")
    print(f"📊 Summary: {initial_count} raw rows -> {len(final_set)} filtered rows.")
    print(f"💾 File ready for the pipeline: {output_path}")

if __name__ == "__main__":
    prepare_final_dataset()