import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import charts

app = FastAPI(title="NursePilot API")

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
