"""initial extractions table

Revision ID: 0001
Revises:
Create Date: 2026-06-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extractions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("patient_name", sa.String(), nullable=True),
        sa.Column("mrn", sa.String(), nullable=True),
        sa.Column("chart_original", postgresql.JSONB(), nullable=True),
        sa.Column("chart", postgresql.JSONB(), nullable=True),
        sa.Column("grounding", postgresql.JSONB(), nullable=True),
        sa.Column("flagged", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extractions_status", "extractions", ["status"])
    op.create_index("ix_extractions_patient_name", "extractions", ["patient_name"])
    op.create_index("ix_extractions_mrn", "extractions", ["mrn"])


def downgrade() -> None:
    op.drop_index("ix_extractions_mrn", table_name="extractions")
    op.drop_index("ix_extractions_patient_name", table_name="extractions")
    op.drop_index("ix_extractions_status", table_name="extractions")
    op.drop_table("extractions")
