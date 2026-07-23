FROM python:3.11-slim

WORKDIR /app

# 1. Create a non-root user early so this layer is cached permanently
RUN useradd -m enlidea_user

# 2. Install system dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 3. Use BuildKit cache to speed up pip installs across rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt gunicorn

# 4. Copy files with ownership already assigned
COPY --chown=enlidea_user:enlidea_user . .

# 5. Create runtime media and static directories and set ownership before switching to non-root user
RUN mkdir -p /app/media /app/static /app/staticfiles \
    && chown -R enlidea_user:enlidea_user /app /app/media /app/static /app/staticfiles

USER enlidea_user

# Gather static files for Whitenoise to serve (providing dummy env vars for build process)
RUN DJANGO_SETTINGS_MODULE=enlidea.settings.development \
    SECRET_KEY=dummy \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASS=dummy \
    DB_HOST=dummy \
    DB_PORT=5432 \
    SIGNING_KEY=dummy \
    EMAIL_HOST_USER=dummy \
    EMAIL_HOST_PASSWORD=dummy \
    ADMIN_URL=admin/ \
    ALLOWED_HOSTS=localhost \
    FRONTEND_URL=http://localhost:5173 \
    CORS_ALLOWED_ORIGINS=http://localhost:5173 \
    CELERY_BROKER_URL=redis://redis:6379/0 \
    CELERY_RESULT_BACKEND=redis://redis:6379/0 \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Use gunicorn instead of runserver
CMD ["gunicorn", "enlidea.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
