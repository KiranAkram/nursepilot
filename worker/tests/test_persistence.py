import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel

from db.models import Extraction
from jobs import _patient_fields, _persist

# ---------------------------------------------------------------------------
# Offline: pure field mapping
# ---------------------------------------------------------------------------


def test_patient_fields():
    chart = {
        "demographics": {
            "family_name": "Henderson",
            "given_name": "Dorothy",
            "mrn": "M1",
        }
    }
    assert _patient_fields(chart) == ("Henderson, Dorothy", "M1")


def test_patient_fields_partial():
    assert _patient_fields({"demographics": {"family_name": "Doe"}}) == ("Doe", None)


def test_patient_fields_empty():
    assert _patient_fields({}) == (None, None)


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

    with Session(engine) as s:
        s.add(Extraction(id=tid, status="processing", pdf=b"%PDF"))
        s.commit()

    chart = {"demographics": {"family_name": "Doe", "given_name": "Jane", "mrn": "M9"}}
    _persist(
        tid, status="done", chart=chart, grounding=[{"f": 1}], flagged=[], engine=engine
    )
    with Session(engine) as s:
        row = s.get(Extraction, tid)
        assert row.status == "done"
        assert row.chart_original == chart
        assert row.chart == chart
        assert row.grounding == [{"f": 1}]
        assert (row.patient_name, row.mrn) == ("Doe, Jane", "M9")
        assert row.pdf is None  # finished jobs drop their bytes

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
