import os
import pandas as pd
import numpy as np
from sklearn.metrics import precision_recall_curve

import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    roc_curve,
)

PRED_PATH = os.path.join(".", "predictions.csv")
FIG_DIR = os.path.join(".", "figures")
METRICS_OUT = os.path.join(".", "metrics_table.csv")

THRESHOLD = 0.5  # for confusion matrix & classification metrics


MODEL_SCORES = {
    "DecisionTree": "dt_score",
    "RandomForest": "rf_score",
    "LightGBM": "lgbm_score",
    "XGBoost": "xgb_score",
}


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def compute_metrics(y_true, scores, threshold=0.5):
    y_pred = (scores >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, scores),
        "pr_auc": average_precision_score(y_true, scores),
        "tn": confusion_matrix(y_true, y_pred)[0, 0],
        "fp": confusion_matrix(y_true, y_pred)[0, 1],
        "fn": confusion_matrix(y_true, y_pred)[1, 0],
        "tp": confusion_matrix(y_true, y_pred)[1, 1],
    }


def plot_confusion_heatmap(cm, title, out_path):
    # Simple heatmap without seaborn (works everywhere)
    plt.figure()
    plt.imshow(cm, interpolation="nearest")
    plt.title(title)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.xticks([0, 1], ["0", "1"])
    plt.yticks([0, 1], ["0", "1"])

    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center")

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def main():
    ensure_dir(FIG_DIR)

    if not os.path.exists(PRED_PATH):
        raise FileNotFoundError(
            f"Missing {PRED_PATH}. Run collect_predictions.py first."
        )

    df = pd.read_csv(PRED_PATH)
    y_true = df["y_true"].astype(int).values

    metrics_rows = []

    # --- Per-model metrics + confusion heatmap ---
    for model_name, col in MODEL_SCORES.items():
        scores = df[col].astype(float).values
        m = compute_metrics(y_true, scores, threshold=THRESHOLD)
        m["model"] = model_name
        m["threshold"] = THRESHOLD
        metrics_rows.append(m)

        y_pred = (scores >= THRESHOLD).astype(int)
        cm = confusion_matrix(y_true, y_pred)
        heatmap_path = os.path.join(FIG_DIR, f"confusion_{model_name}.png")
        plot_confusion_heatmap(cm, f"Confusion Matrix - {model_name}", heatmap_path)

    metrics_df = pd.DataFrame(metrics_rows).set_index("model")
    metrics_df.to_csv(METRICS_OUT)

    print("[✓] Saved metrics table:", METRICS_OUT)
    print(metrics_df[["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]])

    # --- Graph 1: Bar chart compare F1 and ROC-AUC ---
    plt.figure()
    metrics_df[["f1", "roc_auc"]].plot(kind="bar")
    plt.title("Model Comparison: F1 vs ROC-AUC")
    plt.xlabel("Model")
    plt.ylabel("Score")
    plt.tight_layout()
    out1 = os.path.join(FIG_DIR, "compare_f1_rocauc.png")
    plt.savefig(out1, dpi=200)
    plt.close()

    # --- Graph 2: ROC curves for all models ---
    # --- Graph 2: ROC curves for all models (ZOOMED) ---
    plt.figure()
    for model_name, col in MODEL_SCORES.items():
        scores = df[col].astype(float).values
        fpr, tpr, _ = roc_curve(y_true, scores)
        plt.plot(fpr, tpr, label=model_name)

    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.title("ROC Curves (Zoomed: FPR 0-0.05)")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.xlim(0.0, 0.05)
    plt.ylim(0.90, 1.0)   # you can tweak to 0.95 if still tight
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "roc_curves_zoomed.png"), dpi=200)
    plt.close()


    plt.figure()
    for model_name, col in MODEL_SCORES.items():
        scores = df[col].astype(float).values
        precision, recall, _ = precision_recall_curve(y_true, scores)
        plt.plot(recall, precision, label=model_name)

    plt.title("Precision–Recall Curves (All Models)")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "pr_curves_all_models.png"), dpi=200)
    plt.close()



    # --- Graph 4: Threshold metrics (Precision/Recall/F1 + FP) ---
    plt.figure()
    metrics_df[["precision", "recall", "f1"]].plot(kind="bar")
    plt.title(f"Threshold Metrics @ {THRESHOLD}")
    plt.xlabel("Model")
    plt.ylabel("Score")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "threshold_metrics.png"), dpi=200)
    plt.close()

    plt.figure()
    metrics_df[["fp"]].plot(kind="bar")
    plt.title(f"False Positives @ {THRESHOLD}")
    plt.xlabel("Model")
    plt.ylabel("FP Count")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "false_positives.png"), dpi=200)
    plt.close()




    print("[✓] Saved figures in:", FIG_DIR)
    print("    - confusion_*.png (4 files)")
    print("    - compare_f1_rocauc.png")
    print("    - roc_curves_all_models.png")


if __name__ == "__main__":
    main()
