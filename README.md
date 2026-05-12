# Sensitive data risk MLOps (DPDP-style demo) — run and test locally

**Run start-to-end (test):** [End-to-end validation → TL;DR](#tldr-run-everything-copy-paste) · **Full plain-text guide:** [`README.txt`](README.txt) · **Architecture diagram (PNG):** [`docs/mlproject_pipeline_overview.png`](docs/mlproject_pipeline_overview.png) · **Same flow (editable Mermaid):** [`docs/pipeline_overview.mmd`](docs/pipeline_overview.mmd)

This repo is a **minimal end-to-end MLOps** sample for **sensitive data classification & risk scoring**: regex-style detectors (PAN, Aadhaar-like, email, phone, account-like runs, keywords) → **risk label**, **risk score**, **compliance tag**. Stack: **DVC**, **Feast**, **MLflow**, **scikit-learn**, optional **lakeFS**, **FastAPI** (`src/serve.py`), **Prometheus** (`/metrics`). **Not** certified for legal compliance — demo / governance architecture only.

### Recommended practice (map to your checklist)

| Step | In this repo |
|------|----------------|
| Dataset | `src/generate_dataset.py` → `data/raw/sensitive_records.csv` (synthetic; no real PII) |
| **Version data** | **`dvc init`** then **`dvc repro`** (or `run_pipeline.py` when `.dvc/` exists). Add a **DVC remote** for shared storage. |
| Feature store | **Feast** + `src/pii_detector.py` → `data/processed/sensitive_features.parquet` |
| Train | `src/train.py` (`SensitiveDataRiskClassifier`) |
| **Track experiments** | **MLflow** (`dpdp_sensitive_risk`), registry alias **`champion`**, signature + input example |
| Orchestrate | **`pipelines/run_pipeline.py`** or **Kubeflow** / CI |
| **Serve + monitor** | **`uvicorn src.serve:app`**; **Prometheus** scrape `monitoring/prometheus.yml`; **Grafana** dashboards (bring your own) |
| Iterate | Edit **`params.yaml`**, **`dvc repro`**, compare runs in MLflow UI |

---

## End-to-end validation

**Start → finish:** follow these steps **in order** from the **project root** (the directory that contains `requirements.txt` and `dvc.yaml`). When you finish, you should have generated data, a trained model on disk / in MLflow, batch predictions, and (optionally) a working HTTP API.

### TL;DR: run everything (copy-paste)

Use this block for a **full test from zero**; subsections **1)–9)** below add detail, expected outputs, and troubleshooting.

**1 — Environment** (from project root)

```bash
cd /path/to/mlproject
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

**2 — DVC** (so `pipelines/run_pipeline.py` runs `dvc repro`)

With Git:

```bash
git init
git add .
git commit -m "Initial project"
.venv/bin/dvc init
```

Without Git:

```bash
.venv/bin/dvc init --no-scm
```

**3 — Full pipeline**

```bash
.venv/bin/python pipelines/run_pipeline.py
```

**4 — Artifact checks**

```bash
test -f data/raw/sensitive_records.csv
test -f data/processed/sensitive_features.parquet
test -f metrics/train_metrics.json && cat metrics/train_metrics.json
test -f models/risk_label_classes.json
```

**5 — Batch inference**

```bash
.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv
head predictions.csv
```

**6 — HTTP API** (optional; use two terminals)

Terminal A:

```bash
.venv/bin/uvicorn src.serve:app --host 127.0.0.1 --port 8080
```

Terminal B:

```bash
curl -s http://127.0.0.1:8080/healthz
curl -s -X POST http://127.0.0.1:8080/v1/score \
  -H "Content-Type: application/json" \
  -d '{"text":"PAN ABCDE1234F"}'
curl -s -X POST http://127.0.0.1:8080/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"payload_id":"1","data":"Customer Name: Test\nPAN: ABCDE1234F"}'
```

Stop Uvicorn with **Ctrl+C** in terminal A when done.

**7 — MLflow UI** (optional)

```bash
.venv/bin/mlflow ui --host 127.0.0.1 --port 5000
```

Open **http://127.0.0.1:5000** and inspect runs and the registered model **`SensitiveDataRiskClassifier`** (alias **`champion`**).

**Pass criteria (quick):** step 3 exits with code **0**; step 5 produces a CSV whose header includes **`raw_text`**, **`predicted_risk_label`**, **`risk_score`**, **`compliance_tag`**; step 6 **`/healthz`** returns **`{"status":"ok"}`**.

### 1) Prerequisites

- **Python 3.10+** (`python3 --version`).
- **Shell** on Linux or macOS (on **Windows**, use the venv paths under **Step 3 — Install Python dependencies** below).

### 2) Environment

```bash
cd /path/to/mlproject   # your real path
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

