# Iris MLOps sample — run and test locally

This project is a **minimal end-to-end MLOps** demo: **DVC** (data + pipeline), **Feast** (feature definitions), **MLflow** (experiments + model registry), **scikit-learn** training, and a **small Python orchestrator** (you can swap in Kubeflow Pipelines later).

### Recommended practice (map to your checklist)

| Step | In this repo |
|------|----------------|
| Simple dataset (Iris) | `src/download_data.py` → `data/raw/iris.csv` |
| **Version data** | **`dvc init`** then **`dvc repro`** (or `run_pipeline.py`, which calls `dvc repro` when `.dvc/` exists). Add a **DVC remote** for shared storage. |
| Feature store | **Feast** in `feature_repo/`; materialized table in `data/processed/` |
| Train sklearn | `src/train.py` |
| **Track experiments** | **MLflow**: params, metrics, **signature** + **input example** on the logged model |
| Orchestrate | **`pipelines/run_pipeline.py`** (or **Kubeflow** calling the same commands) |
| **Registry + deploy** | **`mlflow.model_alias`** `champion` on the latest version; **`predict.py`** loads `models:/…@champion`; optional **`mlflow models serve`** |
| Iterate | Edit **`params.yaml`**, rerun pipeline; compare runs in MLflow UI |

---

## What you need

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** (3.10 tested) | `python3 --version` |
| **Internet** | First-time `pip install` downloads packages |
| **Git** (optional) | Recommended if you use **DVC** with a normal workflow |

On **Debian/Ubuntu**, the system Python often has **no `pip`** and **`ensurepip` is disabled**. That is expected. This guide uses a **virtual environment**; the venv includes **`pip`** even when the system does not.

If creating a venv fails with a message about `ensurepip`, install the venv package (needs admin once):

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
```

---

## Project layout (quick reference)

| Path | Role |
|------|------|
| `data/raw/` | Raw Iris CSV from scikit-learn |
| `data/processed/` | Parquet table for Feast + training |
| `data/feast/` | Feast local registry and SQLite online store (generated) |
| `feature_repo/` | Feast repo (`feature_store.yaml`, `repo.py`) |
| `src/` | `download_data.py`, `featurize.py`, `train.py`, `predict.py` |
| `pipelines/run_pipeline.py` | Runs all stages in order |
| `metrics/train_metrics.json` | Metrics file (also tracked by DVC as metrics) |
| `params.yaml` | Hyperparameters and MLflow names |
| `dvc.yaml` | DVC pipeline definition |
| `sample_input.csv` | Example rows for batch inference |

---

## Step-by-step: first-time setup

Do everything from the **project root** (the folder that contains `requirements.txt`).

### Step 1 — Go to the project directory

```bash
cd /path/to/mlproject
```

(Replace `/path/to/mlproject` with the real path where you cloned or copied this repo.)

### Step 2 — Create a virtual environment

```bash
python3 -m venv .venv
```

- This creates `.venv/` in the project folder.
- **Do not** rely on `pip` on the host until the venv exists; use the venv’s pip (next step).

### Step 3 — Install Python dependencies

**Linux / macOS** (use the venv’s `pip` explicitly — works even when `pip` is not on your PATH):

```bash
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

**Windows** (Command Prompt / PowerShell):

```bash
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

Wait until all packages finish installing (Feast, MLflow, DVC, scikit-learn, etc.).

### Step 4 — (Optional) Activate the virtual environment

Activation is optional if you always call `.venv/bin/python` and `.venv/bin/pip` as below.

**Linux / macOS:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
.venv\Scripts\activate
```

After activation, `python` and `pip` point at the venv.

---

## Step-by-step: run the full pipeline

You can use **either** the orchestration script **or** DVC.

### Option A — Orchestration script (uses **DVC** when initialized)

From the project root:

```bash
.venv/bin/python pipelines/run_pipeline.py
```

