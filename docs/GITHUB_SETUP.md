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

**SSH** (if you use keys):

```bash
git remote add origin git@github.com:YOUR_USER/REPO_NAME.git
git push -u origin main
```

## 4) Enable GitHub Actions

1. On GitHub: **Settings → Actions → General**.
2. Under **Workflow permissions**, allow **Read and write** (or at least **Read** so workflows can run).
3. **Actions** tab → **ML demo pipeline** → **Run workflow** to execute the full pipeline in CI.

## 5) Optional CI variables

- **`MLFLOW_TRACKING_URI`**: set as a **repository secret** if you use a hosted MLflow server; otherwise CI writes under `mlruns/` in the job workspace (ephemeral).

## What is not in Git (by design)

See **`.gitignore`**: `.venv/`, `mlruns/`, DVC cache, generated `data/raw/*.csv`, `data/processed/*.parquet`, `predictions.csv`, local Feast registry under `data/feast/`. CI regenerates these when the workflow runs.
