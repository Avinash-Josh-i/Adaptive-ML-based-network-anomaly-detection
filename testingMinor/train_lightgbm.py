import pandas as pd
import time
import json
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from lightgbm import LGBMClassifier

DATA_PATH = "data/processed/cicids2017.csv"
MODEL_PATH = "lightgbm_cicids2017.pkl"
FEATURES_PATH = "model_features.json"

FEATURES = [
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


def load_and_prepare_data():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df.columns = df.columns.str.strip()

    # keep only required columns + label
    df = df[FEATURES + ["Label"]].copy()

    # robust label parsing
    df["Label"] = df["Label"].astype(str).str.strip()
    df["Label"] = (df["Label"] != "BENIGN").astype(int)

    # handle inf/nan
    df.replace([float("inf"), float("-inf")], 0, inplace=True)
    df.fillna(0, inplace=True)

    X = df[FEATURES]
    y = df["Label"]
    return X, y


def train_model():
    X, y = load_and_prepare_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = LGBMClassifier(
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        objective="binary",
    )

    start_time = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_time

    y_pred = model.predict(X_test)

    print("\nLightGBM Results")
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, digits=4))

    print(f"Training Time: {training_time:.2f} seconds")

    # save model
    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")

    # save feature list (same as other scripts)
    with open(FEATURES_PATH, "w", encoding="utf-8") as f:
        json.dump(FEATURES, f, indent=2)
    print(f"Feature list saved to: {FEATURES_PATH}")


if __name__ == "__main__":
    train_model()
