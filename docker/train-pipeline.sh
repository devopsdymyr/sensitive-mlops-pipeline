#!/bin/sh
# Run before `pipelines/run_pipeline.py` in the train service: wire DVC → MinIO when enabled.
set -eu

if [ "${CONFIGURE_DVC_MINIO_REMOTE:-1}" != "1" ]; then
  exec "$@"
fi

endpoint="${MLFLOW_S3_ENDPOINT_URL:-http://minio:9000}"
if dvc remote list 2>/dev/null | grep -q '^minio[[:space:]]'; then
  dvc remote modify minio endpointurl "$endpoint" || true
else
  dvc remote add -d minio "s3://dvc-cache/dvcfiles"
  dvc remote modify minio endpointurl "$endpoint"
fi

# S3 keys are read from the environment by DVC/boto; avoid storing them in .dvc/config.
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

exec "$@"
