import io
import os
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel

import routers.charts as charts
from db import get_session
from db.models import Extraction
from main import app

client = TestClient(app)

PDF_BYTES = b"%PDF-1.4 fake pdf body"


def _chart(family="Doe", given="Jane", mrn="M1") -> dict:
    s = {"page": 1, "quote": "x", "confidence": 0.9}
    return {
        "demographics": {
            "family_name": family,
            "given_name": given,
            "dob": "1950-01-01",
            "gender": "female",
            "mrn": mrn,
            "source": s,
        },
        "insurance": {"coverage_type": "Medicare", "source": s},
        "encounter": {
            "status": "finished",
            "encounter_class": "IMP",
            "admit_start": "2024-01-01T00:00:00",
            "discharge_end": "2024-01-05T00:00:00",
            "discharge_disposition": "SNF",
            "source": s,
        },
    }


# ---------------------------------------------------------------------------
# Offline: input validation rejects before touching the DB
# ---------------------------------------------------------------------------


@pytest.fixture
def no_db():
    """Stub the session dependency; validation paths never use it."""
    app.dependency_overrides[get_session] = lambda: iter([MagicMock()])
    yield
    app.dependency_overrides.clear()


def test_create_rejects_non_pdf(no_db):
    resp = client.post(
        "/charts", files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}
    )
    assert resp.status_code == 415


def test_create_rejects_pdf_extension_without_magic(no_db):
    resp = client.post(
        "/charts",
        files={"file": ("packet.pdf", io.BytesIO(b"not really a pdf"), "application/pdf")},
    )
    assert resp.status_code == 415


def test_create_rejects_empty(no_db):
    resp = client.post(
        "/charts", files={"file": ("packet.pdf", io.BytesIO(b""), "application/pdf")}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DB-gated: full upload/poll/edit lifecycle (skips without a reachable DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    try:
        engine = create_engine(url)
        SQLModel.metadata.create_all(engine)
    except OperationalError:
        pytest.skip("database unreachable")

    def _get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_session
    yield engine
    app.dependency_overrides.clear()


def _insert(engine, **kwargs) -> str:
    job_id = kwargs.pop("id", uuid.uuid4().hex)
    with Session(engine) as s:
        s.add(Extraction(id=job_id, **kwargs))
        s.commit()
    return job_id


def test_create_inserts_row_and_enqueues(db, monkeypatch):
    sent = {}

    def fake_send_task(name, args, task_id):
        sent.update(name=name, args=args, task_id=task_id)
        return MagicMock(id=task_id)

    monkeypatch.setattr(charts.celery_app, "send_task", fake_send_task)

    resp = client.post(
        "/charts",
        files={"file": ("packet.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert sent["name"] == "extract_chart"
    assert sent["task_id"] == job_id
    with Session(db) as s:
        row = s.get(Extraction, job_id)
        assert row.status == "pending"
        assert row.filename == "packet.pdf"


def test_get_processing(db):
    job_id = _insert(db, status="processing")
    body = client.get(f"/charts/{job_id}").json()
    assert body["status"] == "processing"
    assert body["chart"] is None


def test_get_done_returns_chart(db):
    job_id = _insert(
        db, status="done", chart=_chart(), grounding=[{"g": 1}], flagged=[]
    )
    body = client.get(f"/charts/{job_id}").json()
    assert body["status"] == "done"
    assert body["chart"]["demographics"]["family_name"] == "Doe"
    assert body["grounding"] == [{"g": 1}]


def test_get_error(db):
    job_id = _insert(db, status="error", error="boom")
    body = client.get(f"/charts/{job_id}").json()
    assert body["status"] == "error"
    assert body["detail"] == "boom"


def test_get_unknown_404(db):
    assert client.get("/charts/does-not-exist").status_code == 404


def test_put_updates_chart(db):
    job_id = _insert(db, status="done", chart=_chart(), grounding=[], flagged=[])
    edited = _chart(family="Smith", given="Pat", mrn="M2")
    resp = client.put(f"/charts/{job_id}", json=edited)
    assert resp.status_code == 200
    assert resp.json()["chart"]["demographics"]["family_name"] == "Smith"
    with Session(db) as s:
        row = s.get(Extraction, job_id)
        assert row.chart["demographics"]["family_name"] == "Smith"
        assert row.patient_name == "Smith, Pat"
        assert row.mrn == "M2"


def test_put_rejects_invalid_chart(db):
    job_id = _insert(db, status="done", chart=_chart(), grounding=[], flagged=[])
    resp = client.put(f"/charts/{job_id}", json={"demographics": {}})
    assert resp.status_code == 422


def test_put_409_when_not_done(db):
    job_id = _insert(db, status="processing")
    assert client.put(f"/charts/{job_id}", json=_chart()).status_code == 409


def test_list_charts(db):
    _insert(db, status="done", patient_name="Alpha One", chart=_chart())
    _insert(db, status="processing", patient_name="Beta Two")
    rows = client.get("/charts").json()
    names = {r["patient_name"] for r in rows}
    assert {"Alpha One", "Beta Two"} <= names
