import os
import time
import json
import sys
import pandas as pd
import numpy as np
import joblib

MODEL_PATH = "lightgbm_cicids2017.pkl"
INPUT_CSV = r"..\adaptive_ml_based_network_anamoly_detection\feature_extract\bin\flows.csv"    
OUTPUT_CSV = "prediction_output.csv"
FEATURES_PATH = "model_features.json"

# --- Adaptive threshold config ---
PERCENTILE = 95
MIN_SAMPLES_FOR_ADAPTIVE = 50
FALLBACK_THRESHOLD = 0.7

# --- Watcher config ---
POLL_INTERVAL_SEC = 1.0          # how often to check file changes
READ_RETRIES = 5                 # handle partial writes
READ_RETRY_SLEEP = 0.2           # seconds
MIN_ROWS_TO_PREDICT = 1          # skip if empty


def load_model():
    return joblib.load(MODEL_PATH)


def load_features():
    """
    Loads the exact feature order used during training.
    Falls back to hardcoded list if the file is missing.
    """
    try:
        feats = joblib.load(FEATURES_PATH)
        if isinstance(feats, list) and len(feats) > 0:
            return feats
    except Exception:
        pass

    try:
        with open(FEATURES_PATH, "r", encoding="utf-8") as f:
            feats = json.load(f)
        if isinstance(feats, list) and len(feats) > 0:
            return feats
    except Exception:
        pass

    return [
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


def choose_adaptive_threshold(scores: np.ndarray) -> float:
    n = len(scores)
    if n < MIN_SAMPLES_FOR_ADAPTIVE:
        return FALLBACK_THRESHOLD
    thr = float(np.percentile(scores, PERCENTILE))
    return max(0.0, min(1.0, thr))


def prepare_input_data(df: pd.DataFrame, FEATURES):
    df.columns = df.columns.str.strip()

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

    if "DurationMs" not in df.columns:
        raise ValueError("Required column 'DurationMs' not found in captured data")

    df["Flow Duration"] = df["DurationMs"] * 1000  # ms -> us

    
    df_out = df.copy()

    df.drop(
        columns=[
            "FlowID", "SrcIP", "DstIP",
            "SrcPort", "DstPort",
            "Protocol", "Label",
            "DurationMs"
        ],
        errors="ignore",
        inplace=True
    )

    missing = set(FEATURES) - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required features for prediction: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)

    X = df[FEATURES].copy()
    return X, df_out


def safe_read_csv(path: str) -> pd.DataFrame:
    """
    Read CSV with retries to handle partial writes while capture app overwrites the file.
    """
    last_err = None
    for _ in range(READ_RETRIES):
        try:
            # If file is being rewritten, size may be 0 momentarily
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            if os.path.getsize(path) == 0:
                raise ValueError("File is empty (maybe being rewritten).")

            df = pd.read_csv(path, low_memory=False)
            return df
        except Exception as e:
            last_err = e
            time.sleep(READ_RETRY_SLEEP)
    raise last_err


def predict_once(model, FEATURES):
    df_raw = safe_read_csv(INPUT_CSV)

    # If only header exists / no rows
    if df_raw.shape[0] < MIN_ROWS_TO_PREDICT:
        return None, None, None

    X, df_out = prepare_input_data(df_raw, FEATURES)

    scores = model.predict_proba(X)[:, 1]
    threshold = choose_adaptive_threshold(scores)
    preds = (scores >= threshold).astype(int)

    df_out["AnomalyScore"] = scores
    df_out["ThresholdUsed"] = threshold
    df_out["Anomaly"] = preds

    # overwrite output each cycle
    df_out.to_csv(OUTPUT_CSV, index=False)

    return threshold, preds, df_out


def watch_and_predict():
    print("[*] Loading model + features...")
    FEATURES = load_features()
    model = load_model()
    print("[✓] Ready. Watching flows.csv. Press Ctrl+C to stop.\n")

    last_sig = None  # (mtime_ns, size)

    while True:
        try:
            if not os.path.exists(INPUT_CSV):
                time.sleep(POLL_INTERVAL_SEC)
                continue

            stat = os.stat(INPUT_CSV)
            sig = (stat.st_mtime_ns, stat.st_size)

            if sig != last_sig:
                last_sig = sig

                threshold, preds, df_out = predict_once(model, FEATURES)

                if threshold is None:
                    # file exists but no rows yet
                    print("[~] flows.csv updated but empty/no rows. Waiting...")
                else:
                    total = len(preds)
                    anom = int(np.sum(preds))
                    benign = total - anom
                    print(
                        f"[✓] Updated: {total} flows | "
                        f"Anomaly={anom}, Benign={benign} | "
                        f"Thr={threshold:.6f} | "
                        f"Saved -> {OUTPUT_CSV}"
                    )

            time.sleep(POLL_INTERVAL_SEC)

        except KeyboardInterrupt:
            print("\n[!] Stopped by user (Ctrl+C).")
            return
        except Exception as e:
            # keep running even if one cycle fails
            print(f"[ERROR] {e}")
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    watch_and_predict()
