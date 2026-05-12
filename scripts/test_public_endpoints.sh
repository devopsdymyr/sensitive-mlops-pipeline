#!/usr/bin/env bash
# Smoke-test published services (Compose binds host ports on 0.0.0.0 so PUBLIC_IP works).
# Usage:
#   bash scripts/test_public_endpoints.sh
#   bash scripts/test_public_endpoints.sh 34.100.137.211
# Reads PUBLIC_HOST from .env if present (only that line is parsed; full .env is not sourced).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

read_public_host() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  grep -E '^[[:space:]]*PUBLIC_HOST=' "$f" | head -1 | sed 's/^[[:space:]]*PUBLIC_HOST=//; s/^["'\'']//; s/["'\'']$//'
}

read_kv() {
  local key="$1" file="$2" default="$3"
  [[ -f "$file" ]] || { echo "$default"; return; }
  local v
  v="$(grep -E "^[[:space:]]*${key}=" "$file" 2>/dev/null | head -1 | sed "s/^[[:space:]]*${key}=//; s/^[\"']//; s/[\"']$//")" || true
  echo "${v:-$default}"
}

HOST="${1:-}"
if [[ -z "$HOST" ]]; then
  HOST="$(read_public_host .env 2>/dev/null || true)"
fi
if [[ -z "$HOST" ]]; then
  HOST="$(read_public_host .env.docker.example 2>/dev/null || true)"
fi
if [[ -z "$HOST" ]]; then
  echo "Set PUBLIC_HOST in .env (copy from .env.docker.example) or pass the IP as the first argument." >&2
  exit 1
fi

ENVF=
[[ -f .env ]] && ENVF=.env
[[ -z "$ENVF" ]] && [[ -f .env.docker.example ]] && ENVF=.env.docker.example
[[ -z "$ENVF" ]] && ENVF=/dev/null

APP_PORT="$(read_kv APP_PORT "$ENVF" 8080)"
MLFLOW_PORT="$(read_kv MLFLOW_PORT "$ENVF" 5000)"
FEAST_UI_PORT="$(read_kv FEAST_UI_PORT "$ENVF" 8888)"
MINIO_API_PORT="$(read_kv MINIO_API_PORT "$ENVF" 9000)"
MINIO_CONSOLE_PORT="$(read_kv MINIO_CONSOLE_PORT "$ENVF" 9001)"

echo "Using host: $HOST (API :$APP_PORT, MLflow :$MLFLOW_PORT, Feast UI :$FEAST_UI_PORT, MinIO API :$MINIO_API_PORT, console :$MINIO_CONSOLE_PORT)"
echo ""

curl_json() {
  local name="$1" url="$2"
  echo "==> $name"
  echo "    $url"
  if out="$(curl -fsS --max-time 20 "$url" 2>&1)"; then
    echo "$out" | head -c 400
    echo ""
  else
    echo "    FAILED: $out" >&2
    return 1
  fi
}

curl_head() {
  local name="$1" url="$2"
  echo "==> $name"
  echo "    $url"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 20 "$url") || {
    echo "    connection failed" >&2
    return 1
  }
  echo "    HTTP $code"
  case "$code" in
    2??|3??|403) return 0 ;;
    *) return 1 ;;
  esac
}

fail=0
curl_json "FastAPI /healthz" "http://${HOST}:${APP_PORT}/healthz" || fail=1
echo ""
curl_head "MLflow UI (GET /)" "http://${HOST}:${MLFLOW_PORT}/" || fail=1
echo ""
curl_head "Feast UI" "http://${HOST}:${FEAST_UI_PORT}/" || fail=1
echo ""
curl_head "MinIO S3 API (root)" "http://${HOST}:${MINIO_API_PORT}/minio/health/live" || fail=1
echo ""
curl_head "MinIO console" "http://${HOST}:${MINIO_CONSOLE_PORT}/" || fail=1

if [[ "$fail" -ne 0 ]]; then
  echo "" >&2
  echo "One or more checks failed. Open the VM firewall for TCP $APP_PORT $MLFLOW_PORT $FEAST_UI_PORT $MINIO_API_PORT $MINIO_CONSOLE_PORT (see docs/DOCKER.md)." >&2
  exit 1
fi

echo ""
echo "All checks passed."
