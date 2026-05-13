#!/usr/bin/env bash
# Mirror GitHub Actions job "demo" (.github/workflows/ml-demo.yml) on your machine.
# Run from repo root after copying .env secrets if you use hosted MLflow (optional).
#
# Usage:
#   bash scripts/ci_e2e.sh
#
# Equivalent convenience target: make local-test

set -euxo pipefail
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
  PIP="${ROOT}/.venv/bin/pip"
else
  PY="python3"
  PIP="pip3"
fi

export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-${ROOT}/mlruns}"

"$PIP" install --upgrade pip
"$PIP" install -r "${ROOT}/requirements.txt"
"$PIP" install -r "${ROOT}/requirements-dev.txt"

"$PY" -m pytest "${ROOT}/tests" -q --tb=short
test -d "${ROOT}/.dvc" || "${PY}" -m dvc init --no-scm
"$PY" "${ROOT}/pipelines/run_pipeline.py" --full-demo
"$PY" "${ROOT}/scripts/verify_outputs.py"

if [[ -n "${API_HEALTH_URL:-}" ]]; then
  curl -fsS --max-time 30 "${API_HEALTH_URL%/}/healthz" | tee /tmp/ci_healthz.json
  "$PY" -c "import json; d=json.load(open('/tmp/ci_healthz.json')); assert d.get('status')=='ok', d"
fi
if [[ -n "${FEAST_UI_URL:-}" ]]; then
  curl -fsS --max-time 30 -o /dev/null "$FEAST_UI_URL"
fi

"$PY" - <<'PY'
import json
from pathlib import Path
m = json.loads(Path("metrics/train_metrics.json").read_text())
print("train_metrics:", {k: m[k] for k in ("run_id", "accuracy", "f1_macro") if k in m})
PY

echo "ci_e2e.sh: OK (matches GitHub Actions ML demo pipeline core steps)."
