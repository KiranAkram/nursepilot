"""job queue: transient pdf bytes, retry_count, pending index

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("extractions", sa.Column("pdf", sa.LargeBinary(), nullable=True))
    op.add_column(
        "extractions",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    # The worker claims the oldest pending row; keep that lookup cheap as the
    # table fills with done rows.
    op.create_index(
        "ix_extractions_pending",
        "extractions",
        ["created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_extractions_pending", table_name="extractions")
    op.drop_column("extractions", "retry_count")
    op.drop_column("extractions", "pdf")
