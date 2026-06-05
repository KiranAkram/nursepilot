import io

from fastapi.testclient import TestClient

import routers.charts as charts
from main import app

client = TestClient(app)

PDF_BYTES = b"%PDF-1.4 fake pdf body"


class FakeAsyncResult:
    """Stand-in for celery.result.AsyncResult with a controllable state."""

    def __init__(self, job_id, *, state, result=None):
        self.id = job_id
        self._state = state
        self.result = result

    def successful(self):
        return self._state == "SUCCESS"

    def failed(self):
        return self._state == "FAILURE"


def _patch_async_result(monkeypatch, **kwargs):
    monkeypatch.setattr(
        charts,
        "AsyncResult",
        lambda job_id, app=None: FakeAsyncResult(job_id, **kwargs),
    )


def test_create_chart_enqueues(monkeypatch):
    sent = {}

    def fake_send_task(name, args):
        sent["name"] = name
        sent["args"] = args
        return FakeAsyncResult("job-123", state="PENDING")

    monkeypatch.setattr(charts.celery_app, "send_task", fake_send_task)

    resp = client.post(
        "/charts",
        files={"file": ("packet.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )

    assert resp.status_code == 202
    assert resp.json() == {"job_id": "job-123", "status": "processing"}
    assert sent["name"] == "extract_chart"
    assert isinstance(sent["args"][0], str)  # base64-encoded


def test_create_chart_rejects_non_pdf():
    resp = client.post(
        "/charts",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 415


def test_create_chart_rejects_pdf_extension_without_magic():
    resp = client.post(
        "/charts",
        files={"file": ("packet.pdf", io.BytesIO(b"not really a pdf"), "application/pdf")},
    )
    assert resp.status_code == 415


def test_create_chart_rejects_empty():
    resp = client.post(
        "/charts",
        files={"file": ("packet.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert resp.status_code == 400


def test_get_chart_processing(monkeypatch):
    _patch_async_result(monkeypatch, state="STARTED")
    resp = client.get("/charts/job-123")
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"


def test_get_chart_done(monkeypatch):
    payload = {"chart": {"demographics": {}}, "grounding": [{"field": "x", "grounded": True}]}
    _patch_async_result(monkeypatch, state="SUCCESS", result=payload)
    resp = client.get("/charts/job-123")
    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "done"
    assert body["chart"] == payload["chart"]
    assert body["grounding"] == payload["grounding"]


def test_get_chart_error(monkeypatch):
    _patch_async_result(monkeypatch, state="FAILURE", result=ValueError("boom"))
    resp = client.get("/charts/job-123")
    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "error"
    assert "boom" in body["detail"]
