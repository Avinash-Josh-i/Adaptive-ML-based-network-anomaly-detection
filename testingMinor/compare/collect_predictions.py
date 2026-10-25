import os
import json
import joblib
import pandas as pd
import numpy as np

# XGBoost
import xgboost as xgb

# --- Fixed test set produced by prepare_test_set.py ---
TEST_SET_PATH = os.path.join(".", "test_set.csv")
PRED_OUT = os.path.join(".", "predictions.csv")

# --- Models (your current names in root) ---
DT_MODEL = os.path.join("..", "decision_tree_cicids2017.pkl")
RF_MODEL = os.path.join("..", "random_forest_cicids2017.pkl")
LGBM_MODEL = os.path.join("..", "lightgbm_cicids2017.pkl")
XGB_MODEL = os.path.join("..", "xgboost_cicids2017.json")

FEATURES_PATH = os.path.join("..", "model_features.json")

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


def load_features():
    if os.path.exists(FEATURES_PATH):
        with open(FEATURES_PATH, "r", encoding="utf-8") as f:
            feats = json.load(f)
        if isinstance(feats, list) and len(feats) > 0:
            return feats
    return FALLBACK_FEATURES


def predict_sklearn_proba(model, X: pd.DataFrame) -> np.ndarray:
    # Works for DT/RF/LGBM sklearn-style models
    proba = model.predict_proba(X)
    return proba[:, 1]


def predict_xgboost_proba(model_path: str, X: pd.DataFrame) -> np.ndarray:
    booster = xgb.Booster()
    booster.load_model(model_path)
    dmat = xgb.DMatrix(X.values, feature_names=list(X.columns))
    # For binary:logistic this returns probability
    pred = booster.predict(dmat)
    return pred.astype(float)


def main():
    if not os.path.exists(TEST_SET_PATH):
        raise FileNotFoundError(
            f"Missing {TEST_SET_PATH}. Run prepare_test_set.py first."
        )

    FEATURES = load_features()

    print("[*] Loading test set:", TEST_SET_PATH)
    df = pd.read_csv(TEST_SET_PATH, low_memory=False)
    df.columns = df.columns.astype(str).str.strip()

    missing = set(FEATURES + ["Label"]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in test_set.csv: {missing}")

    X = df[FEATURES].copy()
    y_true = df["Label"].astype(int).values

    # Clean numeric
    X.replace([np.inf, -np.inf], 0, inplace=True)
    X.fillna(0, inplace=True)

    out = pd.DataFrame({"y_true": y_true})

    # Decision Tree
    print("[*] Loading Decision Tree:", DT_MODEL)
    dt = joblib.load(DT_MODEL)
    out["dt_score"] = predict_sklearn_proba(dt, X)

    # Random Forest
    print("[*] Loading Random Forest:", RF_MODEL)
    rf = joblib.load(RF_MODEL)
    out["rf_score"] = predict_sklearn_proba(rf, X)

    # LightGBM (sklearn API saved via joblib)
    print("[*] Loading LightGBM:", LGBM_MODEL)
    lgbm = joblib.load(LGBM_MODEL)
    out["lgbm_score"] = predict_sklearn_proba(lgbm, X)

    # XGBoost (json booster)
    print("[*] Loading XGBoost:", XGB_MODEL)
    out["xgb_score"] = predict_xgboost_proba(XGB_MODEL, X)

    out.to_csv(PRED_OUT, index=False)
    print(f"[✓] Saved predictions: {PRED_OUT}")
    print(out.head())


if __name__ == "__main__":
    main()
