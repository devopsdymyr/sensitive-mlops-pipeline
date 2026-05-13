# Architecture, GitHub Actions, and Docker Hub flow

This document matches the code in this repository: **DVC** stages (`dvc.yaml`), **`pipelines/run_pipeline.py`**, **MLflow** registration in **`src/train.py`**, **FastAPI** in **`src/serve.py`**, **`.github/workflows/ml-demo.yml`**, and **`.github/workflows/docker-publish.yml`**.

---

## 1. System architecture (local, Docker stack, and optional hosted endpoints)

```mermaid
flowchart TB
  subgraph dev["Local developer"]
    VENV[".venv + requirements.txt"]
    DVC_CLI["dvc repro / run_pipeline.py"]
    MLF_LOCAL["MLflow file store ./mlruns"]
    VENV --> DVC_CLI
    DVC_CLI --> MLF_LOCAL
  end

  subgraph docker["Docker Compose (docker-compose.yml)"]
    MINIO["MinIO S3 API :9000"]
    PG["Postgres MLflow backend"]
    MLF_SRV["MLflow UI :5000"]
    FEAST_UI["Feast UI :8888"]
    TRAIN["train profile: train-pipeline.sh + run_pipeline.py"]
    APP["app: uvicorn serve :8080"]
    MINIO --> MLF_SRV
    PG --> MLF_SRV
    TRAIN --> MLF_SRV
    TRAIN --> MINIO
    APP --> MLF_SRV
    APP --> MINIO
  end

  subgraph data_artifacts["Data & artifacts per run"]
    RAW["data/raw/sensitive_records.csv"]
    PROC["data/processed/sensitive_features.parquet"]
    MET["metrics/train_metrics.json"]
    PRED["predictions.csv"]
    REG["MLflow Model Registry + @champion alias"]
    RAW --> PROC --> MET
    PROC --> REG
  end

  DVC_CLI --> RAW
  TRAIN --> RAW
  TRAIN --> PROC

  subgraph public["Optional public checks (secrets / firewall)"]
    API_PUB["FastAPI /healthz on VM IP:8080"]
    FEAST_PUB["Feast UI on VM IP:8888"]
    MLF_PUB["MLflow on VM IP:5000"]
  end

  APP -.->|"PUBLIC_HOST + SG"| API_PUB
  FEAST_UI -.-> FEAST_PUB
  MLF_SRV -.-> MLF_PUB
```

**Public endpoints:** Compose binds services to `0.0.0.0` (see `docker-compose.yml`). Your cloud **firewall / security group** must allow the same TCP ports. CI and `scripts/test_public_endpoints.sh` call those URLs when **`API_HEALTH_URL`**, **`FEAST_UI_URL`**, and MLflow/S3 secrets are set (`docs/GITHUB_SETUP.md`).

---

## 2. GitHub Actions — `ml-demo.yml` stage by stage

Each step maps to a **function** in your pipeline (shell or Action).

```mermaid
flowchart TD
  T0([Trigger: push/PR main, workflow_dispatch]) --> S1

  S1["Checkout actions/checkout@v4<br/>Function: clone repo at GITHUB_SHA"]
  S1 --> S2

  S2["Map secrets to env<br/>Function: export MLFLOW_TRACKING_URI, AWS_*, API_HEALTH_URL, FEAST_UI_URL<br/>Default MLflow: $GITHUB_WORKSPACE/mlruns"]
  S2 --> S3

  S3["setup-python@v5 + pip cache<br/>Function: Python 3.10"]
  S3 --> S4

  S4["pip install -r requirements.txt + requirements-dev.txt<br/>Function: app + pytest"]
  S4 --> S5

  S5["pytest tests/<br/>Function: fail-fast unit/smoke tests"]
  S5 --> S6

  S6["Ensure DVC metadata<br/>Function: test -d .dvc || dvc init --no-scm"]
  S6 --> S7

  S7["Full pipeline + sample predict<br/>Function: python pipelines/run_pipeline.py --full-demo<br/>• dvc repro OR generate → featurize → train<br/>• train: MLflow metrics + register SensitiveDataRiskClassifier @champion<br/>• predict.py → predictions.csv"]
  S7 --> S8

  S8["Validate pipeline outputs (E2E)<br/>Function: python scripts/verify_outputs.py"]
  S8 --> S9

  S9["Optional public checks<br/>Function: curl API /healthz; curl Feast UI<br/>Only if secrets set"]
  S9 --> S10

  S10["E2E summary + upload-artifact demo-outputs<br/>Function: print train_metrics; zip metrics, predictions, raw, parquet, models/risk_label_classes.json"]
```

**Per-build storage:**

