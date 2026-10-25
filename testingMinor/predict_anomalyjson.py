import pandas as pd
import xgboost as xgb
import numpy as np
import sys

MODEL_PATH = "xgboost_cicids2017.json"
INPUT_CSV = "data/captured_flows.csv"      # change if needed
OUTPUT_CSV = "prediction_output.csv"

# 🔒 Feature order MUST match training exactly
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

# --- Adaptive threshold config ---
# Example: 95th percentile => top 5% most anomalous flows flagged
PERCENTILE = 95

# Safety rails to avoid weird behavior with tiny batches
MIN_SAMPLES_FOR_ADAPTIVE = 50
FALLBACK_THRESHOLD = 0.7  # used if not enough rows


def load_model():
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    return model


def prepare_input_data(df: pd.DataFrame):
    """
    Converts captured flow data into model-ready format.
    Handles column-name differences, unit normalization, dropping IDs, and fixes feature order.
    """

    # Normalize column names
    df.columns = df.columns.str.strip()

    # --- Map your captured column names to CICIDS-style names (if needed) ---
    # Your captured schema: FwdPackets, BwdPackets, FwdBytes, BwdBytes, etc.
    # CICIDS expects: Total Fwd Packets, Total Backward Packets, Total Length of Fwd Packets, Total Length of Bwd Packets
    rename_map = {
        "FwdPackets": "Total Fwd Packets",
        "BwdPackets": "Total Backward Packets",
        "FwdBytes": "Total Length of Fwd Packets",
        "BwdBytes": "Total Length of Bwd Packets",

        "MinPktLen": "Min Packet Length",
        "MaxPktLen": "Max Packet Length",
        "MeanPktLen": "Packet Length Mean",
        "StdPktLen": "Packet Length Std",

        "FlowIATMeanUs": "Flow IAT Mean",
        "FlowIATStdUs": "Flow IAT Std",

        "PacketsPerSec": "Flow Packets/s",
        "BytesPerSec": "Flow Bytes/s",

        "FwdPps": "Fwd Packets/s",
        "BwdPps": "Bwd Packets/s",
    }
    df.rename(columns=rename_map, inplace=True)

    # ---- UNIT NORMALIZATION ----
    # Captured data uses milliseconds; CICIDS uses microseconds
    # Your captured column is DurationMs
    if "DurationMs" not in df.columns:
        raise ValueError("Required column 'DurationMs' not found in captured data")
    df["Flow Duration"] = df["DurationMs"] * 1000

    # ---- DROP IDENTIFIERS (never feed model) ----
    df.drop(
        columns=[
            "FlowID", "SrcIP", "DstIP",
            "SrcPort", "DstPort",
            "Protocol", "Label",  # Label is ground truth (if present) - not used in live detection
            "DurationMs"          # remove raw after conversion
        ],
        errors="ignore",
        inplace=True
    )

    # ---- DEFENSIVE FEATURE CHECK ----
    missing = set(FEATURES) - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required features for prediction: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    # Handle NaN / inf
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)

    # ---- FIX FEATURE ORDER ----
    X = df[FEATURES].copy()

    return X, df


def choose_adaptive_threshold(scores: np.ndarray) -> float:
    """
    Adaptive percentile-based threshold.
    If batch too small, uses a fallback fixed threshold.
    """
    n = len(scores)
    if n < MIN_SAMPLES_FOR_ADAPTIVE:
        return FALLBACK_THRESHOLD

    # Percentile threshold (distribution-free)
    thr = float(np.percentile(scores, PERCENTILE))

    # Small guard: keep within [0,1]
    thr = max(0.0, min(1.0, thr))
    return thr


def main():
    print("[*] Loading captured flows...")
    try:
        df_raw = pd.read_csv(INPUT_CSV, low_memory=False)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {INPUT_CSV}")
        sys.exit(1)

    print("[*] Preparing input features...")
    X, df_clean = prepare_input_data(df_raw)

    print("[*] Loading trained model...")
    model = load_model()

    print("[*] Scoring flows...")
    scores = model.predict_proba(X)[:, 1]

    # --- Adaptive thresholding (this is the key change) ---
    threshold = choose_adaptive_threshold(scores)
    predictions = (scores >= threshold).astype(int)

    # Attach results
    df_clean["AnomalyScore"] = scores
    df_clean["ThresholdUsed"] = threshold
    df_clean["Anomaly"] = predictions

    # Save output
    df_clean.to_csv(OUTPUT_CSV, index=False)

    print(f"[✓] Prediction completed")
    print(f"[✓] Output saved to: {OUTPUT_CSV}")

    print(f"\nAdaptive threshold used: {threshold:.6f}")
    print("\nAnomaly count:")
    print(pd.Series(predictions).value_counts())


if __name__ == "__main__":
    main()
