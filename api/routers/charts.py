"""Upload a discharge PDF and poll for its extracted PatientChart.

Two endpoints, Redis-backed via Celery (no DB):
- POST /charts            enqueue extraction, return a job id
- GET  /charts/{job_id}   poll status; return chart + grounding when done
"""

import base64

from celery.result import AsyncResult
from celery_app import EXTRACT_TASK, celery_app
from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel

router = APIRouter(prefix="/charts", tags=["charts"])

MAX_PDF_BYTES = 25 * 1024 * 1024  # 25 MB


class JobCreated(BaseModel):
    job_id: str
    status: str = "processing"


class JobStatus(BaseModel):
    job_id: str
    status: str  # "processing" | "done" | "error"
    chart: dict | None = None
    grounding: list[dict] | None = None
    detail: str | None = None


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobCreated)
async def create_chart(file: UploadFile) -> JobCreated:
    if file.content_type not in ("application/pdf", "application/octet-stream") and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Expected a PDF upload.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 25 MB limit.")
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="File is not a valid PDF.")

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    result = celery_app.send_task(EXTRACT_TASK, args=[pdf_b64])
    return JobCreated(job_id=result.id)


@router.get("/{job_id}", response_model=JobStatus)
def get_chart(job_id: str) -> JobStatus:
    result = AsyncResult(job_id, app=celery_app)

    if result.successful():
        payload = result.result
        return JobStatus(
            job_id=job_id,
            status="done",
            chart=payload.get("chart"),
            grounding=payload.get("grounding"),
        )
    if result.failed():
        return JobStatus(job_id=job_id, status="error", detail=str(result.result))
    # PENDING / STARTED / RETRY — also the response for an unknown id.
    return JobStatus(job_id=job_id, status="processing")