### 3) DVC (recommended before first full run)

`pipelines/run_pipeline.py` runs **`dvc repro`** when **`.dvc/`** exists (data + stages cached). Otherwise it still runs the same three Python stages, but without DVC versioning.

**With Git (typical):**

```bash
git init
git add .
git commit -m "Initial project"
.venv/bin/dvc init
```

**Without Git:**

```bash
.venv/bin/dvc init --no-scm
```

If `dvc repro` fails with a Git error, ensure you committed at least once after `git init`, then run **`.venv/bin/python pipelines/run_pipeline.py`** again.

### 4) Run the full pipeline

```bash
.venv/bin/python pipelines/run_pipeline.py
```

You should see stages for **generate** → **featurize** (Feast apply) → **train** (MLflow run + registry alias **`champion`**). Warnings from Pydantic or Feast are common in this demo and can be ignored unless the process exits with an error.

### 5) Validate artifacts on disk

```bash
test -f data/raw/sensitive_records.csv && wc -l data/raw/sensitive_records.csv
test -f data/processed/sensitive_features.parquet && echo "parquet OK"
test -f metrics/train_metrics.json && cat metrics/train_metrics.json
test -f models/risk_label_classes.json && echo "classes OK"
```

**What “good” looks like**

- **`data/raw/sensitive_records.csv`**: thousands of lines (header + synthetic rows).
- **`metrics/train_metrics.json`**: JSON with at least **`accuracy`**, **`f1_macro`**, **`precision_macro`**, **`recall_macro`**, and **`run_id`**. On this synthetic dataset, accuracy is typically **very high** (often **> 0.95**); exact numbers change if data or seeds change.
- **`models/risk_label_classes.json`**: defines the classifier class order (created by training; may be gitignored but must exist locally for predict/serve).

Optional: **`.venv/bin/dvc status`** should be clean after a successful **`dvc repro`**.

### 6) Test batch inference (CSV)

```bash
.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv
head -n 10 predictions.csv
```

**Expected file shape**

- Header: **`raw_text`**, **`predicted_risk_label`**, **`risk_score`**, **`compliance_tag`**.
- **`sample_input.csv`** is built so that:
  - Plain meeting text tends toward **`LOW`** / **`CLEAR`**.
  - Lines containing PAN, “CONFIDENTIAL”, email, or phone patterns tend toward **`MEDIUM`** or **`HIGH`** with higher **`risk_score`**.

Exact labels depend on the trained model; retraining can shift boundaries slightly.

### 7) Browse MLflow (optional but useful)

From the same project root (so **`./mlruns`** is picked up):

```bash
.venv/bin/mlflow ui --host 127.0.0.1 --port 5000
```

Open **http://127.0.0.1:5000** and confirm a new run under experiment **`dpdp_sensitive_risk`** (name from **`params.yaml`**) and model **`SensitiveDataRiskClassifier`** with alias **`champion`**.

### 8) Test the FastAPI service (optional)

Terminal A:

```bash
.venv/bin/uvicorn src.serve:app --host 127.0.0.1 --port 8080
```

Terminal B (same machine):

```bash
curl -s http://127.0.0.1:8080/healthz
curl -s http://127.0.0.1:8080/v1/categories | head -c 400
curl -s -X POST http://127.0.0.1:8080/v1/score \
  -H "Content-Type: application/json" \
  -d '{"text":"CONFIDENTIAL PAN ABCDE1234F support@acme.test"}'
curl -s -X POST http://127.0.0.1:8080/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"payload_id":"12345","data":"Customer Name: Rajesh Kumar\nAadhaar Number: 1234-5678-9999\nPAN: ABCDE1234F\nPhone: +91-9876543210\nEmail: rajesh@gmail.com"}'
```

**Expected JSON (`/v1/score`)** includes **`predicted_risk_label`**, **`risk_score`**, **`compliance_tag`**, **`pii_detected`**, and **`categories`** (one entry per detector type with counts and short example snippets).

**Expected JSON (`/v1/analyze`)** — queue-style: echo **`payload_id`**, **`status`**: `"success"`, **`summary`** with **`total_pii_detected`** and ML **`risk_level`** (`LOW` / `MEDIUM` / `HIGH`), **`entities`** (`type`, `value`, demo **`confidence`** from heuristics), and **`categories`** with **`financial`**, **`identity`**, **`contact`** counts. Stop Uvicorn with **Ctrl+C** in terminal A.

### 9) Validation checklist (quick)

