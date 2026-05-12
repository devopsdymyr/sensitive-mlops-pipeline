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
2. **Actions** → **ML demo pipeline** — runs on **push** / **pull_request** to **`main`**, or **Run workflow** (manual).
3. Optional: add **repository secrets** so CI uses your **hosted** MLflow, MinIO (S3 API), and public HTTP checks (see table below).

The workflow file is **`.github/workflows/ml-demo.yml`**. A copy for reference lives at **`docs/github_actions_ml_demo.yml`** (keep them in sync when editing).

## 5) Optional CI secrets (public / hosted endpoints)

Configure under **Settings → Secrets and variables → Actions** (same names). If a secret is **unset**, the job falls back to local behavior (e.g. MLflow under `$GITHUB_WORKSPACE/mlruns`).

| Secret | Purpose |
|--------|---------|
| **`MLFLOW_TRACKING_URI`** | Tracking server URL, e.g. `https://mlflow.example.com` (no trailing path required for MLflow client). |
| **`MLFLOW_S3_ENDPOINT_URL`** | S3-compatible endpoint for **artifact** uploads (e.g. public MinIO API `https://minio.example.com` or path-style host your MLflow stack uses). |
| **`AWS_ACCESS_KEY_ID`** / **`AWS_SECRET_ACCESS_KEY`** | Credentials MinIO/S3 expects for artifact store (often same as MinIO root in dev; use scoped keys in production). |
| **`AWS_DEFAULT_REGION`** | Optional; defaults to **`us-east-1`** in the workflow if unset. |
| **`API_HEALTH_URL`** | Base URL of your deployed FastAPI (no `/healthz`); CI appends **`/healthz`** and checks `{"status":"ok"}`. |
| **`FEAST_UI_URL`** | Full URL of **Feast UI** (e.g. `https://feast-ui.example.com:8888`); CI issues a **GET** and expects HTTP **200**. |

**Fork pull requests:** GitHub does **not** expose your upstream secrets to workflows running from a forked repo, so those jobs use **local** MLflow only unless you use a different design (e.g. `pull_request_target`, which has security trade-offs).

**Security:** Prefer **HTTPS** endpoints, **least-privilege** S3 keys, and do not commit URLs or keys into the workflow YAML—only via secrets.

### Example values (this VM’s public IP)

If Docker Compose is up on the same host as **`PUBLIC_HOST` in `.env.docker.example`** (default **34.100.137.211**) and the firewall allows the ports above, set secrets to:

| Secret | Example value |
|--------|-----------------|
| `MLFLOW_TRACKING_URI` | `http://34.100.137.211:5000` |
| `MLFLOW_S3_ENDPOINT_URL` | `http://34.100.137.211:9000` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Same as **`MINIO_ROOT_USER`** / **`MINIO_ROOT_PASSWORD`** in your `.env` (never commit `.env`). |
| `API_HEALTH_URL` | `http://34.100.137.211:8080` |
| `FEAST_UI_URL` | `http://34.100.137.211:8888` |

Update the IP whenever the instance gets a new external address. On the VM itself, **`docker-compose.yml`** sets MinIO’s **`MINIO_SERVER_URL`** / **`MINIO_BROWSER_REDIRECT_URL`** from **`PUBLIC_HOST`** in **`.env`** (no separate MinIO URL secrets needed on the host).

## What is not in Git (by design)

See **`.gitignore`**: `.venv/`, `mlruns/`, DVC cache, generated `data/raw/*.csv`, `data/processed/*.parquet`, `predictions.csv`, `data/feast/`. CI regenerates these when the workflow runs.
