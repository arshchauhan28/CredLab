"""Add academic program/year-of-study to subjects and student profiles.

Revision ID: 0010_subject_program_year
Revises: 0009_authorized_admin_job_role
Create Date: 2026-10-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0010_subject_program_year"
down_revision: Union[str, None] = "0009_authorized_admin_job_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing records are preserved and receive conservative defaults.
    op.add_column("courses", sa.Column("program", sa.String(length=100), nullable=False, server_default="General"))
    op.add_column("courses", sa.Column("year_of_study", sa.String(length=30), nullable=False, server_default="1st Year"))
    with op.batch_alter_table("courses") as batch_op:
        batch_op.alter_column("code", existing_type=sa.String(length=50), nullable=True)
    op.add_column("users", sa.Column("year_of_study", sa.String(length=30), nullable=True))


def downgrade() -> None:
    # Downgrade is only safe if every subject has a code; otherwise restoring
    # NOT NULL would fail and lose the optional-code feature.
    op.drop_column("users", "year_of_study")
    with op.batch_alter_table("courses") as batch_op:
        batch_op.alter_column("code", existing_type=sa.String(length=50), nullable=False)
    op.drop_column("courses", "year_of_study")
    op.drop_column("courses", "program")
