# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system deps for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev musl-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

RUN addgroup --system appuser && \
    adduser --system --no-create-home --ingroup appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY backend/app ./app

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30 --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# uvicorn with gunicorn-compatible multiple workers
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]