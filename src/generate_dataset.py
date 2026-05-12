"""Stage 1: synthetic sensitive-text dataset (labels come only from pii_detector.analyze_text)."""

from __future__ import annotations

import argparse
import random
import string
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pii_detector import analyze_text  # noqa: E402


def _rand_pan(rng: random.Random) -> str:
    letters = "".join(rng.choice(string.ascii_uppercase) for _ in range(5))
    digits = "".join(rng.choice(string.digits) for _ in range(4))
    tail = rng.choice(string.ascii_uppercase)
    return letters + digits + tail


def _rand_aadhaar(rng: random.Random) -> str:
    d = "".join(rng.choice(string.digits) for _ in range(12))
    return f"{d[:4]} {d[4:8]} {d[8:]}"


def _synthetic_line(rng: random.Random, profile: str) -> str:
    parts: list[str] = ["Log snippet:", "user_action=upload"]
    if profile in ("high", "medium", "mixed"):
        if profile in ("high", "mixed") and rng.random() < 0.9:
            parts.append(f" note={_rand_pan(rng)}")
        if profile in ("high", "medium") and rng.random() < 0.7:
            parts.append(f" id={_rand_aadhaar(rng)}")
        if rng.random() < 0.5:
            parts.append(" email=user@example.com")
        if rng.random() < 0.45:
            parts.append(" phone=+919876543210")
        if rng.random() < 0.35:
            parts.append(" acct=000123456789012345")
    if profile in ("high", "medium") and rng.random() < 0.6:
        parts.append(" CONFIDENTIAL salary spreadsheet attached")
    if profile == "low":
        parts.append(" status=ok no sensitive markers")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "raw" / "sensitive_records.csv")
    parser.add_argument("--n", type=int, default=2500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    profiles = ["low"] * (args.n // 3) + ["medium"] * (args.n // 3) + ["high"] * (args.n - 2 * (args.n // 3))
    rng.shuffle(profiles)

    rows = []
    for i, prof in enumerate(profiles):
        text = _synthetic_line(rng, prof)
        det = analyze_text(text, include_matches=False)
        rows.append(
            {
                "record_id": i,
                "raw_text": text,
                "risk_score": det["risk_score"],
                "risk_label": det["risk_label"],
                "compliance_tag": det["compliance_tag"],
            }
        )

    pd.DataFrame(rows).to_csv(args.out, index=False)
    print(f"Wrote {len(rows)} synthetic records to {args.out}")


if __name__ == "__main__":
    main()
