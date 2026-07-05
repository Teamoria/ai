# ──────────────────────────────────────────────────
# Teamoria AI Service — Production Dockerfile
# Multi-stage build for a slim, secure image
# ──────────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps needed to compile some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a virtual-env so we can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────
FROM python:3.12-slim AS runtime

# Labels
LABEL maintainer="Teamoria <team@taqat.academy>"
LABEL description="Teamoria AI Service — FastAPI"

# System runtime deps (psycopg needs libpq, tesseract for OCR, ffmpeg for media)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        ffmpeg \
        tesseract-ocr \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual-env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy application code
COPY ai-service/ ./ai-service/
COPY Procfile ./

# Create temp upload dir & give ownership
RUN mkdir -p /app/tmp/uploads && \
    chown -R appuser:appuser /app

USER appuser

# Default port — overridable via $PORT env var
ENV PORT=8000
EXPOSE ${PORT}

# Health check (matches the /health endpoint in main.py)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start the FastAPI server
CMD uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --app-dir ai-service \
    --workers 2 \
    --log-level info
