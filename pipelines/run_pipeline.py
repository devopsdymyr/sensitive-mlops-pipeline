#!/usr/bin/env python3
"""
Orchestrate the MLOps pipeline.

Best practice: use **DVC** as the single source of truth once `dvc init` has been run
(`git init` + `dvc init`, or `dvc init --no-scm`). This script runs `dvc repro` when
`.dvc/` exists so data and stages are versioned in the DVC cache.

Fallback: if DVC is not initialized, runs the same three Python steps (good for first
tries before `dvc init`). Kubeflow Pipelines can call the same commands in containers later.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_dvc() -> str | None:
    venv_dvc = ROOT / ".venv" / "bin" / "dvc"
    if venv_dvc.is_file():
        return str(venv_dvc)
    return shutil.which("dvc")


def run_step(description: str, argv: list[str]) -> None:
    print(f"\n=== {description} ===")
    r = subprocess.run(argv, cwd=ROOT, check=False)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main() -> None:
    py = sys.executable
    dvc_bin = resolve_dvc()
    use_dvc = (ROOT / ".dvc").is_dir() and dvc_bin is not None

    if use_dvc:
        print("\n=== DVC pipeline (dvc repro) — versions data + stages ===")
        r = subprocess.run([dvc_bin, "repro"], cwd=ROOT, check=False)
        if r.returncode != 0:
            print(
                "\nDVC failed. If you see a Git error: `git init && git add . && git commit -m init` then `dvc init`.\n"
                "Without Git: `dvc init --no-scm`.\n"
                "Then re-run this script.\n",
                file=sys.stderr,
            )
            raise SystemExit(r.returncode)
    else:
        if dvc_bin and not (ROOT / ".dvc").is_dir():
            print(
                "\nNote: `.dvc/` not found — running scripts only (no DVC cache).\n"
                "Best practice: `dvc init` (with Git) or `dvc init --no-scm`, then re-run for `dvc repro`.\n"
            )
        run_step("Download raw data", [py, "src/download_data.py"])
        run_step("Featurize + Feast apply", [py, "src/featurize.py"])
        run_step("Train + MLflow registry", [py, "src/train.py"])

    print(
        "\nPipeline finished.\n"
        "  • MLflow UI: `mlflow ui`\n"
        "  • Inference: `python src/predict.py --input sample_input.csv`\n"
        "  • Optional lakeFS: `python src/upload_data_lakefs.py` (after quickstart server is up)\n"
    )


if __name__ == "__main__":
    main()
