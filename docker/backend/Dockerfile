# ╔══════════════════════════════════════════════════════════════╗
# ║  Can I Trust? — FastAPI Backend Dockerfile                   ║
# ║  Multi-stage: builder → development → production             ║
# ╚══════════════════════════════════════════════════════════════╝

# ── Stage 1: Python dependency builder ─────────────────────────
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Development image ──────────────────────────────────
FROM python:3.11-slim AS development

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app
RUN useradd -m -u 1000 appuser && \
    mkdir -p logs uploads ml_models && \
    chmod -R 777 logs uploads ml_models && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ── Stage 3: Production image ───────────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="Can I Trust Team" version="1.0.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng libpq5 curl \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

COPY --from=builder /install /usr/local

WORKDIR /app
RUN useradd -m -u 1000 appuser && \
    mkdir -p logs uploads ml_models && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Gunicorn + Uvicorn workers for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]