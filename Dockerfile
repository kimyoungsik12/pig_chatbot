# syntax=docker/dockerfile:1

FROM python:3.10-slim

# Prevents Python from writing .pyc files and buffers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application code
COPY . .

# (Optional) download embedding model during build
ARG INCLUDE_MODEL=false
ARG MODEL_REPO_ID=jhgan/ko-sroberta-multitask
ARG IMAGE_MODEL_PATH=/models/ko-sroberta
RUN if [ "${INCLUDE_MODEL}" = "true" ]; then \
      echo "Downloading model ${MODEL_REPO_ID} to ${IMAGE_MODEL_PATH}"; \
      pip install --no-cache-dir "huggingface_hub>=0.23" "sentence-transformers>=3.2"; \
      python - <<'PY' \
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="${MODEL_REPO_ID}",
    local_dir="${IMAGE_MODEL_PATH}",
    local_dir_use_symlinks=False,
)
PY
    ; else \
      echo "Skipping model download (INCLUDE_MODEL=${INCLUDE_MODEL})"; \
    fi

# Run with a non-root user
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Default command: FastAPI server
CMD ["python", "main.py", "api"]
