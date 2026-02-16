"""
ShelfWatch — YOLO11 Training Script

Trains a YOLO11 model on the SKU-110K shelf dataset and logs
metrics to MLflow.

Usage:
    python training/train.py

Prerequisites:
    - Dataset downloaded via `python dataset/download.py`
    - MLflow server running (optional, defaults to local ./mlruns)
"""

import os
import mlflow
from ultralytics import YOLO


# ──────────────────────────────────────────────
# Config — adjust these as needed
# ──────────────────────────────────────────────
MODEL_VARIANT = os.environ.get("YOLO_MODEL", "yolo11l.pt")  # H100 → go large
DATA_YAML = os.environ.get("DATA_YAML", "dataset/data.yaml")
EPOCHS = int(os.environ.get("EPOCHS", "50"))
IMG_SIZE = int(os.environ.get("IMG_SIZE", "640"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "32"))        # H100 can handle 32+
PROJECT = "runs/shelf"
NAME = "baseline"


def train():
    """Run training and log results to MLflow."""

    mlflow.set_experiment("shelfwatch-training")

    with mlflow.start_run(run_name=f"{MODEL_VARIANT}-ep{EPOCHS}"):
        # Log hyperparams
        mlflow.log_params({
            "model_variant": MODEL_VARIANT,
            "epochs": EPOCHS,
            "img_size": IMG_SIZE,
            "batch_size": BATCH_SIZE,
            "data_yaml": DATA_YAML,
        })

        # Train
        model = YOLO(MODEL_VARIANT)
        results = model.train(
            data=DATA_YAML,
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH_SIZE,
            project=PROJECT,
            name=NAME,
            exist_ok=True,
            verbose=True,
        )

        # Log metrics
        metrics = {
            "mAP50": results.results_dict.get("metrics/mAP50(B)", 0),
            "mAP50-95": results.results_dict.get("metrics/mAP50-95(B)", 0),
            "precision": results.results_dict.get("metrics/precision(B)", 0),
            "recall": results.results_dict.get("metrics/recall(B)", 0),
        }
        mlflow.log_metrics(metrics)

        # Log best weights as artifact
        best_weights = os.path.join(PROJECT, NAME, "weights", "best.pt")
        if os.path.exists(best_weights):
            mlflow.log_artifact(best_weights, artifact_path="weights")
            print(f"✅ best.pt logged to MLflow: {best_weights}")

        print(f"✅ Training complete — metrics: {metrics}")

    return results


if __name__ == "__main__":
    train()
