"""SQLModel tables. One row per uploaded PDF / extraction job."""

from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Extraction(SQLModel, table=True):
    __tablename__ = "extractions"

    # Celery task id doubles as the job/record id.
    id: str = Field(primary_key=True)
    status: str = Field(default="pending", index=True)  # pending|processing|done|error
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
