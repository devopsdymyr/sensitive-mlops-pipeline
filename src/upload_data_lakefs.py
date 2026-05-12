"""Upload local raw/processed datasets to a lakeFS repository (optional data layer).

Prerequisites
-------------
1. Start lakeFS (local quickstart is fine for dev only)::

       .venv/bin/python -m lakefs.quickstart

   UI and API: http://127.0.0.1:8000  (Ctrl+C stops the server)

2. Credentials: the embedded quickstart uses well-known test keys (see lakeFS docs).
   This script defaults them via environment variables compatible with ``lakefs.Client()``
   (same names as ``lakectl``).

Environment (optional overrides)
---------------------------------
- ``LAKECTL_SERVER_ENDPOINT_URL`` (default ``http://127.0.0.1:8000``)
- ``LAKECTL_CREDENTIALS_ACCESS_KEY_ID`` (quickstart default if unset)
- ``LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY`` (quickstart default if unset)
- ``LAKEFS_REPO`` (default ``mlproject-data``)
- ``LAKEFS_BRANCH`` (default ``main``)
- ``LAKEFS_STORAGE_NAMESPACE`` (default ``local://`` + repo id; must be unique per repo on the server)
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import lakefs

# Quickstart defaults (local testing only — not for production).
_DEFAULT_ENDPOINT = "http://127.0.0.1:8000"
_DEFAULT_ACCESS_KEY = "AKIAIOSFOLQUICKSTART"
_DEFAULT_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def ensure_lakectl_env_defaults() -> None:
    os.environ.setdefault("LAKECTL_SERVER_ENDPOINT_URL", _DEFAULT_ENDPOINT)
    os.environ.setdefault("LAKECTL_CREDENTIALS_ACCESS_KEY_ID", _DEFAULT_ACCESS_KEY)
    os.environ.setdefault("LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY", _DEFAULT_SECRET_KEY)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload sensitive-data pipeline artifacts to lakeFS.")
    parser.add_argument(
        "--repo",
        default=os.environ.get("LAKEFS_REPO", "mlproject-data"),
        help="lakeFS repository name",
    )
    parser.add_argument(
        "--branch",
        default=os.environ.get("LAKEFS_BRANCH", "main"),
        help="Branch to write to",
    )
    parser.add_argument(
        "--storage-namespace",
        default=os.environ.get("LAKEFS_STORAGE_NAMESPACE", ""),
        help="Storage namespace for repo creation (default: local://<repo>)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    raw_csv = root / "data" / "raw" / "sensitive_records.csv"
    processed_parquet = root / "data" / "processed" / "sensitive_features.parquet"

    if not raw_csv.is_file():
        raise SystemExit(f"Missing {raw_csv}. Run the pipeline (generate_dataset) first.")

    ensure_lakectl_env_defaults()
    namespace = args.storage_namespace or f"local://{args.repo}"

    client = lakefs.Client()
    repo = lakefs.repository(args.repo, client=client)
    repo.create(storage_namespace=namespace, default_branch=args.branch, exist_ok=True)
    branch = repo.branch(args.branch)

    raw_bytes = raw_csv.read_bytes()
    branch.object("raw/sensitive_records.csv").upload(raw_bytes, mode="wb", content_type="text/csv")

    if processed_parquet.is_file():
        branch.object("processed/sensitive_features.parquet").upload(
            processed_parquet.read_bytes(), mode="wb", content_type="application/octet-stream"
        )

    msg = (
        "Add raw sensitive_records.csv"
        if not processed_parquet.is_file()
        else "Add raw sensitive_records.csv and processed sensitive_features.parquet"
    )
    branch.commit(message=msg)

    extra = ""
    if processed_parquet.is_file():
        extra = f" and .../processed/sensitive_features.parquet ({processed_parquet.stat().st_size} bytes on disk)"

    print(f"lakeFS upload complete: lakefs://{args.repo}/{args.branch}/raw/sensitive_records.csv{extra}")


if __name__ == "__main__":
    main()
