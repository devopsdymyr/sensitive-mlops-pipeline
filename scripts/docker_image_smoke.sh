#!/usr/bin/env bash
# Smoke-test a pushed Docker image: /healthz always; optional /v1/score if MLflow + classes exist.
#
# Usage:
#   bash scripts/docker_image_smoke.sh YOUR_DOCKERHUB_USER/mlproject:latest
#
# Deep inference check (requires reachable MLflow + models/risk_label_classes.json in container):
#   export MLFLOW_TRACKING_URI=http://host:5000
#   export MLFLOW_S3_ENDPOINT_URL=...   # if artifacts on MinIO
#   export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
#   DEEP=1 bash scripts/docker_image_smoke.sh USER/mlproject:latest
#
# Mount local classes file from a trained workspace:
#   DEEP=1 CLASSES_HOST_PATH=$PWD/models/risk_label_classes.json bash scripts/docker_image_smoke.sh ...

set -euo pipefail

IMAGE="${1:-}"
if [[ -z "$IMAGE" ]]; then
  echo "usage: $0 IMAGE_REF" >&2
  exit 1
fi

PORT="${PORT:-18080}"
NAME="mlproject-smoke-$$"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

RUN_ARGS=( -d --name "$NAME" -p "${PORT}:8080" )
if [[ -n "${MLFLOW_TRACKING_URI:-}" ]]; then
  RUN_ARGS+=( -e "MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}" )
fi
if [[ -n "${MLFLOW_S3_ENDPOINT_URL:-}" ]]; then
  RUN_ARGS+=( -e "MLFLOW_S3_ENDPOINT_URL=${MLFLOW_S3_ENDPOINT_URL}" )
fi
if [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
  RUN_ARGS+=( -e "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}" -e "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}" )
fi
if [[ -n "${AWS_DEFAULT_REGION:-}" ]]; then
  RUN_ARGS+=( -e "AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}" )
fi
if [[ -n "${CLASSES_HOST_PATH:-}" && -f "$CLASSES_HOST_PATH" ]]; then
  RUN_ARGS+=( -v "${CLASSES_HOST_PATH}:/app/models/risk_label_classes.json:ro" )
fi

echo "=== docker run $IMAGE (port $PORT) ==="
docker run "${RUN_ARGS[@]}" "$IMAGE"

for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/tmp/hz.json 2>/dev/null; then
    break
  fi
  sleep 1
done

echo "=== GET /healthz ==="
cat /tmp/hz.json
python3 -c "import json; d=json.load(open('/tmp/hz.json')); assert d.get('status')=='ok', d"

if [[ "${DEEP:-}" == "1" ]]; then
  echo "=== POST /v1/score (DEEP=1) ==="
  curl -fsS "http://127.0.0.1:${PORT}/v1/score" \
    -H "Content-Type: application/json" \
    -d '{"text":"PAN ABCDE1234F"}' | head -c 500
  echo ""
fi

echo "=== Smoke OK ==="
