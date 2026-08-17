FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

RUN useradd -m appuser \
    && mkdir -p /models /app/staticfiles \
    && chown -R appuser:appuser /app /models

USER appuser

ENV DJANGO_SETTINGS_MODULE=config.settings \
    WHISPER_MODEL_DIR=/models \
    WHISPER_MODEL_SIZE=tiny \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    GUNICORN_WORKERS=1 \
    GUNICORN_TIMEOUT=600

EXPOSE 8000

CMD ["sh", "-c", "python manage.py warmup_whisper && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-1} --timeout ${GUNICORN_TIMEOUT:-600}"]
