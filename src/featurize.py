"""Stage 2: build a versioned feature table and apply Feast definitions."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "iris.csv"
PROCESSED = ROOT / "data" / "processed" / "iris_features.parquet"
FEAST_DIR = ROOT / "feature_repo"


def feast_apply_argv() -> list[str] | None:
    """Resolve `feast apply` when the venv is not activated (PATH has no `feast`)."""
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
        raise SystemExit(f"Missing raw data: {RAW}. Run download_data (or `dvc repro download`).")

    df = pd.read_csv(RAW)
    df.insert(0, "iris_id", range(len(df)))
    # Single snapshot timestamp for static batch data (Feast requires a timestamp column).
    df["event_timestamp"] = pd.Timestamp.now(tz="UTC")
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED, index=False)
    print(f"Wrote feature table: {PROCESSED}")

    cmd = feast_apply_argv()
    if not cmd:
        raise SystemExit(
            "Feast CLI not found. Create the project venv and install deps:\n"
            "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
            "Or activate the venv so `feast` is on PATH, then re-run this stage."
        )
    r = subprocess.run(cmd, cwd=FEAST_DIR, check=False)
    if r.returncode != 0:
        raise SystemExit(
            "feast apply failed. Check Feast errors above; ensure `pip install -r requirements.txt` "
            "completed successfully."
        )


if __name__ == "__main__":
    main()
