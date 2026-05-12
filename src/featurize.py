"""Stage 2: regex/NLP-style features + Feast apply for sensitive-data risk pipeline."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pii_detector import featurize_dataframe  # noqa: E402

RAW = ROOT / "data" / "raw" / "sensitive_records.csv"
PROCESSED = ROOT / "data" / "processed" / "sensitive_features.parquet"
FEAST_DIR = ROOT / "feature_repo"


def feast_apply_argv() -> list[str] | None:
    for rel in (".venv/bin/feast", ".venv/Scripts/feast.exe"):
        candidate = ROOT / rel
        if candidate.is_file():
            return [str(candidate), "apply"]
    found = shutil.which("feast")
    if found:
        return [found, "apply"]
    return None


def main() -> None:
    if not RAW.is_file():
        raise SystemExit(f"Missing raw data: {RAW}. Run generate_dataset (or `dvc repro`).")

    df = pd.read_csv(RAW)
    df = featurize_dataframe(df, text_col="raw_text")
    df["event_timestamp"] = pd.Timestamp.now(tz="UTC")
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED, index=False)
    print(f"Wrote feature table: {PROCESSED}")

    cmd = feast_apply_argv()
    if not cmd:
        raise SystemExit(
            "Feast CLI not found. Install deps in `.venv` or activate the venv, then re-run."
        )
    r = subprocess.run(cmd, cwd=FEAST_DIR, check=False)
    if r.returncode != 0:
        raise SystemExit("feast apply failed. See errors above.")


if __name__ == "__main__":
    main()
