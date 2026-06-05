"""Celery client for enqueuing/polling worker tasks.

The API never imports worker code (no Gemini deps leak in). It talks to the
worker purely over Redis by task *name* — see EXTRACT_TASK.
"""

import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# Stable cross-service contract: matches @app.task(name=...) in worker/tasks.py.
EXTRACT_TASK = "extract_chart"

celery_app = Celery("api", broker=REDIS_URL, backend=REDIS_URL)
