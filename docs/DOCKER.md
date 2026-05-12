# Docker: self-hosted MLflow + MinIO + Feast UI + DVC + API

This stack runs **PostgreSQL** (MLflow experiment metadata), **MinIO** (S3-compatible storage for MLflow model artifacts and the **DVC** remote bucket `dvc-cache`), **MLflow** tracking server, **Feast UI** (browse the feature registry), and the **FastAPI** app from this repo.

**Feast** uses a **local file registry** (`registry.db`) and **SQLite online store** under `data/feast/`, on the Docker volume `feast_registry` (`feature_repo/feature_store.yaml` paths stay relative). Run **`train`** once so `feast apply` creates the registry; then open Feast UI.

**DVC**: the **`train`** service runs **`dvc repro`** (same stages as `dvc.yaml`). A **MinIO** remote is registered automatically by `docker/train-pipeline.sh` (bucket `dvc-cache`, prefix `dvcfiles`) so you can `dvc push` / `dvc pull` from that remote. The **`.dvc/cache`** directory is a named volume for faster repeat runs.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose v2](https://docs.docker.com/compose/)

## Quick start

```bash
cd /path/to/mlproject
cp .env.docker.example .env
# Edit .env — set strong passwords before any public host.

docker compose build
docker compose up -d
```

Wait until **MLflow** is healthy (~30–60s first time). Then train and register the model (**`dvc repro`**, Feast registry on `feast_registry`, model on **`models_vol`**, MLflow/MinIO):

```bash
docker compose --profile train run --rm train
docker compose restart app
curl -s http://localhost:8080/healthz
```

- **API:** `http://localhost:8080` (scores use the model from MLflow registry; artifacts live on MinIO).
- **MLflow UI:** `http://localhost:5000`
- **Feast UI:** `http://localhost:8888` (feature definitions + registry after at least one `train` / `feast apply`).
- **MinIO console:** `http://localhost:9001` (default user/password from `.env` until you change them).

If **5000**, **8080**, or **8888** is already in use on the host (common on macOS with AirPlay, or local dev servers), override before `up`:

```bash
export MLFLOW_PORT=15001 APP_PORT=28180 FEAST_UI_PORT=18888
docker compose up -d
```

## Access via instance public IP (browser / GitHub Actions)

**Compose behavior**

- Published ports use **`0.0.0.0:${PORT}`** on the VM so listeners accept traffic to the **instance public IP**, not only `127.0.0.1`.
- **`PUBLIC_HOST`** must be in **`.env`** (start from **`.env.docker.example`**) **before** `docker compose up` so MinIO gets correct **`MINIO_SERVER_URL`** and **`MINIO_BROWSER_REDIRECT_URL`** (built in **`docker-compose.yml`** from `PUBLIC_HOST` + **`MINIO_API_PORT`** / **`MINIO_CONSOLE_PORT`**).
- **PostgreSQL** is **not** published on the host — it stays on the Docker network for MLflow only (not open on the public IP).

**Firewall**

1. Set **`PUBLIC_HOST`** in **`.env`** (default in **`.env.docker.example`**; refresh after reprovision, e.g. `curl -fsS https://api.ipify.org`).
2. Open **TCP** on your cloud firewall / VPC for: **`APP_PORT`**, **`MLFLOW_PORT`**, **`FEAST_UI_PORT`**, **`MINIO_API_PORT`**, **`MINIO_CONSOLE_PORT`** (defaults **8080**, **5000**, **8888**, **9000**, **9001**).

**Example (GCP — replace `NETWORK_TAG`, tighten `--source-ranges` for production)**

```bash
gcloud compute firewall-rules create mlproject-demo-tcp \
  --allow=tcp:8080,tcp:5000,tcp:8888,tcp:9000,tcp:9001 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=NETWORK_TAG \
  --description="MLproject stack — restrict source IPs in production"
```

3. URLs (defaults):

| Service | URL |
|---------|-----|
| FastAPI health | `http://PUBLIC_HOST:8080/healthz` |
| MLflow UI | `http://PUBLIC_HOST:5000` |
| Feast UI | `http://PUBLIC_HOST:8888` |
| MinIO S3 API | `http://PUBLIC_HOST:9000` |
| MinIO console | `http://PUBLIC_HOST:9001` |

4. Smoke test from any machine (uses **`PUBLIC_HOST`** and ports from **`.env`** or **`.env.docker.example`**):

```bash
make public-test
# or: bash scripts/test_public_endpoints.sh
# or: bash scripts/test_public_endpoints.sh 203.0.113.10
```

**GitHub Actions:** set repository secrets to the same **`http://PUBLIC_HOST:…`** values (see **`docs/GITHUB_SETUP.md`**). Prefer **HTTPS** + a reverse proxy before exposing anything sensitive on the internet.

## Environment variables (integration)

| Variable | Where | Purpose |
|----------|--------|---------|
| `MLFLOW_TRACKING_URI` | `app`, `train` | `http://mlflow:5000` — all runs and registry lookups go to the MLflow container. |
| `MLFLOW_S3_ENDPOINT_URL` | `app`, `train`, `mlflow` | `http://minio:9000` — boto3/MLflow talk S3 API to MinIO. |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | same | MinIO root user/password (dev defaults in `.env.docker.example`). |
| `CONFIGURE_DVC_MINIO_REMOTE` | `train` | `1` (default): `docker/train-pipeline.sh` adds default remote `minio` → `s3://dvc-cache/dvcfiles` and sets `endpointurl`. Set `0` to skip (local cache only). |
| `SKIP_DVC` | host / CI only | Not set in Compose by default. Set `1` on `python pipelines/run_pipeline.py` to run the three scripts without `dvc repro` (e.g. smoke test without `.dvc`). |

## Optional: DVC remote from your laptop

If you use the same MinIO ports on localhost (after `docker compose up`):

```bash
dvc remote add -d minio s3://dvc-cache/dvcfiles
dvc remote modify minio endpointurl http://localhost:9000
dvc remote modify minio access_key_id minioadmin
dvc remote modify minio secret_access_key 'your-minio-password'
```

The compose stack pre-creates the **`dvc-cache`** bucket for this pattern.

## `dvc push` / `dvc pull`

After `docker compose --profile train run --rm train`, from the project directory with the same remote configured:

```bash
dvc push   # upload cached outs to MinIO
dvc pull   # restore from MinIO on a fresh clone
```

## Public exposure (read carefully)

- Compose publishes **MLflow**, **MinIO**, **Feast UI**, and the **API** on host ports — fine on a **dev VM** behind a firewall.
- For **internet-facing** services: put **TLS** (e.g. nginx, Caddy, Traefik, cloud LB), **strong secrets**, **network policies**, and **do not** expose Postgres or MinIO root to the world without hardening.
- Replace default passwords in **`.env`** before any shared or public host.

## Images

| File | Role |
|------|------|
| `Dockerfile` | Shared image for **app**, **feast-ui**, **train**: deps, `.venv/bin/python` → system Python (for `dvc.yaml`), `docker/train-pipeline.sh`. |
| `docker/mlflow.Dockerfile` | MLflow server + Postgres wait + MinIO bucket bootstrap. |
| `docker/train-pipeline.sh` | Registers MinIO DVC remote + `exec` pipeline command. |
| `docker-compose.yml` | Postgres, MinIO, MLflow, Feast UI, API, optional `train` profile; **`app` / `feast-ui` / `train` share image `mlproject/python-runner:local`**. |

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| `app` 500 / model missing | Run **`train`** profile once, then **`docker compose restart app`**. |
| MLflow cannot reach MinIO | Ensure **`minio`** is up; MLflow entrypoint waits for TCP `9000`. |
| Feast errors | Volume **`feast_registry`** must be writable; wipe volume only if you accept losing the local registry. |
| Feast UI empty | Run **`train`** (or `feast apply` in `feature_repo`) so **`registry.db`** exists on **`feast_registry`**. |
| Stale **`train`** image vs **`app`** | All three Python services use the same **`image:`** — run **`docker compose build`** once. |
