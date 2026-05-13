# Convenience targets (GNU Make). From project root: `make demo`

.PHONY: demo pipeline full-demo docker-build docker-up docker-train public-test local-test verify ci-e2e minio-keys

demo:
	bash scripts/run_full_demo.sh

pipeline:
	.venv/bin/python pipelines/run_pipeline.py

full-demo:
	.venv/bin/python pipelines/run_pipeline.py --full-demo

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-train:
	docker compose --profile train run --rm train
	docker compose restart app

# After compose is up: hit API / MLflow / Feast / MinIO on PUBLIC_HOST (see .env.docker.example).
public-test:
	bash scripts/test_public_endpoints.sh

local-test:
	bash scripts/local_test.sh

verify:
	.venv/bin/python scripts/verify_outputs.py

ci-e2e:
	bash scripts/ci_e2e.sh

# Mint MinIO service-account S3 keys (requires: docker compose up -d minio).
minio-keys:
	bash scripts/minio_create_s3_credentials.sh
