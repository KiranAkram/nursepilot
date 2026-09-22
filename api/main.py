import os
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import charts


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # The extraction worker runs in-process as a daemon thread, so one web service
    # is both API and worker. RUN_WORKER=0 disables it: for running the API alone
    # (e.g. `uv run uvicorn` without worker deps on the path) or once the worker
    # is split back out into its own service (`python worker/main.py`).
    if os.environ.get("RUN_WORKER", "1") == "1":
        from listener import run_forever  # worker/ is on PYTHONPATH in the image

        threading.Thread(
            target=run_forever, name="extraction-worker", daemon=True
        ).start()
    yield


app = FastAPI(title="NursePilot API", lifespan=lifespan)

# Frontend runs on a separate origin in dev (Vite, :5173). Override in cloud.
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(charts.router)


@app.get("/health")
def health():
    return {"status": "ok"}