| Artifact path | Role |
|---------------|------|
| `data/raw/sensitive_records.csv` | Raw synthetic rows (`generate_dataset.py`) |
| `data/processed/sensitive_features.parquet` | Processed features + Feast (`featurize.py`) |
| `metrics/train_metrics.json` | **accuracy**, **f1_macro**, run id (`train.py`) |
| `predictions.csv` | Batch inference on `sample_input.csv` (`predict.py`) |
| `mlruns/` (job workspace) | MLflow runs + model files when tracking URI is local |

Fork PRs do not receive secrets; those builds use **local `mlruns`** in the runner only.

**`dvc.yaml` and CI:** stages use **`${py}: .venv/bin/python`**. On GitHub Actions, **“Wire DVC Python path”** symlinks the runner’s `python` to **`.venv/bin/python`** (same pattern as **`Dockerfile`**) so **`dvc repro`** succeeds without committing a venv.

---

## 3. Training, metrics, accuracy, and model registry

```mermaid
flowchart LR
  subgraph train_py["src/train.py"]
    A["Feast get_historical_features"]
    B["train_test_split + LogisticRegression.fit"]
    C["mlflow.log_metrics accuracy, f1_macro, …"]
    D["mlflow.sklearn.log_model registered_model_name"]
    E["set_registered_model_alias @champion"]
    A --> B --> C --> D --> E
  end

  PROC2["sensitive_features.parquet"] --> A
  E --> REG2["Registry: SensitiveDataRiskClassifier"]
  C --> MET2["metrics/train_metrics.json"]
```

**Consumers:**

- **`src/predict.py`** — loads `models:/SensitiveDataRiskClassifier@champion` (see `params.yaml`).
- **`src/serve.py`** — same URI via `MLFLOW_MODEL_URI` or `params.yaml`; needs **`models/risk_label_classes.json`** on disk (written by `train.py`).

---

## 4. Model registry → Docker image → Docker Hub → run container

The **Dockerfile** packages **code + dependencies**; it does **not** embed the trained sklearn weights by default (they live in MLflow artifact storage). The **running** container must reach **MLflow** and have **`models/risk_label_classes.json`** (volume from train step, or copy from CI after training).

```mermaid
flowchart TD
  subgraph registry["MLflow Model Registry"]
    R1["Registered model + version"]
    R2["Artifact URI on MinIO/S3 or local mlruns"]
    R1 --> R2
  end

  subgraph image_build["CI: docker-publish workflow"]
    B1["docker build -f Dockerfile"]
    B2["docker push USER/mlproject:tag"]
    B1 --> B2
  end

  subgraph hub["Docker Hub"]
    H1["Image: code + Python deps"]
  end

  subgraph run["Runtime (VM / K8s / Compose app service)"]
    U1["docker run -e MLFLOW_TRACKING_URI …"]
    U2["Optional: -v …/risk_label_classes.json:/app/models/…"]
    U3["uvicorn src.serve:app loads model from registry"]
    U1 --> U3
    U2 --> U3
  end

  R2 -.->|"mlflow.sklearn.load_model"| U3
  image_build --> hub
  hub --> run
```

**Smoke test without scoring:** `GET /healthz` returns `{"status":"ok"}` without loading the model (`serve.py`). **Full inference test** needs MLflow reachable + `risk_label_classes.json` (see `scripts/docker_image_smoke.sh`).

---

## 5. End-to-end sequence (one diagram)

```mermaid
sequenceDiagram
  participant GH as GitHub Actions
  participant DVC as DVC stages
  participant ML as MLflow
  participant S3 as MinIO/S3 artifacts
  participant DH as Docker Hub
  participant C as Container

  GH->>DVC: run_pipeline.py --full-demo
  DVC->>DVC: generate_dataset → raw CSV
  DVC->>DVC: featurize → parquet + feast apply
  DVC->>ML: train.py log_metrics + log_model
  ML->>S3: store model artifacts
  ML->>ML: register + @champion
  GH->>GH: upload-artifact metrics, csv, parquet
  Note over GH,DH: Manual workflow docker-publish.yml (optional push trigger)
  GH->>DH: docker build push
  C->>DH: docker pull
  C->>ML: load_model models:/…@champion
  C->>C: uvicorn serve /v1/score
```

---

## Related files

| Topic | Path |
|-------|------|
| Local full demo | `scripts/run_full_demo.sh`, `make demo` |
| Same steps as GitHub job (venv bootstrap + full demo) | `scripts/local_test.sh`, `make local-test` |
| Same steps as GitHub job (uses system or `.venv` python) | `scripts/ci_e2e.sh`, `make ci-e2e` |
| Output checks only | `scripts/verify_outputs.py`, `make verify` |
| Docker stack | `docker-compose.yml`, `docs/DOCKER.md` |
| GitHub ML CI | `.github/workflows/ml-demo.yml` |
| Docker Hub push | `.github/workflows/docker-publish.yml` |
| Public URL smoke | `scripts/test_public_endpoints.sh`, `make public-test` |
