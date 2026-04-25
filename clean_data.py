import pandas as pd

# 1. LOAD THE DICTIONARY
# This file contains the names of the 49 columns
features_df = pd.read_csv('data/NUSW-NB15_features.csv', encoding='cp1252')
# Clean the names (remove spaces) so they are easy to use in code
column_names = features_df['Name'].str.strip().tolist()

# 2. LOAD THE RAW DATA
# We tell pandas there is no header in the file and to use our list instead
raw_data = pd.read_csv('data/UNSW-NB15_1.csv', header=None, names=column_names, low_memory=False)

# 3. SELECT THE "POWER" FEATURES
# These are the ones that actually reveal hacker behavior
# Updated list with correct capitalization
power_features = [
    'sttl', 
    'sbytes', 
    'dbytes', 
    'Sload',  # Changed to Capital S
    'Dload',  # Changed to Capital D
    'Label'
]

# Create the clean version
clean_df = raw_data[power_features].copy()

# 4. DOWNSAMPLE & SAVE
# We take 50,000 random rows so the file is small (around 2-3 MB)
final_set = clean_df.sample(n=50000, random_state=42)
final_set.to_csv('data/final_project_data.csv', index=False)

print("Success! Created 'final_project_data.csv' in your data folder.")
print("You can now Push this file to GitHub for your friends!")