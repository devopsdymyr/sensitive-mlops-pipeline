"""Batch scoring: ML risk label + PII-derived risk_score + compliance tag (all PII logic in pii_detector)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mlflow.sklearn
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "params.yaml"
CLASSES_PATH = ROOT / "models" / "risk_label_classes.json"

sys.path.insert(0, str(ROOT / "src"))
from pii_detector import (  # noqa: E402
    FEATURE_COLUMNS,
    analyze_text,
    compliance_tag_for_risk_label,
    featurize_dataframe,
)


def default_model_uri() -> str:
    if not PARAMS_PATH.is_file():
        return "models:/SensitiveDataRiskClassifier@champion"
    with PARAMS_PATH.open() as f:
        cfg = yaml.safe_load(f)
    mlflow_cfg = cfg.get("mlflow", {})
    name = mlflow_cfg.get("registered_model_name", "SensitiveDataRiskClassifier")
    alias = mlflow_cfg.get("model_alias", "champion")
    return f"models:/{name}@{alias}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Score CSV rows with column raw_text.")
    parser.add_argument("--model-uri", default=None)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="predictions.csv")
    args = parser.parse_args()

    if not CLASSES_PATH.is_file():
        raise SystemExit(
            f"Missing {CLASSES_PATH}. Run training once so label order is saved next to the project."
        )
    with CLASSES_PATH.open() as f:
        classes = json.load(f)["classes"]

    model_uri = args.model_uri or default_model_uri()
    model = mlflow.sklearn.load_model(model_uri)

    df = pd.read_csv(args.input)
    if "raw_text" not in df.columns:
        raise SystemExit("Input CSV must include a 'raw_text' column.")

    feat_df = featurize_dataframe(df, text_col="raw_text")
    X = feat_df[FEATURE_COLUMNS].astype("float32")

    pred_idx = model.predict(X).astype(int)
    labels = [classes[i] for i in pred_idx]

    risk_scores = [analyze_text(t, include_matches=False)["risk_score"] for t in df["raw_text"]]

    out = df.copy()
    out["predicted_risk_label"] = labels
    out["risk_score"] = risk_scores
    out["compliance_tag"] = [compliance_tag_for_risk_label(lb) for lb in labels]
    out.to_csv(args.output, index=False)
    print(f"Wrote {args.output} ({len(out)} rows) using {model_uri}")


if __name__ == "__main__":
    main()
