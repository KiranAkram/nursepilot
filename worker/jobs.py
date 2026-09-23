"""One extraction job: screen -> extract -> ground -> persisted `extractions` row.

No queue awareness here. Claiming, retries and failure status are owned by
jobqueue.py / listener.py; this module only knows how to run a job to `done`.
"""

from sqlalchemy.engine import Engine
from sqlmodel import Session

from db import get_engine
from db.models import Extraction
from extraction import extract_chart_from_pdf
from screening import screen_pdf
from verification import extract_page_texts, verify_chart


def _patient_fields(chart: dict) -> tuple[str | None, str | None]:
    """Pull denormalized name/MRN out of a chart dict for listing/search."""
    demo = chart.get("demographics") or {}
    name = ", ".join(p for p in (demo.get("family_name"), demo.get("given_name")) if p)
    return name or None, demo.get("mrn")


def _persist(
    job_id: str,
    *,
    status: str,
    chart: dict | None = None,
    grounding: list | None = None,
    flagged: list | None = None,
    error: str | None = None,
    screening: dict | None = None,
    engine: Engine | None = None,
) -> None:
    """Upsert the Extraction row for this job (engine injectable for tests).

    On the first completion we set both chart_original (immutable) and the
    editable chart; later edits go through the API and aren't clobbered here.
    A finished job no longer needs its PDF, so `done` clears the bytes.
    """
    with Session(engine or get_engine()) as session:
        row = session.get(Extraction, job_id) or Extraction(id=job_id)
        row.status = status
        if error is not None:
            row.error = error
        if screening is not None:
            row.screening = screening
        if chart is not None:
            if row.chart_original is None:
                row.chart_original = chart
            if row.chart is None:
                row.chart = chart
            row.grounding = grounding
            row.flagged = flagged
            row.patient_name, row.mrn = _patient_fields(chart)
        if status == "done":
            row.pdf = None
        session.add(row)
        session.commit()


def extract_chart(
    job_id: str, pdf_bytes: bytes, *, engine: Engine | None = None
) -> dict:
    """Screen, then run extraction + grounding, and persist the job as `done`.

    Screening comes first so nothing reaches Gemini until the document is
    confirmed to be a packet; a pass is recorded on the row as `extracting`.
    Raises on any failure; the caller (listener) maps the exception to
    rejected / retry / error.
    """
    screening = screen_pdf(pdf_bytes)
    _persist(job_id, status="extracting", screening=screening, engine=engine)
    chart, flagged = extract_chart_from_pdf(pdf_bytes)
    chart_json = chart.model_dump(mode="json")
    grounding = [
        g.model_dump() for g in verify_chart(chart, extract_page_texts(pdf_bytes))
    ]
    _persist(
        job_id,
        status="done",
        chart=chart_json,
        grounding=grounding,
        flagged=flagged,
        engine=engine,
    )
    return {"chart": chart_json, "grounding": grounding, "flagged": flagged}
