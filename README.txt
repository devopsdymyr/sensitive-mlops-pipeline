================================================================================
  SENSITIVE DATA CLASSIFICATION & RISK SCORING — README.txt
================================================================================

Architecture diagram (PNG, matches this use case):
    docs/mlproject_pipeline_overview.png
  Editable Mermaid source (same flow, model.pkl inside MLflow bundle):
    docs/pipeline_overview.mmd


LEGAL / SAFETY NOTICE
---------------------
This project uses SYNTHETIC text and heuristic regexes for an MLOps demo only.
It is NOT certified legal or compliance software, a production security scanner,
or a substitute for professional review.
Do not rely on it for production compliance, consent decisions, or legal
defensibility without expert review and a proper control framework.


PII DETECTION (single module)
-----------------------------
All pattern matching, ML features, heuristic risk score, and compliance tags
live in:  src/pii_detector.py

Public helpers:
  - detect_pii_matches(text)     matched substrings per category
  - extract_features(text)     numeric vector for Feast / sklearn
  - featurize_dataframe(df)    batch features from column raw_text
  - analyze_text(text)         one-shot: features + risk_score + risk_label + compliance_tag (+ optional matches)
  - compliance_tag_for_risk_label(label)   map LOW/MEDIUM/HIGH -> CLEAR / DPDP_REVIEW / BLOCK_OR_REDACT

Other stages call these only — they do not reimplement PII rules.


MODEL FILE FORMAT (train.py -> MLflow)
--------------------------------------
Training uses mlflow.sklearn.log_model(..., artifact_path="model").
The saved object is an MLflow *Model* directory, not a lone .pkl in the repo root.
Under mlruns/<exp>/<run>/artifacts/model/ you typically see:
  MLmodel          YAML descriptor (flavor, paths, signature)
  model.pkl        pickled sklearn estimator (weights live here)
  conda.yaml / python_env.yaml / requirements.txt   env metadata

The Model Registry stores name, version, tags, alias @champion, and a *source* URI
pointing at that logged folder; large files stay in the artifact store (mlruns
or your remote backend). Separately, models/risk_label_classes.json maps class
indices to LOW/MEDIUM/HIGH for predict.py and serve.py.

See README.md section "Model format and MLflow Model Registry" for full detail.


--------------------------------------------------------------------------------
  END-TO-END MLOPS FLOW (recommended stack)
--------------------------------------------------------------------------------

  Raw CSV / JSON / logs (synthetic here)
           |
           v
      [ Data versioning ]
           |
          DVC   (dvc.yaml stages, dvc.lock, optional remote)
           |
           v
  [ Feature engineering: regex + simple NLP signals ]
           |
          Feast (offline feature table + feature_repo/)
           |
           v
      [ Model training ]
           |
    scikit-learn LogisticRegression  (risk_label: LOW / MEDIUM / HIGH)
           |
           v
      [ Experiment + registry ]
           |
    MLflow  (params, metrics, model signature, registry alias "champion")
           |
           v
      [ Batch inference ]
           |
    predict.py  (CSV with raw_text column)
           |
           v
      [ Online serving + metrics ]
           |
    FastAPI src/serve.py  (/v1/analyze, /v1/score, /v1/categories, /metrics, /healthz)
           |
           v
      [ Monitoring ]
           |
    Prometheus (monitoring/prometheus.yml)  -->  Grafana (self-hosted dashboards)


--------------------------------------------------------------------------------
  DVC PIPELINE STAGES (dvc.yaml)
--------------------------------------------------------------------------------

  1) generate_data
     cmd:  .venv/bin/python src/generate_dataset.py
     out:  data/raw/sensitive_records.csv
     Role: Synthetic records with raw_text + ground-truth risk_label / score / tag.

  2) featurize
     cmd:  .venv/bin/python src/featurize.py
     out:  data/processed/sensitive_features.parquet
     Role: Regex feature columns via pii_detector.py; feast apply.

  3) train
     cmd:  .venv/bin/python src/train.py
     out:  metrics/train_metrics.json, models/risk_label_classes.json (gitignored)
     Role: Feast get_historical_features; train classifier; MLflow log + registry.

  Run:  .venv/bin/dvc repro
     or: .venv/bin/python pipelines/run_pipeline.py


--------------------------------------------------------------------------------
  OUTPUTS PER REQUEST (design target)
--------------------------------------------------------------------------------

  risk_score          Float 0-100 (heuristic from signals; see pii_detector.py)
  predicted_risk_label  LOW | MEDIUM | HIGH (classifier)
  compliance_tag      CLEAR | DPDP_REVIEW | BLOCK_OR_REDACT (mapping from label)
  pii_detected        Boolean: any regex category matched in the payload text
  categories          Per-category rows (PAN, AADHAAR, EMAIL, PHONE, ACCOUNT_NUMBER,
                      SENSITIVE_KEYWORD): flags, match_count, example_snippets (capped)


--------------------------------------------------------------------------------
  TOOLS IN THIS REPOSITORY
--------------------------------------------------------------------------------

  Git, DVC, Feast, scikit-learn, pandas, pyarrow, MLflow, lakeFS (optional),
  FastAPI, Uvicorn, prometheus_client, GitLab CI example (.gitlab-ci.yml).


--------------------------------------------------------------------------------
  VALIDATE FROM START TO END (summary)
--------------------------------------------------------------------------------

  Full step-by-step use case + how it works + tests: README.md (single flow).

  From project root:
    python3 -m venv .venv
    .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt
    git init && git add . && git commit -m init && .venv/bin/dvc init
      OR:  .venv/bin/dvc init --no-scm
    .venv/bin/python pipelines/run_pipeline.py
    test -f data/raw/sensitive_records.csv
    test -f data/processed/sensitive_features.parquet
    test -f metrics/train_metrics.json && cat metrics/train_metrics.json
    test -f models/risk_label_classes.json
    .venv/bin/python src/predict.py --input sample_input.csv --output predictions.csv
    head predictions.csv

  Pass: pipeline exit 0; predictions header has raw_text, predicted_risk_label,
        risk_score, compliance_tag; train_metrics.json has accuracy and f1_macro.


--------------------------------------------------------------------------------
  QUICK COMMANDS
--------------------------------------------------------------------------------

  One-shot full demo (venv + deps + DVC if needed + pipeline + predict):
    bash scripts/run_full_demo.sh
    # or:  make demo

  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python pipelines/run_pipeline.py --full-demo

  .venv/bin/mlflow ui --host 127.0.0.1 --port 5000

  .venv/bin/uvicorn src.serve:app --host 127.0.0.1 --port 8080
  # curl -s http://127.0.0.1:8080/v1/categories | jq .
  # curl -s -X POST http://127.0.0.1:8080/v1/score -H "Content-Type: application/json" \
  #   -d '{"text":"test PAN ABCDE1234F"}' | jq .

  Diagram: docs/mlproject_pipeline_overview.png

  # If Feast project config changed name, remove data/feast/ once then re-featurize.

--------------------------------------------------------------------------------
  GitHub vs GitLab push + CI: README.md section "Git hosting & CI".
================================================================================
