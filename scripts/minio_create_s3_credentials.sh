#!/usr/bin/env bash
# Create MinIO service-account credentials (S3 access key + secret) for MLflow / DVC / boto3.
# Uses the MinIO root user from .env to mint a child key pair. Compose can then use
# MINIO_ACCESS_KEY + MINIO_SECRET_KEY instead of MINIO_ROOT_* (rotate keys without changing root password).
#
# Prerequisites: from repo root, MinIO running —  docker compose up -d minio
# Usage: bash scripts/minio_create_s3_credentials.sh
#        bash scripts/minio_create_s3_credentials.sh my-svc-name

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin_change_me}"
SVC_NAME="${1:-mlproject-s3}"

if [[ -z "$(docker compose ps -q minio 2>/dev/null)" ]]; then
  echo "MinIO container not found. From repo root run:  docker compose up -d minio" >&2
  exit 1
fi

CID="$(docker compose ps -q minio)"
NET="$(docker inspect "$CID" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' | head -1)"

if [[ -z "$NET" ]]; then
  echo "Could not detect Docker network for the minio service." >&2
  exit 1
fi

MC_IMAGE="${MINIO_MC_IMAGE:-minio/mc:latest}"

json=""
for i in $(seq 1 30); do
  if json="$(
    docker run --rm \
      --network "$NET" \
      --entrypoint /bin/sh \
      "$MC_IMAGE" \
      -c "mc alias set local http://minio:9000 '${MINIO_ROOT_USER}' '${MINIO_ROOT_PASSWORD}' >/dev/null 2>&1 && mc admin user svcacct add local '${MINIO_ROOT_USER}' --name '${SVC_NAME}' --json" 2>/dev/null
  )"; then
    if echo "$json" | grep -q '"accessKey"'; then
      break
    fi
  fi
  sleep 1
done

if [[ -z "$json" ]] || ! echo "$json" | grep -q '"accessKey"'; then
  echo "Failed to create service account (is MinIO healthy on port 9000?). Last output:" >&2
  echo "${json:-<empty>}" >&2
  exit 1
fi

ACCESS="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["accessKey"])' <<<"$json")"
SECRET="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["secretKey"])' <<<"$json")"

echo ""
echo "# --- Add to .env (never commit). Then: docker compose up -d --force-recreate mlflow app ---"
echo "MINIO_ACCESS_KEY=${ACCESS}"
echo "MINIO_SECRET_KEY=${SECRET}"
echo ""
echo "# GitHub Actions → repository Secrets (same values boto uses for S3):"
echo "#   AWS_ACCESS_KEY_ID=${ACCESS}"
echo "#   AWS_SECRET_ACCESS_KEY=${SECRET}"
echo "#   MLFLOW_S3_ENDPOINT_URL=http://PUBLIC_HOST:9000   # replace PUBLIC_HOST"
echo ""
