"""FastAPI scoring API + Prometheus /metrics (PII logic only via pii_detector)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

import mlflow.sklearn
import pandas as pd
import yaml
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "params.yaml"
CLASSES_PATH = ROOT / "models" / "risk_label_classes.json"

import sys

sys.path.insert(0, str(ROOT / "src"))
from pii_detector import (  # noqa: E402
    FEATURE_COLUMNS,
    analyze_text,
    compliance_tag_for_risk_label,
    entity_category_counts,
    extract_inference_entities,
    featurize_dataframe,
    list_pii_categories,
    pii_category_report,
)

_model: Any = None
_classes: list[str] | None = None

app = FastAPI(
    title="Sensitive data risk scoring",
    version="0.1.0",
    description=(
        "POST /v1/analyze — queue-style payload `{payload_id, data}`; returns entities, "
        "category buckets (financial / identity / contact), and ML `risk_level`. "
        "POST /v1/score — simple `{text}` JSON. GET /v1/categories lists regex detector keys."
    ),
)
SCORE_REQUESTS = Counter("score_requests_total", "Total /score calls")
SCORE_LATENCY = Histogram("score_latency_seconds", "Latency of /score")
ANALYZE_REQUESTS = Counter("analyze_requests_total", "Total /v1/analyze calls")
ANALYZE_LATENCY = Histogram("analyze_latency_seconds", "Latency of /v1/analyze")


def _model_uri() -> str:
    if uri := os.getenv("MLFLOW_MODEL_URI"):
        return uri
    with PARAMS_PATH.open() as f:
        cfg = yaml.safe_load(f)
    m = cfg.get("mlflow", {})
    return f"models:/{m.get('registered_model_name', 'SensitiveDataRiskClassifier')}@{m.get('model_alias', 'champion')}"


def _get_model_and_classes() -> tuple[Any, list[str]]:
    global _model, _classes
    if _model is None:
        if not CLASSES_PATH.is_file():
            raise RuntimeError(f"Train first — missing {CLASSES_PATH}")
        with CLASSES_PATH.open() as f:
            _classes = json.load(f)["classes"]
        _model = mlflow.sklearn.load_model(_model_uri())
    assert _classes is not None
    return _model, _classes


class ScoreRequest(BaseModel):
    """User payload: free-form text to score for sensitive-data / PII risk."""

    text: str = Field(..., max_length=50_000, description="Raw text to analyze.")


class PIICategoryRow(BaseModel):
    category: str
    description: str
    pii_detected: bool
    match_count: int
    example_snippets: list[str]


class ScoreResponse(BaseModel):
    predicted_risk_label: str
    risk_score: float
    compliance_tag: str
    pii_detected: bool = Field(
        ...,
        description="True if any PII / sensitive pattern category matched.",
    )
    categories: list[PIICategoryRow]


class QueueAnalyzeRequest(BaseModel):
    """Minimal queue payload: correlate responses with `payload_id`."""

    payload_id: str = Field(..., max_length=256, description="Opaque id from your queue / caller.")
    data: str = Field(..., max_length=50_000, description="Free-form text to scan for PII and risk.")


class InferenceEntity(BaseModel):
    type: str
    value: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Demo confidence from heuristics, not ML NER.")


class InferenceSummary(BaseModel):
    total_pii_detected: int = Field(..., ge=0, description="Count of structured entities returned.")
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH from the trained classifier on `data`.")


class InferenceCategoryBuckets(BaseModel):
    financial: int = Field(0, ge=0)
    identity: int = Field(0, ge=0)
    contact: int = Field(0, ge=0)


class QueueAnalyzeResponse(BaseModel):
    payload_id: str
    status: Literal["success", "error"]
    summary: InferenceSummary
    entities: list[InferenceEntity]
    categories: InferenceCategoryBuckets


@app.post("/v1/analyze", response_model=QueueAnalyzeResponse)
def analyze_queue(req: QueueAnalyzeRequest) -> QueueAnalyzeResponse:
    """
    Structured PII / risk response for queue workers (payload_id + data).

    Entity `type` values include PERSON_NAME (labeled line), AADHAAR, PAN, PHONE, EMAIL,
    ACCOUNT_NUMBER. `categories` aggregate those into financial / identity / contact counts.
    """
    ANALYZE_REQUESTS.inc()
    model, classes = _get_model_and_classes()
    with ANALYZE_LATENCY.time():
        raw = req.data
        entities_raw = extract_inference_entities(raw)
        entities = [
            InferenceEntity(type=e["type"], value=e["value"], confidence=round(float(e["confidence"]), 2))
            for e in entities_raw
        ]
        counts = entity_category_counts(entities_raw)
        df = pd.DataFrame({"raw_text": [raw]})
        feat = featurize_dataframe(df)
        X = feat[FEATURE_COLUMNS].astype("float32")
        idx = int(model.predict(X)[0])
        label = classes[idx]
    return QueueAnalyzeResponse(
        payload_id=req.payload_id,
        status="success",
        summary=InferenceSummary(total_pii_detected=len(entities), risk_level=label),
        entities=entities,
        categories=InferenceCategoryBuckets(
            financial=counts["financial"],
            identity=counts["identity"],
            contact=counts["contact"],
        ),
    )


@app.post("/v1/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    SCORE_REQUESTS.inc()
    model, classes = _get_model_and_classes()
    with SCORE_LATENCY.time():
        df = pd.DataFrame({"raw_text": [req.text]})
        feat = featurize_dataframe(df)
        X = feat[FEATURE_COLUMNS].astype("float32")
        idx = int(model.predict(X)[0])
        label = classes[idx]
        det = analyze_text(req.text, include_matches=False)
        risk_score = round(float(det["risk_score"]), 2)
        any_pii, cat_rows = pii_category_report(req.text, max_examples=5)
    return ScoreResponse(
        predicted_risk_label=label,
        risk_score=risk_score,
        compliance_tag=compliance_tag_for_risk_label(label),
        pii_detected=any_pii,
        categories=[PIICategoryRow(**r) for r in cat_rows],
    )


@app.get("/v1/categories")
def categories() -> list[dict[str, str]]:
    """Catalog of PII / sensitive pattern categories used by /v1/score."""
    return list_pii_categories()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
