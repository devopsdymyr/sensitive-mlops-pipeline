# Convenience targets (GNU Make). From project root: `make demo`

.PHONY: demo pipeline

demo:
	bash scripts/run_full_demo.sh

pipeline:
	.venv/bin/python pipelines/run_pipeline.py

full-demo:
	.venv/bin/python pipelines/run_pipeline.py --full-demo
