#!/usr/bin/env bash
# One-shot: venv + deps + DVC bootstrap (if needed) + full ML pipeline + sample predict.
# Run from anywhere:  bash scripts/run_full_demo.sh
# Or from repo root:   ./scripts/run_full_demo.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
PIP="${ROOT}/.venv/bin/pip"
DVC="${ROOT}/.venv/bin/dvc"

echo "=== Project root: ${ROOT} ==="

if [[ ! -f "$PY" ]]; then
  echo "=== Creating .venv ==="
  python3 -m venv "${ROOT}/.venv"
fi

echo "=== Installing dependencies ==="
"$PIP" install --upgrade pip
"$PIP" install -r "${ROOT}/requirements.txt"

if [[ ! -d "${ROOT}/.dvc" ]]; then
  echo "=== Initializing DVC (first time) ==="
  if git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
    "$DVC" init
  else
    "$DVC" init --no-scm
  fi
fi

echo "=== Running ML pipeline (DVC repro or fallback) + demo predict ==="
"$PY" "${ROOT}/pipelines/run_pipeline.py" --full-demo

echo ""
echo "=== Demo complete ==="
echo "  • predictions.csv  — sample batch scores"
echo "  • metrics/train_metrics.json"
echo "  • MLflow:  cd ${ROOT} && .venv/bin/mlflow ui --host 127.0.0.1 --port 5000"
echo "  • API:     .venv/bin/uvicorn src.serve:app --host 127.0.0.1 --port 8080"
