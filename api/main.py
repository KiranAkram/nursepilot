from fastapi import FastAPI

from api.routers import nurses

app = FastAPI()

app.include_router(nurses.router)


@app.get("/health")
def health():
    return {"status": "ok"}
