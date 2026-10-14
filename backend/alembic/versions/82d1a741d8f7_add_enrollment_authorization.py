"""
Add enrollment authorization.

Revision ID: 82d1a741d8f7
Revises: 0008_student_academic_profile

Create Date: 2026-10-12 03:12:07.602467
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "82d1a741d8f7"
down_revision: Union[str, None] = "0008_student_academic_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply enrollment authorization and account profile changes."""

    # Create the enrollment authorization allowlist.
    op.create_table(
        "authorized_enrollments",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "enrollment_number",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "expected_role",
            sa.Enum(
                "STUDENT",
                "FACULTY",
                "ADMIN",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "claimed_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["claimed_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for enrollment authorization lookups.
    op.create_index(
        "ix_authorized_enrollments_claimed_by_user_id",
        "authorized_enrollments",
        ["claimed_by_user_id"],
        unique=True,
    )

    op.create_index(
        "ix_authorized_enrollments_course_id",
        "authorized_enrollments",
        ["course_id"],
        unique=False,
    )

    op.create_index(
        "ix_authorized_enrollments_enrollment_number",
        "authorized_enrollments",
        ["enrollment_number"],
        unique=True,
    )

    op.create_index(
        "ix_authorized_enrollments_id",
        "authorized_enrollments",
        ["id"],
        unique=False,
    )

    # Add enrollment and administrative job-role fields to users.
    # Enrollment numbers remain nullable to preserve existing accounts.
    op.add_column(
        "users",
        sa.Column(
            "enrollment_number",
            sa.String(length=10),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "admin_job_role",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_users_enrollment_number",
        "users",
        ["enrollment_number"],
        unique=True,
    )


def downgrade() -> None:
    """Reverse enrollment authorization and account profile changes."""

    # Remove the users enrollment-number index and columns.
    op.drop_index(
        "ix_users_enrollment_number",
        table_name="users",
    )

    op.drop_column("users", "admin_job_role")
    op.drop_column("users", "enrollment_number")

    # Remove authorization indexes.
    op.drop_index(
        "ix_authorized_enrollments_id",
        table_name="authorized_enrollments",
    )

    op.drop_index(
        "ix_authorized_enrollments_enrollment_number",
        table_name="authorized_enrollments",
    )

    op.drop_index(
        "ix_authorized_enrollments_course_id",
        table_name="authorized_enrollments",
    )

    op.drop_index(
        "ix_authorized_enrollments_claimed_by_user_id",
        table_name="authorized_enrollments",
    )

    # Remove the authorization table.
    op.drop_table("authorized_enrollments")