| Step | Command / check | Pass? |
|------|------------------|--------|
| Deps installed | `.venv/bin/python -c "import sklearn, mlflow, feast, dvc"` | no import error |
| Pipeline | `.venv/bin/python pipelines/run_pipeline.py` | exit code 0 |
| Raw data | `test -f data/raw/sensitive_records.csv` | file exists |
| Features | `test -f data/processed/sensitive_features.parquet` | file exists |
| Metrics | `test -f metrics/train_metrics.json` | file exists |
| Classes | `test -f models/risk_label_classes.json` | file exists |
| Predict | `.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv` | exit code 0; CSV has 4 columns |
| API (optional) | `curl -s http://127.0.0.1:8080/healthz` | `{"status":"ok"}` |

**Architecture diagram (this use case):** [`docs/mlproject_pipeline_overview.png`](docs/mlproject_pipeline_overview.png) · Mermaid: [`docs/pipeline_overview.mmd`](docs/pipeline_overview.mmd).

### Copy-paste: minimal path (experienced users)

```bash
cd /path/to/mlproject
python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt
.venv/bin/dvc init --no-scm   # or git init + commit + dvc init — see step 3 above
.venv/bin/python pipelines/run_pipeline.py
.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv && head predictions.csv
```

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
| `data/raw/` | Synthetic sensitive-text CSV (`sensitive_records.csv`) |
| `data/processed/` | Parquet with regex features + labels for Feast / training |
| `src/` | `generate_dataset.py`, `pii_detector.py`, `featurize.py`, `train.py`, `predict.py`, `serve.py`, `upload_data_lakefs.py` |
| `pipelines/run_pipeline.py` | Runs all stages in order |
| `metrics/train_metrics.json` | Metrics file (also tracked by DVC as metrics) |
| `params.yaml` | Hyperparameters and MLflow names |
| `dvc.yaml` | DVC pipeline definition |
| `sample_input.csv` | Example rows for batch inference |
| `docs/mlproject_pipeline_overview.png` | End-to-end pipeline diagram (updated for MLflow bundle + registry) |
| `docs/pipeline_overview.mmd` | Same diagram as Mermaid (easy to edit and re-export PNG) |

---

## Model format and MLflow Model Registry

Training (`src/train.py`) calls **`mlflow.sklearn.log_model(..., artifact_path="model")`**. That does **not** write a single hand-rolled `.pkl` in the project root; it writes a standard **MLflow Model** directory for the sklearn flavor.

**What is on disk after a training run (local tracking)**

Under **`mlruns/<experiment_id>/<run_id>/artifacts/model/`** you typically get:

| File / folder | Role |
|---------------|------|
| **`MLmodel`** | YAML descriptor: flavor (`sklearn`), `sklearn_model` path, signature, etc. |
| **`model.pkl`** | **Pickled** `sklearn` estimator (this is the actual learned weights for the sklearn flavor). |
| **`conda.yaml`** / **`python_env.yaml`**, **`requirements.txt`** | Environment hints for reproducible loads. |
| **`input_example.json`** (optional) | Example saved from training. |

So the answer to “is it `.pkl`?”: **yes, the sklearn object is pickled as `model.pkl`, but only as part of the MLflow Model bundle**, not as the only artifact you should think about. Loading is done via **`mlflow.sklearn.load_model("runs:/.../model")`** or **`models:/SensitiveDataRiskClassifier@champion`**, which reads that bundle.

**Separate file in this repo (not the registry bundle)**

- **`models/risk_label_classes.json`** — written by training for **class index → label** mapping at **`predict.py`** / **`serve.py`**. It is **not** the sklearn weight file.

**What the Model Registry stores**

The **MLflow Model Registry** holds **registered model metadata**: name (**`SensitiveDataRiskClassifier`** from `params.yaml`), **version** numbers, **tags**, and a **`source`** URI pointing at a run’s logged **`model`** folder (for example `runs:/<run_id>/model` or an equivalent file URI). The **alias** **`@champion`** points one registered **version** at the “current production” bundle. **Large binaries stay in the artifact store** (`mlruns/.../artifacts/` locally, or your remote artifact store if configured); the registry row is the **pointer + governance metadata**, not a second copy of the weights in a different custom format.

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

