# Athena-SDA — reproducible backend pipeline image.
# Frontend is built separately (src/frontend); see src/frontend/README.md.
#
#   docker build -t athena-sda .
#   docker run --rm -v "$PWD/data:/app/data" -v "$PWD/models:/app/models" \
#       athena-sda python scripts/run_anomaly_monitor.py status

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps: gcc/curl for wheels that may compile (xgboost/scikit-learn ship
# wheels for manylinux, so this is a safety net only).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Code + schemas only. data/ and models/ are bind-mounted at runtime.
COPY src ./src
COPY scripts ./scripts
COPY schemas ./schemas
COPY docs ./docs
COPY pyproject.toml ./

# Sidecar must listen on all interfaces inside compose.
ENV ATHENA_BIND=0.0.0.0

# Run the CLI directly (idempotent, reversible); override CMD as needed.
ENTRYPOINT ["python", "scripts/run_anomaly_monitor.py"]
CMD ["status"]
