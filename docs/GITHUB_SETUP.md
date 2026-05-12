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
2. **Actions** → **ML demo pipeline** → **Run workflow** (manual dispatch).
3. Optional: set secret **`MLFLOW_TRACKING_URI`** for a shared MLflow server.

The workflow file is **`.github/workflows/ml-demo.yml`**. A copy for reference lives at **`docs/github_actions_ml_demo.yml`** (keep them in sync when editing).

## 5) Optional CI variables

- **`MLFLOW_TRACKING_URI`**: repository **secret** for hosted MLflow; otherwise the job uses `file://…/mlruns` under the workspace.

## What is not in Git (by design)

See **`.gitignore`**: `.venv/`, `mlruns/`, DVC cache, generated `data/raw/*.csv`, `data/processed/*.parquet`, `predictions.csv`, `data/feast/`. CI regenerates these when the workflow runs.
