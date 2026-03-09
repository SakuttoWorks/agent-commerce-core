# 1. Runtime Environment: Python 3.12 (Standard for 2026)
FROM python:3.12-slim

# 2. System Dependencies: Minimal build tools and libmagic for MIME type detection
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Working Directory
WORKDIR /app

# 3. Environment Configuration
# PYTHONUNBUFFERED ensures logs are streamed directly to Cloud Logging
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Application Source Code
COPY . .

# Note: Running as default root user for maximum compatibility with Cloud Run v2 (Phase 1).
# Identity-based access control is handled at the IAM/infrastructure layer.

# 4. Entrypoint: Start Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
