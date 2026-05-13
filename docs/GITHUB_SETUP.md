# Push this project to GitHub

## 1) Create an empty repository on GitHub

1. Open [github.com/new](https://github.com/new).
2. Repository name: choose any name (e.g. **`sensitive-mlops-pipeline`**).
3. Choose **Public** or **Private**.
4. **Do not** add a README, `.gitignore`, or license (this repo already has them).
5. Click **Create repository**.

## 2) Commit locally (if you have not already)

From this project’s root:

```bash
git status
git add -A
git commit -m "Initial commit: sensitive data MLOps pipeline (DVC, Feast, MLflow, FastAPI)"
```

## 3) Add the remote and push

Replace **`YOUR_USER`** and **`REPO_NAME`** with your GitHub username and repo name:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USER/REPO_NAME.git
git push -u origin main
```

**If `error: remote origin already exists`:** use **`git remote set-url`** instead of **`add`**:

```bash
git remote set-url origin https://github.com/YOUR_USER/REPO_NAME.git
git push -u origin main
```

**Typo check:** the branch name is **`main`**, not `mai`.

**SSH** (if **`origin` already exists**):

```bash
git remote set-url origin git@github.com:YOUR_USER/REPO_NAME.git
git push -u origin main
```

### Pushing workflow files (`.github/workflows/`)

GitHub may reject pushes that add or change workflows unless your credential has the **`workflow`** scope. Use **`gh auth login`** and paste a **classic PAT** with **`repo`** + **`workflow`**, or push from the GitHub **web editor**.

## 4) Enable GitHub Actions

1. **Settings → Actions → General** — allow workflows (your org’s policy may require admin approval).
2. **Actions** → **ML demo pipeline** — runs on **push** / **pull_request** to **`main`**, or **Run workflow** (manual). The job runs **pytest**, then **`pipelines/run_pipeline.py --full-demo`**, then **`scripts/verify_outputs.py`**, optional **public URL** checks if secrets are set, then uploads **demo-outputs** (metrics, CSVs, parquet, **`models/risk_label_classes.json`**).
3. Optional: add **repository secrets** and/or **Actions variables** (same names) so CI uses your **hosted** MLflow, MinIO (S3 API), and public HTTP checks (see table below). The workflow sets **job-level `env`** from **secrets first**, then **variables**, then defaults.

The workflow file is **`.github/workflows/ml-demo.yml`**. A copy for reference lives at **`docs/github_actions_ml_demo.yml`** (keep them in sync when editing).

**Docker Hub image:** **`.github/workflows/docker-publish.yml`** builds **`Dockerfile`** and pushes **`DOCKERHUB_USERNAME/mlproject`** with tags **`latest`** and **`:<commit-sha>`** (the SHA is the **ML demo** passing commit when the workflow is triggered by **`workflow_run`**; on **manual** dispatch it is the checked-out **`github.sha`**). **Triggers:** (1) **Actions → “Docker Hub — build and push” → Run workflow**; (2) automatically after **“ML demo pipeline”** succeeds on a **push** to **`main`** (skips **fork** repos and does not run for PR-only ML demo successes). Add secrets **`DOCKERHUB_USERNAME`** and **`DOCKERHUB_TOKEN`**. The job uses **Docker Buildx** with **GHA layer cache**, then **pulls** the SHA-tagged image and checks **`GET /healthz`**. Architecture diagrams are in **`docs/ARCHITECTURE_AND_CI.md`** §6–7.

## 5) Optional CI secrets and variables (public / hosted endpoints)

Configure under **Settings → Secrets and variables → Actions** using the **same names** in either tab:

- **Secrets** — use for passwords, access keys, and any value that must not appear in logs.
- **Variables** — use for non-sensitive URLs (e.g. public `http://host:5000`) if you prefer not to store them as secrets.

The workflow resolves each value as **`secret || variable || default`** (see **`env:`** on the **`demo`** job in **`.github/workflows/ml-demo.yml`**). If both are unset, the job falls back to local behavior (e.g. MLflow under **`${{ github.workspace }}/mlruns`**).

| Name | Put in **Secrets** | Put in **Variables** (optional) |
|------|-------------------|----------------------------------|
| **`MLFLOW_TRACKING_URI`** | yes | yes (public URL) — secret wins if both set |
| **`MLFLOW_S3_ENDPOINT_URL`** | yes | yes |
| **`AWS_DEFAULT_REGION`** | yes | yes |
| **`API_HEALTH_URL`** / **`FEAST_UI_URL`** | yes | yes |
| **`AWS_ACCESS_KEY_ID`** / **`AWS_SECRET_ACCESS_KEY`** | **yes (required for keys)** | **no** — never store keys in Variables |

### Complete example (Docker Compose on one VM — default ports)

Replace **`34.100.137.211`** with your instance’s **public IP** (must match **`PUBLIC_HOST`** in the VM’s **`.env`** so MLflow/MinIO agree with what GitHub calls). Open **TCP 5000, 9000, 8080, 8888** (and **9001** if you use the MinIO console) on the cloud firewall.

**Option 1 — Simplest: put everything under Secrets** (copy **Name** = left, **Secret** = right):

| Secret name | Example value |
|-------------|----------------|
| `MLFLOW_TRACKING_URI` | `http://34.100.137.211:5000` |
| `MLFLOW_S3_ENDPOINT_URL` | `http://34.100.137.211:9000` |
| `AWS_DEFAULT_REGION` | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | `minioadmin` |
| `AWS_SECRET_ACCESS_KEY` | `minioadmin_change_me` |
| `API_HEALTH_URL` | `http://34.100.137.211:8080` |
| `FEAST_UI_URL` | `http://34.100.137.211:8888` |

The **`AWS_*`** pair above matches the **default** **`MINIO_ROOT_USER`** / **`MINIO_ROOT_PASSWORD`** in **`.env.docker.example`**. If you changed those on the VM, use your real values instead. Prefer **`make minio-keys`** on the VM and paste **`MINIO_ACCESS_KEY`** / **`MINIO_SECRET_KEY`** as **`AWS_ACCESS_KEY_ID`** / **`AWS_SECRET_ACCESS_KEY`**.

**Option 2 — URLs in Variables, keys in Secrets only** (same **names**; credentials never in Variables):

| Variable name | Example value |
|---------------|----------------|
| `MLFLOW_TRACKING_URI` | `http://34.100.137.211:5000` |
| `MLFLOW_S3_ENDPOINT_URL` | `http://34.100.137.211:9000` |
| `AWS_DEFAULT_REGION` | `us-east-1` |
| `API_HEALTH_URL` | `http://34.100.137.211:8080` |
| `FEAST_UI_URL` | `http://34.100.137.211:8888` |

| Secret name | Example value |
|-------------|----------------|
| `AWS_ACCESS_KEY_ID` | `minioadmin` (or service account key from **`make minio-keys`**) |
| `AWS_SECRET_ACCESS_KEY` | `minioadmin_change_me` (or matching secret key) |

If a name exists in **both** tabs, the **Secret** value is used.

**Checklist so “everything works”**

1. **`docker compose up -d`** on the VM; **`PUBLIC_HOST`** in **`.env`** equals the IP you put in GitHub.
2. Firewall allows **GitHub-hosted runners** to reach those **HTTP ports** (often you allow **`0.0.0.0/0`** on a demo VM; tighten for production).
3. **`MLFLOW`** and **`app`** have been started at least once (**`docker compose up -d`**) so MLflow and the API respond; optional checks need **`API_HEALTH_URL`** and **`FEAST_UI_URL`** reachable.
4. After **`docker compose --profile train run --rm train`**, Feast UI has data; **`curl -fsS http://IP:8080/healthz`** returns **`{"status":"ok"}`**.

See also **`docs/github_actions_env.example`** for the same list in comment form.

| Name (Secret and/or Variable) | Purpose |
|------------------------------|---------|
| **`MLFLOW_TRACKING_URI`** | Tracking server URL, e.g. `https://mlflow.example.com` (no trailing path required for MLflow client). |
| **`MLFLOW_S3_ENDPOINT_URL`** | S3-compatible endpoint for **artifact** uploads (e.g. public MinIO API `https://minio.example.com` or path-style host your MLflow stack uses). |
| `AWS_ACCESS_KEY_ID` / **`AWS_SECRET_ACCESS_KEY`** | **Secrets only** (not variables): S3 credentials MinIO expects — either the **root** user/password (**`MINIO_ROOT_*`** in your VM `.env`) or a **service account** from **`bash scripts/minio_create_s3_credentials.sh`** (use those values as **`AWS_ACCESS_KEY_ID`** / **`AWS_SECRET_ACCESS_KEY`** here). |
| **`AWS_DEFAULT_REGION`** | Optional; defaults to **`us-east-1`** if unset. |
| **`API_HEALTH_URL`** | Base URL of your deployed FastAPI (no `/healthz`); CI appends **`/healthz`** and checks `{"status":"ok"}`. |
| **`FEAST_UI_URL`** | Full URL of **Feast UI** (e.g. `https://feast-ui.example.com:8888`); CI issues a **GET** and expects HTTP **200**. |

**Fork pull requests:** Workflows triggered from a **fork** do **not** receive the base repository’s **secrets** or **Actions variables** (GitHub passes neither to that runner context). Those jobs therefore use workflow defaults (e.g. **`${{ github.workspace }}/mlruns`**). To use hosted endpoints on fork PRs you would need a different pattern (e.g. `pull_request_target`), which has **security trade-offs** — avoid unless you understand the risks.

**Security:** Prefer **HTTPS** endpoints, **least-privilege** S3 keys, and never commit URLs or keys in workflow YAML. Put credentials in **Secrets**; use **Variables** only for non-sensitive values.

Update **`PUBLIC_HOST`** on the VM and the GitHub URLs above whenever the instance gets a new external IP. On the VM, **`docker-compose.yml`** sets MinIO’s **`MINIO_SERVER_URL`** / **`MINIO_BROWSER_REDIRECT_URL`** from **`PUBLIC_HOST`** in **`.env`**.

## What is not in Git (by design)

See **`.gitignore`**: `.venv/`, `mlruns/`, DVC cache, generated `data/raw/*.csv`, `data/processed/*.parquet`, `predictions.csv`, `data/feast/`. CI regenerates these when the workflow runs.
