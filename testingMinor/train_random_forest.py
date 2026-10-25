import pandas as pd
import time
import json
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

DATA_PATH = "data/processed/cicids2017.csv"
MODEL_PATH = "random_forest_cicids2017.pkl"
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
    "Bwd Packets/s"
]


def load_and_prepare_data():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df.columns = df.columns.str.strip()

    df = df[FEATURES + ["Label"]].copy()
    df["Label"] = df["Label"].astype(str).str.strip()
    df["Label"] = (df["Label"] != "BENIGN").astype(int)

    df.replace([float("inf"), float("-inf")], 0, inplace=True)
    df.fillna(0, inplace=True)

    return df[FEATURES], df["Label"]


def train_model():
    X, y = load_and_prepare_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=14,
        min_samples_leaf=10,
        n_jobs=-1,
        random_state=42
    )

    start_time = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_time

    y_pred = model.predict(X_test)

    print("\nRandom Forest Results")
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, digits=4))
    print(f"Training Time: {training_time:.2f} seconds")

    # Save model
    import joblib
    joblib.dump(model, MODEL_PATH)

    # Save feature list
    with open(FEATURES_PATH, "w") as f:
        json.dump(FEATURES, f, indent=2)


if __name__ == "__main__":
    train_model()
