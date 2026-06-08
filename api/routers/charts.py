"""Upload a discharge PDF, then read/edit its extracted PatientChart.

Postgres-backed (via the shared `extractions` table). Celery does the work; the
DB is the source of truth for status and results.
- POST /charts            enqueue extraction, return a job id
- GET  /charts            list extractions (history)
- GET  /charts/{job_id}   status + chart/grounding/flagged when done
- PUT  /charts/{job_id}   overwrite the (nurse-edited) chart
"""

import base64
import uuid
from datetime import datetime
from typing import Annotated

from celery_app import EXTRACT_TASK, celery_app
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session, select

from db import get_session
from db.models import Extraction
from schemas import PatientChart

router = APIRouter(prefix="/charts", tags=["charts"])

MAX_PDF_BYTES = 25 * 1024 * 1024  # 25 MB

SessionDep = Annotated[Session, Depends(get_session)]


def _public_status(db_status: str) -> str:
    """Collapse internal row states into the three the frontend cares about."""
    if db_status in ("pending", "processing"):
        return "processing"
    return db_status  # "done" | "error"


def _patient_fields(chart: dict) -> tuple[str | None, str | None]:
    demo = chart.get("demographics") or {}
    name = ", ".join(p for p in (demo.get("family_name"), demo.get("given_name")) if p)
    return name or None, demo.get("mrn")


class JobCreated(BaseModel):
    job_id: str
    status: str = "processing"


class JobStatus(BaseModel):
    job_id: str
    status: str  # "processing" | "done" | "error"
    filename: str | None = None
    patient_name: str | None = None
    mrn: str | None = None
    chart: dict | None = None
    grounding: list[dict] | None = None
    flagged: list[dict] | None = None
    detail: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class JobSummary(BaseModel):
    job_id: str
    status: str
    filename: str | None = None
    patient_name: str | None = None
    mrn: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _to_status(row: Extraction) -> JobStatus:
    public = _public_status(row.status)
    return JobStatus(
        job_id=row.id,
        status=public,
        filename=row.filename,
        patient_name=row.patient_name,
        mrn=row.mrn,
        chart=row.chart if public == "done" else None,
        grounding=row.grounding if public == "done" else None,
        flagged=row.flagged if public == "done" else None,
        detail=row.error if public == "error" else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobCreated)
async def create_chart(
    file: UploadFile,
    session: SessionDep,
) -> JobCreated:
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

    # Create the row first (known id) so the worker only ever updates it.
    job_id = uuid.uuid4().hex
    session.add(Extraction(id=job_id, status="pending", filename=file.filename))
    session.commit()

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    celery_app.send_task(EXTRACT_TASK, args=[pdf_b64], task_id=job_id)
    return JobCreated(job_id=job_id)


@router.get("", response_model=list[JobSummary])
def list_charts(
    session: SessionDep,
    limit: int = 50,
) -> list[JobSummary]:
    rows = session.exec(
        select(Extraction).order_by(Extraction.created_at.desc()).limit(limit)
    ).all()
    return [
        JobSummary(
            job_id=r.id,
            status=_public_status(r.status),
            filename=r.filename,
            patient_name=r.patient_name,
            mrn=r.mrn,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/{job_id}", response_model=JobStatus)
def get_chart(job_id: str, session: SessionDep) -> JobStatus:
    row = session.get(Extraction, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    return _to_status(row)


@router.put("/{job_id}", response_model=JobStatus)
def update_chart(
    job_id: str,
    chart: dict,
    session: SessionDep,
) -> JobStatus:
    row = session.get(Extraction, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    if row.status != "done":
        raise HTTPException(status_code=409, detail="Chart is not ready to edit.")

    # Edits must still be a well-formed chart.
    try:
        validated = PatientChart.model_validate(chart).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row.chart = validated
    row.patient_name, row.mrn = _patient_fields(validated)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_status(row)
