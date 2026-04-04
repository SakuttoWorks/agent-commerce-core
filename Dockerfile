# ==========================================
# Stage 1: Builder (Ultra-fast dependency resolution and build)
# ==========================================
FROM python:3.12-slim AS builder

# Copy Astral's official fast package manager `uv` binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install essential build tools (will not bloat the runtime container)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first to leverage Docker layer caching
COPY requirements.txt pyproject.toml ./

# Create virtual environment (.venv) using uv and install lightning fast
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install -r requirements.txt

# ==========================================
# Stage 2: Runtime (Minimal image for production)
# ==========================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# 1. Environment Configuration
# PYTHONUNBUFFERED ensures logs are streamed directly to Cloud Logging
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Copy the completely built virtual environment (.venv) from the builder stage
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 2. Copy Application Source Code
COPY . .

# 3. Security: Execute as non-root user (Cloud Run Best Practice)
RUN useradd -m ghostuser && chown -R ghostuser /app
USER ghostuser

# 4. Entrypoint: Start Uvicorn server
# (workers setting can be adjusted based on Cloud Run instance size)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]