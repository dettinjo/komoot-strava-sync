# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies first (layer cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Data directory — expected to be mounted as a Docker volume
VOLUME ["/data"]

ENV DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "app.main"]
