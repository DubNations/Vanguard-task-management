# ============================================================
# Django App Dockerfile — 多阶段构建
# ============================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=seedteam.settings \
    DJANGO_ENV=prod

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    libcairo2 \
    libpango1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements/base.txt backend/requirements/prod.txt /app/requirements/
RUN pip install --no-cache-dir -r /app/requirements/prod.txt

# Copy backend code
COPY backend/ /app/

# Collect static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Create necessary directories
RUN mkdir -p /app/storage /app/logs

# Run as non-root user
RUN addgroup --system app && adduser --system --ingroup app app
RUN chown -R app:app /app
USER app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run with gunicorn
CMD ["gunicorn", "seedteam.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "/app/logs/access.log", \
     "--error-logfile", "/app/logs/error.log"]
