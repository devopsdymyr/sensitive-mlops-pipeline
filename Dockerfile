# API + training image (same deps as local pipeline).
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Match `dvc.yaml` `${py}` (.venv/bin/python) inside the image without copying host `.venv` (see `.dockerignore`).
RUN mkdir -p .venv/bin \
    && ln -sf /usr/local/bin/python .venv/bin/python \
    && chmod +x docker/train-pipeline.sh \
    && mkdir -p models data/feast data/raw data/processed mlruns

EXPOSE 8080

CMD ["uvicorn", "src.serve:app", "--host", "0.0.0.0", "--port", "8080"]
