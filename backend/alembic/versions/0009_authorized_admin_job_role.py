"""Require explicit administrative job-role provisioning for admin enrollment.

Revision ID: 0009_authorized_admin_job_role
Revises: 82d1a741d8f7
Create Date: 2026-10-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_authorized_admin_job_role"
down_revision: Union[str, None] = "82d1a741d8f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable by design: existing rows are preserved but do not authorize
    # administrator registration until an authorized SUPER_ADMIN provisions them.
    op.add_column(
        "authorized_enrollments",
        sa.Column("admin_job_role", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_authorized_enrollments_admin_job_role",
        "authorized_enrollments",
        ["admin_job_role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_authorized_enrollments_admin_job_role",
        table_name="authorized_enrollments",
    )
    op.drop_column("authorized_enrollments", "admin_job_role")
