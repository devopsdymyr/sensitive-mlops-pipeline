"""Fast smoke tests for PII helpers (no MLflow / network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pii_detector import analyze_text, detect_pii_matches  # noqa: E402


def test_pan_detected():
    text = "PAN ABCDE1234F for KYC"
    m = detect_pii_matches(text)
    assert m["PAN"], "expected PAN pattern"


def test_analyze_text_shape():
    out = analyze_text("Customer Name: Test User", include_matches=False)
    assert "risk_score" in out
    assert "risk_label" in out
    assert isinstance(out["risk_score"], (int, float))
