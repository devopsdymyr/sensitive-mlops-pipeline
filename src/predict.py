"""Batch inference using a model from the MLflow Model Registry."""

from __future__ import annotations

import argparse
from pathlib import Path

import mlflow.pyfunc
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "params.yaml"


def default_model_uri() -> str:
    if not PARAMS_PATH.is_file():
        return "models:/IrisClassifier@champion"
    with PARAMS_PATH.open() as f:
        cfg = yaml.safe_load(f)
    mlflow_cfg = cfg.get("mlflow", {})
    name = mlflow_cfg.get("registered_model_name", "IrisClassifier")
    alias = mlflow_cfg.get("model_alias", "champion")
    return f"models:/{name}@{alias}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Load registry model (by alias) and run batch predictions.")
    parser.add_argument(
        "--model-uri",
        default=None,
        help="MLflow model URI. Default: from params.yaml (registry alias, e.g. models:/IrisClassifier@champion).",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="CSV with columns sepal_length,sepal_width,petal_length,petal_width",
    )
    parser.add_argument("--output", type=str, default="predictions.csv")
    args = parser.parse_args()

    model_uri = args.model_uri or default_model_uri()
    model = mlflow.pyfunc.load_model(model_uri)
    df = pd.read_csv(args.input)
    expected = {"sepal_length", "sepal_width", "petal_length", "petal_width"}
    missing = expected - set(df.columns)
    if missing:
        raise SystemExit(f"Input CSV missing columns: {sorted(missing)}")

    feature_cols = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
    # Match training dtype and MLflow signature (infer_signature used float32 from train.py).
    X = df[feature_cols].astype("float32")
    preds = model.predict(X)
    out = df.copy()
    out["prediction"] = preds
    out.to_csv(args.output, index=False)
    print(f"Wrote {args.output} ({len(out)} rows) using {model_uri}")


if __name__ == "__main__":
    main()
