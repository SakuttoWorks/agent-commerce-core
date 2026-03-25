# ==========================================
# Stage 1: Builder (Ultra-fast dependency resolution and build)
# ==========================================
FROM python:3.12-slim AS builder

# Copy the official ultra-fast package manager `uv` binary from Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# System libraries required for python-magic (and build tools for C extensions just in case)
# * These build tools will not be carried over to the runtime stage, keeping the container lightweight.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first to leverage Docker layer caching
COPY requirements.txt pyproject.toml ./

# Build a virtual environment (.venv) using uv for blazing-fast installation
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install -r requirements.txt

# ==========================================
# Stage 2: Runtime (Minimal image for production deployment)
# ==========================================
FROM python:3.12-slim AS runtime

# 1. System Dependencies: libmagic for python-magic (MIME type detection)
# Install only the shared libraries required for runtime and completely remove caches
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# 2. Environment Configuration
# PYTHONUNBUFFERED ensures logs are streamed directly to Cloud Logging
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Copy the completely built virtual environment (.venv) from the builder stage
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 3. Copy Application Source Code
COPY . .

# 4. Security: Run as a non-root user (Cloud Run best practice)
RUN useradd -m ghostuser && chown -R ghostuser /app
USER ghostuser

# 5. Entrypoint: Start Uvicorn server
# (The number of workers can be adjusted according to the Cloud Run instance size)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
