# Multi-stage build for minimal image size
FROM python:3.12-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Production image
FROM python:3.12-alpine

LABEL maintainer="Server Monitor"
LABEL description="Lightweight server monitoring dashboard"

# Install runtime dependencies
RUN apk add --no-cache \
    smartmontools \
    lsblk \
    coreutils \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN adduser -D -h /app monitor

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Copy application files
COPY --chown=monitor:monitor backend/ ./backend/
COPY --chown=monitor:monitor frontend/ ./frontend/

# Create data directory
RUN mkdir -p /app/data && chown monitor:monitor /app/data

WORKDIR /app/backend

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MONITOR_DB_PATH=/app/data/metrics.db \
    COLLECTION_INTERVAL=300 \
    RETENTION_DAYS=90 \
    LOG_LEVEL=WARNING \
    PORT=8080

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run as non-root user (note: may need root for SMART access)
# USER monitor

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "2", "app:app"]
