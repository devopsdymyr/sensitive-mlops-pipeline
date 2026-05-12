#!/bin/sh
set -eu
host="${PGHOST:-postgres}"
port="${PGPORT:-5432}"
i=0
while ! python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${host}',${port})); s.close()" 2>/dev/null; do
  i=$((i + 1))
  if [ "$i" -gt 60 ]; then
    echo "Postgres at ${host}:${port} not reachable"
    exit 1
  fi
  sleep 1
done

python - <<'PY'
import os, socket, time

def wait_tcp(h, p, tries=60):
    for _ in range(tries):
        try:
            s = socket.create_connection((h, p), 2)
            s.close()
            return
        except OSError:
            time.sleep(1)
    raise SystemExit(f"cannot reach {h}:{p}")

wait_tcp("minio", 9000)

from minio import Minio

mc = Minio(
    "minio:9000",
    access_key=os.environ["AWS_ACCESS_KEY_ID"],
    secret_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    secure=False,
)
for bucket in ("mlflow-artifacts", "dvc-cache"):
    if not mc.bucket_exists(bucket):
        mc.make_bucket(bucket)
PY

exec mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri "${MLFLOW_BACKEND_STORE_URI}" \
  --default-artifact-root "${MLFLOW_DEFAULT_ARTIFACT_ROOT}"
