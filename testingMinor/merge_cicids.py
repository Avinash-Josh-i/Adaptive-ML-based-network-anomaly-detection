# import pandas as pd
# from pathlib import Path

# raw_dir = Path("data/raw")
# processed_dir = Path("data/processed")
# processed_dir.mkdir(exist_ok=True)

# # Merge all CSVs
# files = list(raw_dir.glob("*.csv"))
# dfs = [pd.read_csv(f) for f in files]
# df = pd.concat(dfs, ignore_index=True)

# # Save merged CSV
# merged_csv_path = processed_dir / "cicids2017.csv"
# df.to_csv(merged_csv_path, index=False)
# print(f"Merged dataset saved to {merged_csv_path}")

# --------------------

import os
import pandas as pd

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
OUTPUT_FILE = os.path.join(PROCESSED_DIR, "cicids2017.csv")

def merge_csv_files():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    all_dfs = []
    for file in os.listdir(RAW_DIR):
        if file.endswith(".csv"):
            file_path = os.path.join(RAW_DIR, file)
            print(f"Reading: {file_path}")
            df = pd.read_csv(file_path, low_memory=False)
            all_dfs.append(df)

    merged_df = pd.concat(all_dfs, ignore_index=True)
    merged_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nMerged file saved to: {OUTPUT_FILE}")
    print(f"Total rows: {merged_df.shape[0]}")
    print(f"Total columns: {merged_df.shape[1]}")

if __name__ == "__main__":
    merge_csv_files()
