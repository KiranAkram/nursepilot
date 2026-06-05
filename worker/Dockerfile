FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY shared/ ./shared/
COPY worker/ ./worker/
RUN uv pip install --system ./shared celery redis google-genai pypdf python-dotenv

WORKDIR /app/worker

CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
