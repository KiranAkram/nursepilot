FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY shared/ ./shared/
COPY worker/ ./worker/
COPY api/ ./api/

# The extraction worker runs inside this process (api/main.py lifespan), so the
# image bundles worker/ and its runtime deps (google-genai, pypdf) next to the
# API's own. Adding a dep to either service's pyproject means adding it here too.
RUN uv pip install --system ./shared \
    fastapi uvicorn[standard] python-multipart \
    google-genai pypdf httpx

# Lets `from listener import run_forever` resolve without packaging worker/.
ENV PYTHONPATH=/app/worker

WORKDIR /app/api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
