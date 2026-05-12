# Convenience targets (GNU Make). From project root: `make demo`

.PHONY: demo pipeline full-demo docker-build docker-up docker-train public-test

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
