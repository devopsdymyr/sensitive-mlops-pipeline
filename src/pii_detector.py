"""
PII / sensitive-data detection for this repository (single source of truth).

All regex patterns, feature extraction, heuristic risk scoring, and compliance
tags used by the MLOps flow (generate_dataset → featurize → train → predict →
serve) are defined here only. Do not duplicate detection logic in other modules.

This is a **demo heuristic layer** (not a certified DPDP auditor). Production
systems need legal review, consent flows, and audited models.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# --- Patterns (PII / sensitive signals) ---------------------------------

# Indian PAN: 5 letters, 4 digits, 1 letter (simplified).
_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
# 12-digit Aadhaar-like sequences (spaces or hyphens between groups).
_AADHAAR = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
# Labeled person / customer name (demo — not NER).
_CUSTOMER_NAME = re.compile(
    r"(?:Customer\s+Name|Full\s+Name|Name)\s*:\s*([^\n\r]+)",
    re.IGNORECASE,
)
_EMAIL = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b",
    re.IGNORECASE,
)
_PHONE = re.compile(r"(?<!\d)(?:\+91[\s-]?[6-9]\d{9}|[6-9]\d{9})\b")
_ACCOUNT = re.compile(r"\b\d{9,18}\b")
_SENSITIVE_KW = re.compile(
    r"\b(password|confidential|secret|salary|bank statement|"
    r"credit card|ssn|tax id|pan card|aadhaar)\b",
    re.IGNORECASE,
)

# Human-readable labels for API responses (must match keys in detect_pii_matches).
PII_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "PAN": "Indian income-tax PAN pattern (5 letters + 4 digits + 1 letter; demo regex).",
    "AADHAAR": "12-digit national ID–style numeric block (spacing optional; demo).",
    "EMAIL": "Email address–shaped tokens.",
    "PHONE": "10-digit India mobile–style numbers (+91 optional; demo).",
    "ACCOUNT_NUMBER": "Long numeric runs that may resemble bank / account numbers (high false positives).",
    "SENSITIVE_KEYWORD": "High-risk keywords (e.g. confidential, password, salary; demo list).",
}


def detect_pii_matches(text: str, max_per_type: int = 20) -> dict[str, list[str]]:
    """
    Return matched substrings per category (capped), for explainability / logging.
    """
    if not isinstance(text, str):
        text = str(text)
    t = text
    return {
        "PAN": _PAN.findall(t)[:max_per_type],
        "AADHAAR": _AADHAAR.findall(t)[:max_per_type],
        "EMAIL": _EMAIL.findall(t)[:max_per_type],
        "PHONE": _PHONE.findall(t)[:max_per_type],
        "ACCOUNT_NUMBER": _ACCOUNT.findall(t)[:max_per_type],
        "SENSITIVE_KEYWORD": _SENSITIVE_KW.findall(t)[:max_per_type],
    }


def pii_category_report(text: str, max_examples: int = 5) -> tuple[bool, list[dict[str, Any]]]:
    """
    Per-category PII flags, counts, and example match snippets for APIs (capped).

    Returns (any_pii_detected, list of category rows).
    """
    m = detect_pii_matches(text, max_per_type=100)
    any_pii = any(len(v) > 0 for v in m.values())
    rows: list[dict[str, Any]] = []
    for key, examples in m.items():
        rows.append(
            {
                "category": key,
                "description": PII_CATEGORY_DESCRIPTIONS.get(key, ""),
                "pii_detected": len(examples) > 0,
                "match_count": len(examples),
                "example_snippets": examples[:max_examples],
            }
        )
    return any_pii, rows


# Inference API: entity types and demo confidence (regex / heuristic, not ML NER).
_ENTITY_CONFIDENCE: dict[str, float] = {
    "PERSON_NAME": 0.96,
    "AADHAAR": 0.99,
    "PAN": 0.98,
    "PHONE": 0.97,
    "EMAIL": 0.99,
    "ACCOUNT_NUMBER": 0.85,
}

# Bucket counts for queue-style responses (aligns with financial / identity / contact split).
_ENTITY_BUCKET: dict[str, str] = {
    "PERSON_NAME": "financial",
    "PAN": "financial",
    "ACCOUNT_NUMBER": "financial",
    "AADHAAR": "identity",
    "PHONE": "contact",
    "EMAIL": "contact",
}


def extract_inference_entities(text: str, max_entities: int = 64) -> list[dict[str, Any]]:
    """
    Structured entities for queue / minimal inference payloads (type, value, confidence).

    Uses regex + labeled-line heuristics only (not a production NER model).
    """
    if not isinstance(text, str):
        text = str(text)
    t = text
    spans: list[tuple[int, int, str, str, float]] = []

    for m in _CUSTOMER_NAME.finditer(t):
        val = (m.group(1) or "").strip()
        if val:
            spans.append((m.start(1), m.end(1), "PERSON_NAME", val, _ENTITY_CONFIDENCE["PERSON_NAME"]))

    for label, regex, conf_key in (
        ("AADHAAR", _AADHAAR, "AADHAAR"),
        ("PAN", _PAN, "PAN"),
        ("PHONE", _PHONE, "PHONE"),
        ("EMAIL", _EMAIL, "EMAIL"),
        ("ACCOUNT_NUMBER", _ACCOUNT, "ACCOUNT_NUMBER"),
    ):
        conf = _ENTITY_CONFIDENCE[conf_key]
        for m in regex.finditer(t):
            val = m.group(0)
            spans.append((m.start(0), m.end(0), label, val, conf))

    spans.sort(key=lambda x: x[0])
    out: list[dict[str, Any]] = []
    last_end = -1
    for start, end, typ, val, conf in spans:
        if start < last_end:
            continue
        out.append({"type": typ, "value": val, "confidence": conf})
        last_end = end
        if len(out) >= max_entities:
            break
    return out


def entity_category_counts(entities: list[dict[str, Any]]) -> dict[str, int]:
    """Map entity types to financial / identity / contact hit counts."""
    counts = {"financial": 0, "identity": 0, "contact": 0}
    for e in entities:
        bucket = _ENTITY_BUCKET.get(str(e.get("type", "")), "")
        if bucket in counts:
            counts[bucket] += 1
    return counts


def list_pii_categories() -> list[dict[str, str]]:
    """Stable-ordered category catalog for OpenAPI / GET /v1/categories."""
    return [
        {"category": key, "description": PII_CATEGORY_DESCRIPTIONS.get(key, "")}
        for key in detect_pii_matches("", max_per_type=0)
    ]


def extract_features(text: str) -> dict[str, float]:
    """Numeric feature vector for ML / Feast (one row)."""
    if not isinstance(text, str):
        text = str(text)
    t = text
    return {
        "pan_hits": float(len(_PAN.findall(t))),
        "aadhaar_hits": float(len(_AADHAAR.findall(t))),
        "email_hits": float(len(_EMAIL.findall(t))),
        "phone_hits": float(len(_PHONE.findall(t))),
        "account_hits": float(len(_ACCOUNT.findall(t))),
        "keyword_hits": float(len(_SENSITIVE_KW.findall(t))),
        "text_length": float(min(len(t), 50_000)),
    }


FEATURE_COLUMNS: list[str] = [
    "pan_hits",
    "aadhaar_hits",
    "email_hits",
    "phone_hits",
    "account_hits",
    "keyword_hits",
    "text_length",
]


def featurize_dataframe(df: pd.DataFrame, text_col: str = "raw_text") -> pd.DataFrame:
    """Append PII feature columns derived from raw_text (batch)."""
    feats = df[text_col].map(lambda s: extract_features(s))  # type: ignore[arg-type]
    feat_df = pd.DataFrame(list(feats), columns=FEATURE_COLUMNS)
    return pd.concat([df.reset_index(drop=True), feat_df], axis=1)


def label_from_signals(row: pd.Series) -> tuple[float, str, str]:
    """
    Heuristic risk score (0–100), risk label, and compliance tag from feature row.
    """
    score = (
        25 * min(row["pan_hits"], 2)
        + 25 * min(row["aadhaar_hits"], 2)
        + 10 * min(row["email_hits"], 3)
        + 8 * min(row["phone_hits"], 3)
        + 5 * min(row["account_hits"], 4)
        + 12 * min(row["keyword_hits"], 5)
        + 0.02 * min(row["text_length"], 5000)
    )
    score = float(min(100.0, score))
    if score >= 70:
        label, tag = "HIGH", "BLOCK_OR_REDACT"
    elif score >= 35:
        label, tag = "MEDIUM", "DPDP_REVIEW"
    else:
        label, tag = "LOW", "CLEAR"
    return score, label, tag


def compliance_tag_for_risk_label(label: str) -> str:
    """Map classifier / predicted risk label to a compliance tag."""
    return {"LOW": "CLEAR", "MEDIUM": "DPDP_REVIEW", "HIGH": "BLOCK_OR_REDACT"}.get(label, "DPDP_REVIEW")


def analyze_text(text: str, include_matches: bool = True) -> dict[str, Any]:
    """
    Full PII pass for one document: features, heuristic risk, compliance, optional matches.

    Use this from dataset generation, batch predict (risk_score), and serving.
    """
    feats = extract_features(text)
    s = pd.Series(feats)
    risk_score, risk_label, compliance_tag = label_from_signals(s)
    out: dict[str, Any] = {
        "features": feats,
        "risk_score": risk_score,
        "risk_label": risk_label,
        "compliance_tag": compliance_tag,
    }
    if include_matches:
        out["matches"] = detect_pii_matches(text)
    return out
