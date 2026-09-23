"""DB-gated: claim / fail / reclaim semantics over a real Postgres.

Skips without a reachable DATABASE_URL (same convention as test_persistence).
"""

import os
import uuid

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel

from db.models import Extraction
from db.session import psycopg_dsn
from jobqueue import MAX_ATTEMPTS, claim, fail, reclaim_stale, reject


@pytest.fixture
def engine():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    try:
        eng = create_engine(os.environ["DATABASE_URL"])
        SQLModel.metadata.create_all(eng)
    except OperationalError:
        pytest.skip("database unreachable")
    return eng


@pytest.fixture
def conn(engine):
    with psycopg.connect(psycopg_dsn(), autocommit=True) as c:
        yield c


def _insert(engine, **kw) -> str:
    job_id = kw.pop("id", f"test-queue-{uuid.uuid4().hex}")
    with Session(engine) as s:
        s.add(Extraction(id=job_id, **kw))
        s.commit()
    return job_id


def _row(engine, job_id) -> Extraction:
    with Session(engine) as s:
        return s.get(Extraction, job_id)


@pytest.fixture(autouse=True)
def _cleanup(engine):
    yield
    with psycopg.connect(psycopg_dsn(), autocommit=True) as c:
        c.execute("DELETE FROM extractions WHERE id LIKE 'test-queue-%'")


def test_claim_takes_oldest_pending_and_marks_screening(engine, conn):
    # Park any stray pending rows from other tests behind ours by pre-claiming them.
    while claim(conn) is not None:
        pass
    older = _insert(engine, status="pending", pdf=b"%PDF-old")
    _insert(engine, status="pending", pdf=b"%PDF-new")

    got = claim(conn)

    assert got == (older, b"%PDF-old")
    assert _row(engine, older).status == "screening"


def test_claim_returns_none_when_nothing_pending(engine, conn):
    while claim(conn) is not None:
        pass
    assert claim(conn) is None


def test_claim_skips_non_pending(engine, conn):
    while claim(conn) is not None:
        pass
    _insert(engine, status="done")
    _insert(engine, status="error")
    assert claim(conn) is None


def test_fail_retries_then_errors_and_drops_pdf(engine, conn):
    job_id = _insert(engine, status="screening", pdf=b"%PDF")

    for attempt in range(1, MAX_ATTEMPTS):
        fail(conn, job_id, f"boom {attempt}")
        row = _row(engine, job_id)
        assert (row.status, row.retry_count, row.pdf) == ("pending", attempt, b"%PDF")
        conn.execute(
            "UPDATE extractions SET status='screening' WHERE id=%s", (job_id,)
        )

    fail(conn, job_id, "boom final")
    row = _row(engine, job_id)
    assert row.status == "error"
    assert row.retry_count == MAX_ATTEMPTS
    assert row.error == "boom final"
    assert row.pdf is None


def test_fail_non_retryable_errors_immediately(engine, conn):
    job_id = _insert(engine, status="screening", pdf=b"%PDF")
    fail(conn, job_id, "no pdf", retryable=False)
    row = _row(engine, job_id)
    assert (row.status, row.retry_count, row.pdf) == ("error", 1, None)


def test_reclaim_stale_requeues_only_old_in_flight_rows(engine, conn):
    stale = _insert(engine, status="extracting", pdf=b"%PDF")
    fresh = _insert(engine, status="screening", pdf=b"%PDF")
    finished = _insert(engine, status="done")
    conn.execute(
        "UPDATE extractions SET updated_at = now() - interval '1 hour' WHERE id = %s",
        (finished,),
    )
    conn.execute(
        "UPDATE extractions SET updated_at = now() - interval '1 hour' WHERE id = %s",
        (stale,),
    )

    assert reclaim_stale(conn) == 1
    assert (_row(engine, stale).status, _row(engine, stale).retry_count) == (
        "pending",
        1,
    )
    assert _row(engine, fresh).status == "screening"
    assert _row(engine, finished).status == "done"


def test_reclaim_stale_exhausts_to_error(engine, conn):
    job_id = _insert(
        engine, status="extracting", pdf=b"%PDF", retry_count=MAX_ATTEMPTS - 1
    )
    conn.execute(
        "UPDATE extractions SET updated_at = now() - interval '1 hour' WHERE id = %s",
        (job_id,),
    )

    assert reclaim_stale(conn) == 1
    row = _row(engine, job_id)
    assert row.status == "error"
    assert row.pdf is None
    assert "died" in row.error


def test_reject_is_terminal_and_records_verdict(engine, conn):
    job_id = _insert(engine, status="screening", pdf=b"%PDF", error="stale")
    verdict = {"outcome": "rejected", "score": 0.12, "threshold": 0.5}

    reject(conn, job_id, verdict)

    row = _row(engine, job_id)
    assert row.status == "rejected"
    assert row.pdf is None
    assert row.error is None
    assert row.screening == verdict
    assert claim(conn) != (job_id, None)  # never picked up again


def test_fail_records_screening_when_given(engine, conn):
    job_id = _insert(engine, status="screening", pdf=b"%PDF")
    fail(conn, job_id, "down", screening={"outcome": "unavailable", "reason": "down"})
    row = _row(engine, job_id)
    assert row.status == "pending"
    assert row.screening == {"outcome": "unavailable", "reason": "down"}
