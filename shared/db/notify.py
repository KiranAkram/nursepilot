"""Postgres NOTIFY as the job event bus (API -> worker).

The `extractions` table is the queue; NOTIFY is only the wake-up. Fired inside the
inserting transaction so it's delivered on commit and never without its row.
"""

from sqlalchemy import text
from sqlmodel import Session

CHANNEL = "extraction_jobs"


def notify_new_job(session: Session, job_id: str) -> None:
    """Queue a wake-up for the worker; delivered when `session` commits."""
    session.connection().execute(
        text("SELECT pg_notify(:channel, :job_id)"),
        {"channel": CHANNEL, "job_id": job_id},
    )
