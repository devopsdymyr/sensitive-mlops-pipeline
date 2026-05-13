#!/usr/bin/env bash
# Complete local test: venv, deps, optional dev tools, pipeline, pytest, output verification.
# Usage (from repo root):
#   bash scripts/local_test.sh
#   SKIP_FULL_DEMO=1 bash scripts/local_test.sh   # only venv + pytest (expects prior pipeline)
#   make local-test

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
PIP="${ROOT}/.venv/bin/pip"

echo "=== Local test — project root: ${ROOT} ==="

if [[ ! -x "$PY" ]]; then
  echo "=== Creating .venv ==="
  python3 -m venv "${ROOT}/.venv"
fi

echo "=== pip install (app + dev) ==="
"$PIP" install --upgrade pip
"$PIP" install -r "${ROOT}/requirements.txt"
if [[ -f "${ROOT}/requirements-dev.txt" ]]; then
  "$PIP" install -r "${ROOT}/requirements-dev.txt"
fi

if [[ "${SKIP_FULL_DEMO:-}" == "1" ]]; then
  echo "=== SKIP_FULL_DEMO=1 — skipping pipeline ==="
else
  if [[ ! -d "${ROOT}/.dvc" ]]; then
    echo "=== dvc init (first time) ==="
    if git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
      "${ROOT}/.venv/bin/dvc" init
    else
      "${ROOT}/.venv/bin/dvc" init --no-scm
    fi
  fi
  echo "=== Pipeline + batch predict ==="
  "$PY" "${ROOT}/pipelines/run_pipeline.py" --full-demo
fi

if [[ -d "${ROOT}/tests" ]] && "$PY" -c "import pytest" 2>/dev/null; then
  echo "=== pytest ==="
  "$PY" -m pytest "${ROOT}/tests" -q
else
  echo "=== pytest skipped (no tests/ or pytest not installed) ==="
fi

echo "=== verify_outputs.py ==="
"$PY" "${ROOT}/scripts/verify_outputs.py"

echo ""
echo "=== Local test finished OK ==="
