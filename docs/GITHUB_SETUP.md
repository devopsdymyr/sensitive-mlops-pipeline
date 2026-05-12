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

**If `error: remote origin already exists`:** do not run `git remote add` again — set the URL instead:

```bash
git remote set-url origin https://github.com/YOUR_USER/REPO_NAME.git
git push -u origin main
```

**Typo check:** the branch name is **`main`** (full word), not `mai`.

**SSH** (if you use keys). If **`origin` already exists**, use **`git remote set-url`** instead of **`add`**:

```bash
git remote set-url origin git@github.com:YOUR_USER/REPO_NAME.git
git push -u origin main
```

## 4) Enable GitHub Actions (after a successful push)

This repository keeps the workflow definition as **`docs/github_actions_ml_demo.yml`** so **`git push`** works with typical HTTPS tokens (no **`workflow`** OAuth scope required for the code push).

To turn on Actions:

1. On GitHub: **Settings → Actions → General** — allow workflows.
2. Locally (only when your credential has **`repo` + `workflow`**, or you will add the file on GitHub’s website):

```bash
mkdir -p .github/workflows
cp docs/github_actions_ml_demo.yml .github/workflows/ml-demo.yml
git add .github/workflows/ml-demo.yml
git commit -m "ci: add GitHub Actions ML demo workflow"
git push -u origin main
```

Or: open **GitHub → Add file → Create new file** at **`.github/workflows/ml-demo.yml`**, paste the contents of **`docs/github_actions_ml_demo.yml`**, commit on **`main`**.

3. **Actions** tab → **ML demo pipeline** → **Run workflow**.

## 5) Optional CI variables

- **`MLFLOW_TRACKING_URI`**: set as a **repository secret** if you use a hosted MLflow server; otherwise CI writes under `mlruns/` in the job workspace (ephemeral).

## What is not in Git (by design)

See **`.gitignore`**: `.venv/`, `mlruns/`, DVC cache, generated `data/raw/*.csv`, `data/processed/*.parquet`, `predictions.csv`, local Feast registry under `data/feast/`. CI regenerates these when the workflow runs.

## 6) If you still see “workflow scope” on push

That means something under **`.github/workflows/`** is still in your commits (for example an old **`ml-demo.yml`**). Remove it, commit, and push again:

```bash
git rm -f .github/workflows/ml-demo.yml 2>/dev/null || true
rmdir .github/workflows 2>/dev/null || true
git add -A
git commit -m "ci: remove workflow from git to unblock push" || true
git push -u origin main
```

Then use **section 4** to add the workflow with a PAT that has **`workflow`** scope or via the GitHub web UI.
