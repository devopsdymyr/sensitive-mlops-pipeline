"""Train risk-label classifier from Feast offline features + MLflow (DPDP-style demo)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import mlflow
import pandas as pd
import yaml
from feast import FeatureStore
from mlflow.exceptions import MlflowException
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "params.yaml"
PROCESSED = ROOT / "data" / "processed" / "sensitive_features.parquet"
FEAST_REPO = ROOT / "feature_repo"
METRICS_DIR = ROOT / "metrics"

FEATURE_REFS = [
    "sensitive_risk_features:pan_hits",
    "sensitive_risk_features:aadhaar_hits",
    "sensitive_risk_features:email_hits",
    "sensitive_risk_features:phone_hits",
    "sensitive_risk_features:account_hits",
    "sensitive_risk_features:keyword_hits",
    "sensitive_risk_features:text_length",
]
FEATURE_COLS = [r.split(":")[1] for r in FEATURE_REFS]


def load_params() -> dict:
    with PARAMS_PATH.open() as f:
        return yaml.safe_load(f)


def _git_tags_from_env() -> dict[str, str]:
    tags: dict[str, str] = {}
    for key in ("CI_COMMIT_SHA", "GITHUB_SHA", "GIT_COMMIT"):
        if val := os.getenv(key):
            tags["git.commit"] = val[:40]
            break
    if ref := os.getenv("CI_COMMIT_REF_NAME") or os.getenv("GITHUB_REF_NAME"):
        tags["git.branch"] = ref
    return tags


def main() -> None:
    params = load_params()
    train_cfg = params["train"]
    mlflow_cfg = params["mlflow"]
    data_cfg = params["data"]

    if not PROCESSED.is_file():
        raise SystemExit(f"Missing {PROCESSED}. Run featurize first.")

    labels = pd.read_parquet(PROCESSED, columns=["record_id", "risk_label"])

    store = FeatureStore(repo_path=str(FEAST_REPO))
    entity_df = pd.read_parquet(PROCESSED, columns=["record_id", "event_timestamp"]).drop_duplicates(
        subset=["record_id"]
    )

    fv_df = store.get_historical_features(entity_df=entity_df, features=FEATURE_REFS).to_df()
    df = fv_df.merge(labels, on="record_id", how="inner")

    X = df[FEATURE_COLS].astype("float32")
    le = LabelEncoder()
    y = le.fit_transform(df["risk_label"].astype(str))

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=train_cfg["test_size"],
        random_state=data_cfg["random_state"],
        stratify=y,
    )

    mlflow.set_experiment(mlflow_cfg["experiment_name"])
    registered_name = mlflow_cfg["registered_model_name"]
    model_alias = mlflow_cfg.get("model_alias", "champion")

    with mlflow.start_run() as run:
        for k, v in _git_tags_from_env().items():
            mlflow.set_tag(k, v)
        mlflow.set_tag("use_case", "sensitive_data_classification")
        mlflow.log_param("label_classes", ",".join(le.classes_))

        mlflow.log_params(
            {
                "C": train_cfg["C"],
                "max_iter": train_cfg["max_iter"],
                "test_size": train_cfg["test_size"],
                "model": train_cfg["model"],
            }
        )

        model = LogisticRegression(
            max_iter=int(train_cfg["max_iter"]),
            C=float(train_cfg["C"]),
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        metrics = {
            "accuracy": float(accuracy_score(y_test, preds)),
            "f1_macro": float(f1_score(y_test, preds, average="macro")),
            "precision_macro": float(precision_score(y_test, preds, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(y_test, preds, average="macro", zero_division=0)),
        }
        mlflow.log_metrics(metrics)

        signature = infer_signature(X_train, model.predict(X_train))
        input_example = X_train.head(5)

        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=registered_name,
            signature=signature,
            input_example=input_example,
        )

        models_dir = ROOT / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        classes_path = models_dir / "risk_label_classes.json"
        with classes_path.open("w") as f:
            json.dump({"classes": list(le.classes_)}, f, indent=2)
        mlflow.log_artifact(str(classes_path), artifact_path="metadata")

        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        metrics_path = METRICS_DIR / "train_metrics.json"
        with metrics_path.open("w") as f:
            json.dump({"run_id": run.info.run_id, **metrics}, f, indent=2)
        print(f"Wrote {metrics_path}")

    client = MlflowClient()
    try:
        versions = client.search_model_versions(f"name='{registered_name}'")
        if not versions:
            print("No registered model versions found; skipping model alias.")
        else:
            mv = max(versions, key=lambda v: int(v.version))
            client.set_registered_model_alias(registered_name, model_alias, mv.version)
            print(f"Model {registered_name} v{mv.version} -> alias @{model_alias}")
    except MlflowException as exc:
        print(f"Skipping model alias ({exc}).")


if __name__ == "__main__":
    main()
