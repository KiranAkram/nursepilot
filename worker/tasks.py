import base64
import os

from celery import Celery

from extraction import extract_chart_from_pdf
from verification import extract_page_texts, verify_chart

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)


@app.task
def ping():
    return "pong"


@app.task
def add(x, y):
    return x + y


@app.task(name="extract_chart")
def extract_chart(pdf_b64: str) -> dict:
    """Extract a PatientChart from a base64-encoded SNF referral PDF.

    Returns the validated chart plus a per-field grounding report.
    """
    pdf_bytes = base64.b64decode(pdf_b64)
    chart = extract_chart_from_pdf(pdf_bytes)
    grounding = verify_chart(chart, extract_page_texts(pdf_bytes))
    return {
        "chart": chart.model_dump(mode="json"),
        "grounding": [g.model_dump() for g in grounding],
    }