- If **`.dvc/`** exists (after `dvc init`), this runs **`dvc repro`** so **data and pipeline outputs are versioned in the DVC cache** (best practice).
- If DVC is not initialized yet, it runs the three Python stages only and prints a hint to run `dvc init`.

**What you should see**

1. `Download raw data` — writes `data/raw/iris.csv` (150 rows).
2. `Featurize + Feast apply` — writes `data/processed/iris_features.parquet` and runs `feast apply` (creates/updates `data/feast/`).
3. `Train + MLflow registry` — trains a model, logs to MLflow under experiment `iris_mlops`, registers `IrisClassifier`, writes `metrics/train_metrics.json`, and moves the latest version to **Production** when the registry allows it.

You may see **warnings** from Feast, Pydantic, or MLflow; they are usually harmless for this sample.

### Option B — DVC (`dvc repro`)

DVC expects either a **Git** repository or a one-time **no-SCM** init.

**If you use Git (recommended):**

```bash
git init
git add .
git commit -m "Initial project"
dvc init
dvc repro
```

**If you do not want Git:**

```bash
dvc init --no-scm
dvc repro
```

Use the same Python environment for `dvc` as for the project (after `source .venv/bin/activate`, or install DVC only inside the venv — `requirements.txt` already includes `dvc`).

---

## Step-by-step: test inference (batch predict)

After a successful training run, the default model URI comes from **`params.yaml`**: registered name **`IrisClassifier`** and alias **`champion`** (MLflow’s modern alternative to legacy “Production” stages).

From the project root:

```bash
.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv
```

This loads **`models:/IrisClassifier@champion`** unless you pass **`--model-uri`**.

**Check the output:**

```bash
cat predictions.csv
# or: head predictions.csv
```

You should see the original feature columns plus a **`prediction`** column (class indices `0`, `1`, `2`).

**Custom input:** any CSV with columns `sepal_length`, `sepal_width`, `petal_length`, `petal_width` (header row required).

**Custom model URI:**

```bash
.venv/bin/python src/predict.py --input sample_input.csv --output out.csv --model-uri "runs:/<run_id>/model"
```

Use a run id from the MLflow UI if you prefer not to use the registry URI.

---

## Step-by-step: browse experiments (MLflow UI)

From the project root (so MLflow finds `./mlruns`):

```bash
.venv/bin/mlflow ui --host 127.0.0.1 --port 5000
```

Open **http://127.0.0.1:5000** in a browser. Inspect runs, parameters, metrics, and the registered model.

Stop the server with `Ctrl+C`.

**Optional REST serving** (separate terminal, after a model exists):

```bash
.venv/bin/mlflow models serve -m "models:/IrisClassifier@champion" --host 127.0.0.1 -p 5001 --no-conda
```

---

## Step-by-step: change parameters and rerun

1. Edit **`params.yaml`** (for example `train.C` or `train.max_iter`).
2. Run again:

   ```bash
   .venv/bin/python pipelines/run_pipeline.py
   ```

   or `dvc repro`.

MLflow records a new run; DVC reruns stages when dependencies or recorded params change.

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| **`Command 'pip' not found'`** | Do not use system `pip`. Create `.venv` and run **`.venv/bin/pip install -r requirements.txt`**. |
| **`python3: No module named venv'`** or venv creation fails | Install `python3-venv` (see “What you need” above). |
| **`feast apply failed`** | Ensure Step 3 finished. Run **`.venv/bin/pip install -r requirements.txt`**. This repo resolves **`.venv/bin/feast`** automatically so you do **not** need `feast` on your system PATH. |
| **Feast errors after upgrading `entity_key_serialization_version`** | Remove `data/feast/` and run the featurize stage again so the registry is recreated. |
| **`Missing ... iris.csv` / featurize errors** | Run **download** first: `.venv/bin/python src/download_data.py` or the full `run_pipeline.py`. |
| **DVC errors about Git** | Run `git init` and commit files, **or** use `dvc init --no-scm`. |
| **`output 'data/raw/iris.csv' is already tracked by SCM (Git)`** | Data outputs must be **ignored by Git** so DVC can own them. Run: `git rm -r --cached data/raw/iris.csv data/processed/iris_features.parquet` (ignore errors if a path was never tracked), then `git commit -m "Stop tracking data outputs; DVC owns them"`. Ensure `.gitignore` lists `data/raw/*.csv` and `data/processed/*.parquet`, then `dvc repro` again. |
| **Predict cannot load registry model** | Run training once. Default URI is `models:/<name>@champion` from `params.yaml` (`registered_model_name`, `model_alias`). Use `--model-uri runs:/<run_id>/model` if needed. |