For a **single ordered path** with artifact checks and pass criteria, see **[End-to-end validation](#end-to-end-validation)** first.

You can use **either** the orchestration script **or** DVC.

### Option A — Orchestration script (uses **DVC** when initialized)

From the project root:

```bash
.venv/bin/python pipelines/run_pipeline.py
```

- If **`.dvc/`** exists (after `dvc init`), this runs **`dvc repro`** so **data and pipeline outputs are versioned in the DVC cache** (best practice).
- If DVC is not initialized yet, it runs the three Python stages only and prints a hint to run `dvc init`.

**What you should see**

1. `Generate synthetic data` — writes `data/raw/sensitive_records.csv`.
2. `Featurize + Feast apply` — writes `data/processed/sensitive_features.parquet` and runs `feast apply`.
3. `Train + MLflow registry` — trains `SensitiveDataRiskClassifier`, logs to MLflow, sets alias **`champion`**, writes `metrics/train_metrics.json` and `models/risk_label_classes.json`.

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

**Expected columns and sample behavior** are summarized under **[End-to-end validation](#end-to-end-validation)** (step 6 there).

After training, defaults come from **`params.yaml`**: **`SensitiveDataRiskClassifier`** + alias **`champion`**.

From the project root:

```bash
.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv
```

Input CSV must include a **`raw_text`** column. Output adds **`predicted_risk_label`**, **`risk_score`** (0–100 heuristic), and **`compliance_tag`** (`CLEAR` / `DPDP_REVIEW` / `BLOCK_OR_REDACT`).

This loads **`models:/SensitiveDataRiskClassifier@champion`** unless you pass **`--model-uri`**.

**Check the output:**

```bash
cat predictions.csv
# or: head predictions.csv
```

You should see **`raw_text`** plus **`predicted_risk_label`**, **`risk_score`**, and **`compliance_tag`**.

**Custom input:** any CSV with a **`raw_text`** column (one row per document / log line to score).

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

**REST scoring (FastAPI + Prometheus metrics)**

```bash
.venv/bin/uvicorn src.serve:app --host 127.0.0.1 --port 8080
```

- `POST /v1/analyze` with JSON `{"payload_id": "...", "data": "..."}` — queue-style response: **`summary`** (`total_pii_detected`, **`risk_level`** from the classifier), **`entities`** (e.g. `PERSON_NAME`, `AADHAAR`, `PAN`, `PHONE`, `EMAIL` with demo confidences), **`categories`** (`financial`, `identity`, `contact` counts).  
- `POST /v1/score` with JSON `{"text": "..."}` — returns `predicted_risk_label`, `risk_score`, `compliance_tag`, aggregate `pii_detected`, and `categories` (per-type: `PAN`, `AADHAAR`, `EMAIL`, `PHONE`, `ACCOUNT_NUMBER`, `SENSITIVE_KEYWORD` with counts and short example snippets).  
- `GET /v1/categories` — static list of those category keys and descriptions.  
- `GET /metrics` for Prometheus  
- `GET /healthz`  

**Optional MLflow model HTTP server**

```bash
.venv/bin/mlflow models serve -m "models:/SensitiveDataRiskClassifier@champion" --host 127.0.0.1 -p 5001 --no-conda
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
| **`Missing ... sensitive_records.csv` / featurize errors** | Run **`generate_dataset`**: `.venv/bin/python src/generate_dataset.py` or the full `run_pipeline.py` / `dvc repro`. |
| **DVC errors about Git** | Run `git init` and commit files, **or** use `dvc init --no-scm`. |
| **`output 'data/raw/...csv' is already tracked by SCM (Git)`** | Data outputs must be **ignored by Git** so DVC can own them. Run: `git rm -r --cached data/raw/sensitive_records.csv data/processed/sensitive_features.parquet` (ignore errors if a path was never tracked), then `git commit -m "Stop tracking data outputs; DVC owns them"`. Ensure `.gitignore` lists `data/raw/*.csv` and `data/processed/*.parquet`, then `dvc repro` again. |
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

**Optional Python `lakefs://` paths for pandas:** install **`lakefs-spec`** (`pip install lakefs-spec`) and use URIs like `lakefs://mlproject-data/main/raw/sensitive_records.csv` in `pandas.read_csv` (see [lakeFS-spec quickstart](https://lakefs-spec.org/latest/quickstart/)).

---

## Quick copy-paste checklist (Linux/macOS)

End-to-end detail: **[End-to-end validation](#end-to-end-validation)** — fastest path: **[TL;DR (copy-paste)](#tldr-run-everything-copy-paste)**.

```bash
cd /path/to/mlproject
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
git init && git add . && git commit -m "init" && .venv/bin/dvc init   # or: .venv/bin/dvc init --no-scm
.venv/bin/python pipelines/run_pipeline.py
test -f metrics/train_metrics.json && cat metrics/train_metrics.json
.venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv
head predictions.csv
.venv/bin/mlflow ui --host 127.0.0.1 --port 5000
```

If that completes (pipeline exit code 0, metrics file present, predictions CSV has four columns), your local environment and pipeline are validated. For HTTP checks, continue with **step 8** in the validation section. Diagram: **`docs/mlproject_pipeline_overview.png`** (Mermaid source: **`docs/pipeline_overview.mmd`**).
