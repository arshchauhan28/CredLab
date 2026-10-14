"""Add badges table, subject certificate requests, and subject certificate support.

Revision ID: 0013_badges_and_subject_certs
Revises: 0012_registration_approval
Create Date: 2026-10-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0013_badges_and_subject_certs"
down_revision: Union[str, None] = "0012_registration_approval"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create badges table
    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "practical_id",
            sa.Integer(),
            sa.ForeignKey("lab_practicals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "badge_type",
            sa.String(length=50),
            nullable=False,
            server_default="PRACTICAL_COMPLETION",
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "icon",
            sa.String(length=50),
            nullable=False,
            server_default="??",
        ),
        sa.Column(
            "earned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.UniqueConstraint(
            "user_id", "practical_id", name="uq_user_practical_badge"
        ),
    )

    # 2. Create subject_certificate_requests table
    op.create_table(
        "subject_certificate_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column(
            "reviewed_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "student_id",
            "course_id",
            name="uq_subject_cert_request_student_course",
        ),
    )

    # 3. Add course_id and certificate_type to completion_certificates
    op.add_column(
        "completion_certificates",
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_completion_certificates_course_id",
        "completion_certificates",
        ["course_id"],
    )
    op.add_column(
        "completion_certificates",
        sa.Column(
            "certificate_type",
            sa.String(length=30),
            nullable=False,
            server_default="PRACTICAL",
        ),
    )
    op.create_index(
        "ix_completion_certificates_certificate_type",
        "completion_certificates",
        ["certificate_type"],
    )


    # 4. Add is_active column to lab_practicals for safe archival
    op.add_column(
        "lab_practicals",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_index(
        "ix_lab_practicals_is_active",
        "lab_practicals",
        ["is_active"],
    )

def downgrade() -> None:
    op.drop_index(
        "ix_completion_certificates_certificate_type",
        table_name="completion_certificates",
    )
    op.drop_column("completion_certificates", "certificate_type")
    op.drop_index(
        "ix_completion_certificates_course_id",
        table_name="completion_certificates",
    )
    op.drop_column("completion_certificates", "course_id")
    op.drop_table("subject_certificate_requests")
    op.drop_table("badges")
