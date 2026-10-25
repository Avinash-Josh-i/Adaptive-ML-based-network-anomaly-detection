import os
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# --- Input dataset (base) ---
DATA_PATH = os.path.join("..", "data", "processed", "cicids2017.csv")

# --- Output fixed split files ---
OUT_DIR = "."
TRAIN_OUT = os.path.join(OUT_DIR, "train_set.csv")
TEST_OUT = os.path.join(OUT_DIR, "test_set.csv")

# --- Feature contract ---
FEATURES_PATH = os.path.join("..", "model_features.json")  # same file used by predict_anomaly

# If FEATURES_PATH missing, fallback here (must match your training scripts)
FALLBACK_FEATURES = [
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Min Packet Length",
    "Max Packet Length",
    "Packet Length Mean",
    "Packet Length Std",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Flow IAT Mean",
    "Flow IAT Std",
    "Fwd Packets/s",
    "Bwd Packets/s",
]

RANDOM_STATE = 42
TEST_SIZE = 0.20  # 80/20 split


def load_features():
    if os.path.exists(FEATURES_PATH):
        with open(FEATURES_PATH, "r", encoding="utf-8") as f:
            feats = json.load(f)
        if isinstance(feats, list) and len(feats) > 0:
            return feats
    return FALLBACK_FEATURES


def main():
    print("[*] Loading dataset:", DATA_PATH)
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df.columns = df.columns.astype(str).str.strip()

    FEATURES = load_features()

    # Keep only required columns
    missing = set(FEATURES + ["Label"]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing}")

    df = df[FEATURES + ["Label"]].copy()

    # Binary label: BENIGN => 0, others => 1
    df["Label"] = df["Label"].astype(str).str.strip()
    df["Label"] = (df["Label"] != "BENIGN").astype(int)

    # Clean
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)

    X = df[FEATURES]
    y = df["Label"]

    print("[*] Creating fixed train/test split...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )

    train_df = X_train.copy()
    train_df["Label"] = y_train.values

    test_df = X_test.copy()
    test_df["Label"] = y_test.values

    train_df.to_csv(TRAIN_OUT, index=False)
    test_df.to_csv(TEST_OUT, index=False)

    print(f"[✓] Saved: {TRAIN_OUT}  rows={len(train_df):,}")
    print(f"[✓] Saved: {TEST_OUT}   rows={len(test_df):,}")
    print("\nTest set class distribution:")
    print(test_df["Label"].value_counts())


if __name__ == "__main__":
    main()
