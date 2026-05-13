#!/usr/bin/env python3
"""Assert pipeline outputs exist and look sane (used by scripts/local_test.sh)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    ("data/raw/sensitive_records.csv", True),
    ("data/processed/sensitive_features.parquet", True),
    ("metrics/train_metrics.json", True),
    ("models/risk_label_classes.json", True),
    ("predictions.csv", False),
)


def main() -> int:
    errors: list[str] = []
    for rel, required in REQUIRED:
        p = ROOT / rel
        if not p.is_file():
            if required:
                errors.append(f"missing required file: {rel}")
            continue
        if rel.endswith("train_metrics.json"):
            data = json.loads(p.read_text())
            for key in ("accuracy", "f1_macro"):
                if key not in data:
                    errors.append(f"{rel}: missing metric {key!r}")
            if not isinstance(data.get("accuracy"), (int, float)):
                errors.append(f"{rel}: accuracy must be numeric")
        if rel.endswith("risk_label_classes.json"):
            data = json.loads(p.read_text())
            if "classes" not in data or not data["classes"]:
                errors.append(f"{rel}: expected non-empty 'classes' list")
        if rel.endswith("predictions.csv"):
            with p.open(newline="") as f:
                row = next(csv.DictReader(f), None)
            if not row:
                errors.append(f"{rel}: empty or no header")
            else:
                for col in ("raw_text", "predicted_risk_label"):
                    if col not in row:
                        errors.append(f"{rel}: missing column {col!r}")

    if errors:
        print("verify_outputs.py failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("verify_outputs.py: all checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
