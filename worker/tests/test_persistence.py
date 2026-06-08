import base64
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel

import tasks
from db.models import Extraction
from tasks import _patient_fields, _persist


class _FakeChart:
    def model_dump(self, mode="json"):
        return {"demographics": {"family_name": "A", "given_name": "B", "mrn": "M"}}

# ---------------------------------------------------------------------------
# Offline: pure field mapping
# ---------------------------------------------------------------------------


def test_patient_fields():
    chart = {"demographics": {"family_name": "Henderson", "given_name": "Dorothy", "mrn": "M1"}}
    assert _patient_fields(chart) == ("Henderson, Dorothy", "M1")


def test_patient_fields_partial():
    assert _patient_fields({"demographics": {"family_name": "Doe"}}) == ("Doe", None)


def test_patient_fields_empty():
    assert _patient_fields({}) == (None, None)


def test_task_persists_status_sequence(monkeypatch):
    """The bound task should persist processing -> done with the chart payload."""
    calls = []
    monkeypatch.setattr(
        tasks, "_persist", lambda task_id, **kw: calls.append((kw.get("status"), kw))
    )
    monkeypatch.setattr(tasks, "extract_chart_from_pdf", lambda pdf: (_FakeChart(), []))
    monkeypatch.setattr(tasks, "extract_page_texts", lambda pdf: [])
    monkeypatch.setattr(tasks, "verify_chart", lambda chart, texts: [])

    result = tasks.extract_chart.apply(args=[base64.b64encode(b"x").decode()])

    assert result.successful()
    assert [status for status, _ in calls] == ["processing", "done"]
    done_kwargs = calls[-1][1]
    assert done_kwargs["chart"] == {
        "demographics": {"family_name": "A", "given_name": "B", "mrn": "M"}
    }
    assert done_kwargs["grounding"] == []


# ---------------------------------------------------------------------------
# DB-gated: persistence lifecycle (skips without a reachable DATABASE_URL)
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    try:
        eng = create_engine(url)
        SQLModel.metadata.create_all(eng)
    except OperationalError:
        pytest.skip("database unreachable")
    return eng


def _cleanup(engine, task_id):
    with Session(engine) as s:
        row = s.get(Extraction, task_id)
        if row:
            s.delete(row)
            s.commit()


def test_persist_lifecycle(engine):
    tid = "test-persist-lifecycle"
    _cleanup(engine, tid)

    _persist(tid, status="processing", engine=engine)
    with Session(engine) as s:
        assert s.get(Extraction, tid).status == "processing"

    chart = {"demographics": {"family_name": "Doe", "given_name": "Jane", "mrn": "M9"}}
    _persist(tid, status="done", chart=chart, grounding=[{"f": 1}], flagged=[], engine=engine)
    with Session(engine) as s:
        row = s.get(Extraction, tid)
        assert row.status == "done"
        assert row.chart_original == chart
        assert row.chart == chart
        assert row.grounding == [{"f": 1}]
        assert (row.patient_name, row.mrn) == ("Doe, Jane", "M9")

    _cleanup(engine, tid)


def test_persist_error_status(engine):
    tid = "test-persist-error"
    _cleanup(engine, tid)

    _persist(tid, status="error", error="boom", engine=engine)
    with Session(engine) as s:
        row = s.get(Extraction, tid)
        assert row.status == "error"
        assert row.error == "boom"
        assert row.chart is None

    _cleanup(engine, tid)
