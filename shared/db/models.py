"""SQLModel tables. One row per uploaded PDF / extraction job."""

from datetime import datetime

from sqlalchemy import Column, DateTime, LargeBinary, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Extraction(SQLModel, table=True):
    __tablename__ = "extractions"

    # API-generated job id (uuid4 hex); the row is created before the worker sees it.
    id: str = Field(primary_key=True)
    status: str = Field(default="pending", index=True)
    # pending -> screening -> extracting -> done | rejected | error
    filename: str | None = None

    # Denormalized for listing/search without cracking open the chart JSON.
    patient_name: str | None = Field(default=None, index=True)
    mrn: str | None = Field(default=None, index=True)

    # chart_original is the immutable LLM extraction; chart is the editable working
    # copy (starts equal, overwritten by nurse edits). grounding/flagged describe
    # the original extraction.
    chart_original: dict | None = Field(default=None, sa_column=Column(JSONB))
    chart: dict | None = Field(default=None, sa_column=Column(JSONB))
    grounding: list | None = Field(default=None, sa_column=Column(JSONB))
    flagged: list | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = None

    # Job-queue state. The PDF is held only while the job is pending/processing
    # (cleared on done/final error); retry_count caps re-runs after a failure.
    pdf: bytes | None = Field(default=None, sa_column=Column(LargeBinary))
    retry_count: int = Field(default=0, sa_column_kwargs={"server_default": "0"})
    # Screening verdict (worker/screening.py): outcome accepted|rejected|unavailable,
    # score, threshold, model, at. The audit record for the intake gate.
    screening: dict | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )
