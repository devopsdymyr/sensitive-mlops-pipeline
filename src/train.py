"""Stage 3: train sklearn model using Feast offline features + MLflow tracking/registry."""

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

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "params.yaml"
PROCESSED = ROOT / "data" / "processed" / "iris_features.parquet"
FEAST_REPO = ROOT / "feature_repo"
METRICS_DIR = ROOT / "metrics"


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

    labels = pd.read_parquet(PROCESSED, columns=["iris_id", "target"])

    store = FeatureStore(repo_path=str(FEAST_REPO))
    entity_df = pd.read_parquet(PROCESSED, columns=["iris_id", "event_timestamp"]).drop_duplicates(
        subset=["iris_id"]
    )

    feature_refs = [
        "iris_features:sepal_length",
        "iris_features:sepal_width",
        "iris_features:petal_length",
        "iris_features:petal_width",
    ]
    fv_df = store.get_historical_features(entity_df=entity_df, features=feature_refs).to_df()
    df = fv_df.merge(labels, on="iris_id", how="inner")

    feature_cols = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
    X = df[feature_cols].astype("float32")
    y = df["target"].astype(int)

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
            "precision_macro": float(precision_score(y_test, preds, average="macro")),
            "recall_macro": float(recall_score(y_test, preds, average="macro")),
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
        print(f"Skipping model alias ({exc}). Load by run URI from MLflow UI if needed.")


if __name__ == "__main__":
    main()
