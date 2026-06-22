import base64
import os

from celery import Celery
from sqlalchemy.engine import Engine
from sqlmodel import Session

from db import get_engine
from db.models import Extraction
from extraction import extract_chart_from_pdf
from verification import extract_page_texts, verify_chart

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# Single worker, results persisted to Postgres (not read back from Celery), so
# we drop everything that chatters at the broker while idle:
#   - no Redis result backend (the API reads charts from Postgres, not AsyncResult)
#   - no remote-control pidbox / task events (a fanout channel that gets polled)
# This keeps Redis traffic tied to actual task enqueue/consume, not coordination.
app = Celery("worker", broker=REDIS_URL)
app.conf.update(
    task_ignore_result=True,
    worker_enable_remote_control=False,
    worker_send_task_events=False,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"polling_interval": 5.0},
)


@app.task
def ping():
    return "pong"


@app.task
def add(x, y):
    return x + y


def _patient_fields(chart: dict) -> tuple[str | None, str | None]:
    """Pull denormalized name/MRN out of a chart dict for listing/search."""
    demo = chart.get("demographics") or {}
    name = ", ".join(p for p in (demo.get("family_name"), demo.get("given_name")) if p)
    return name or None, demo.get("mrn")


def _persist(
    task_id: str,
    *,
    status: str,
    chart: dict | None = None,
    grounding: list | None = None,
    flagged: list | None = None,
    error: str | None = None,
    engine: Engine | None = None,
) -> None:
    """Upsert the Extraction row for this job (engine injectable for tests).

    On the first completion we set both chart_original (immutable) and the
    editable chart; later edits go through the API and aren't clobbered here.
    """
    with Session(engine or get_engine()) as session:
        row = session.get(Extraction, task_id) or Extraction(id=task_id)
        row.status = status
        if error is not None:
            row.error = error
        if chart is not None:
            if row.chart_original is None:
                row.chart_original = chart
            if row.chart is None:
                row.chart = chart
            row.grounding = grounding
            row.flagged = flagged
            row.patient_name, row.mrn = _patient_fields(chart)
        session.add(row)
        session.commit()


@app.task(bind=True, name="extract_chart")
def extract_chart(self, pdf_b64: str) -> dict:
    """Extract a PatientChart from a base64-encoded SNF referral PDF.

    Persists progress to the extractions table (processing → done/error) and
    returns the validated chart, a per-field grounding report, and any
    individually-invalid values quarantined for review (`flagged`).
    """
    task_id = self.request.id
    if task_id:
        _persist(task_id, status="processing")
    try:
        pdf_bytes = base64.b64decode(pdf_b64)
        chart, flagged = extract_chart_from_pdf(pdf_bytes)
        chart_json = chart.model_dump(mode="json")
        grounding = [
            g.model_dump() for g in verify_chart(chart, extract_page_texts(pdf_bytes))
        ]
    except Exception as exc:
        if task_id:
            _persist(task_id, status="error", error=str(exc))
        raise
    if task_id:
        _persist(
            task_id,
            status="done",
            chart=chart_json,
            grounding=grounding,
            flagged=flagged,
        )
    return {"chart": chart_json, "grounding": grounding, "flagged": flagged}
