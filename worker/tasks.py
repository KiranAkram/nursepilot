import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)


@app.task
def ping():
    return "pong"


@app.task
def add(x, y):
    return x + y
