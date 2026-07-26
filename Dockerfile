FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir /usr/src/app/wheels -r requirements.txt gunicorn==26.0.0

FROM python:3.11-slim

WORKDIR /app

RUN useradd -m enlidea_user
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/src/app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

COPY --chown=enlidea_user:enlidea_user . .

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

CMD ["gunicorn", "enlidea.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
