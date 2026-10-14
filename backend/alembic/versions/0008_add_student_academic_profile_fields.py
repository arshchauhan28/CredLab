"""Add student academic profile fields to users table.

Revision ID: 0008_student_academic_profile
Revises: 0007_completion_certificate
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_student_academic_profile"
down_revision: Union[str, None] = "0007_completion_certificate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add academic profile fields to users."""

    op.add_column(
        "users",
        sa.Column("student_id_number", sa.String(length=50), nullable=True),
    )

    op.create_index(
        "ix_users_student_id_number",
        "users",
        ["student_id_number"],
        unique=True,
    )

    op.add_column(
        "users",
        sa.Column("academic_course", sa.String(length=100), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("academic_year", sa.String(length=50), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("semester", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    """Remove academic profile fields from users."""

    op.drop_index(
        "ix_users_student_id_number",
        table_name="users",
    )

    op.drop_column("users", "semester")
    op.drop_column("users", "academic_year")
    op.drop_column("users", "academic_course")
    op.drop_column("users", "student_id_number")