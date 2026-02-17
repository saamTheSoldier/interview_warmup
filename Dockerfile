# Multi-stage build for smaller production image
# Challenge: Optimize Docker image size and build cache

FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user (security best practice)
RUN useradd -m -u 1000 appuser

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Run with uvicorn; Gunicorn + Uvicorn workers for production scalability
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
