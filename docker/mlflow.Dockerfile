FROM python:3.10-slim

WORKDIR /srv

ENV PIP_NO_CACHE_DIR=1

RUN pip install --upgrade pip \
    && pip install --no-cache-dir "mlflow>=2.10,<3" "boto3>=1.34" "psycopg2-binary>=2.9" "minio>=7.2,<8"

COPY docker/mlflow-entrypoint.sh /mlflow-entrypoint.sh
RUN chmod +x /mlflow-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/mlflow-entrypoint.sh"]