---

## Iterating and expanding

- **DVC remotes:** add `dvc remote add` to push data and cache to cloud storage.
- **lakeFS (optional):** Git-like branches/commits over object storage; see **Optional: lakeFS** below.
- **Kubeflow:** replace `pipelines/run_pipeline.py` with a KFP pipeline that runs the same three commands in containers.
- **Feast online serving:** add `feast materialize` / feature server when you need real-time features.

---

## Optional: lakeFS for versioned data

**What it is:** [lakeFS](https://lakefs.io/) adds branching, commits, and merges on top of your data in S3 (or a local blockstore in dev). It complements **Git** (code) and can sit **under** DVC as the actual object store (DVC’s S3 remote can target a lakeFS S3 gateway in real deployments).

**Install (already in `requirements.txt`):**

```bash
.venv/bin/pip install lakefs
```

**1 — Start a local lakeFS (quickstart, dev only)** — in a **separate terminal**, from the project root:

```bash
.venv/bin/python -m lakefs.quickstart
```

Leave it running. Open **http://127.0.0.1:8000** for the lakeFS web UI. This mode is **not** for production.

**2 — Produce local files** (if you have not already):

```bash
.venv/bin/python pipelines/run_pipeline.py
```

**3 — Upload `data/raw/` (and processed parquet if present) to lakeFS:**

```bash
.venv/bin/python src/upload_data_lakefs.py
```

Defaults assume the quickstart server on **http://127.0.0.1:8000** and the usual quickstart access keys (see [lakeFS quickstart / launch](https://docs.lakefs.io/latest/quickstart/)). If login fails, copy the access key and secret from the lakeFS UI or your `~/.lakectl.yaml`, then export:

```bash
export LAKECTL_SERVER_ENDPOINT_URL="http://127.0.0.1:8000"
export LAKECTL_CREDENTIALS_ACCESS_KEY_ID="..."
export LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY="..."
```

Optional: `LAKEFS_REPO`, `LAKEFS_BRANCH`, `LAKEFS_STORAGE_NAMESPACE` (see `src/upload_data_lakefs.py`).

**4 — DVC + lakeFS (typical pattern):** keep **small pointers** in Git/DVC; point a **DVC S3 remote** at your lakeFS S3 API endpoint and bucket (repo/branch path) using lakeFS’s S3-compatible gateway. Follow [lakeFS + DVC](https://docs.lakefs.io/latest/integrations/dvc/) and [DVC S3 remotes](https://dvc.org/doc/user-guide/data-management/remote-storage/amazon-s3) for your environment.

**Optional Python `lakefs://` paths for pandas:** install **`lakefs-spec`** (`pip install lakefs-spec`) and use URIs like `lakefs://mlproject-data/main/raw/iris.csv` in `pandas.read_csv` (see [lakeFS-spec quickstart](https://lakefs-spec.org/latest/quickstart/)).

---

## Quick copy-paste checklist (Linux/macOS)

```bash
cd /path/to/mlproject
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python pipelines/run_pipeline.py
.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv
head predictions.csv
```

If that completes, your local environment is set up correctly.
