"""Add faculty-reviewed lab completion certificate requests.

Revision ID: 0011_certificate_approval
Revises: 0010_subject_program_year
Create Date: 2026-10-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0011_certificate_approval"
down_revision: Union[str, None] = "0010_subject_program_year"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "certificate_approval_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lab_id", sa.Integer(), sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("practical_id", sa.Integer(), sa.ForeignKey("lab_practicals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("student_id", "lab_id", name="uq_certificate_request_student_lab"),
    )
    op.create_index("ix_certificate_approval_requests_student_id", "certificate_approval_requests", ["student_id"])
    op.create_index("ix_certificate_approval_requests_lab_id", "certificate_approval_requests", ["lab_id"])
    op.create_index("ix_certificate_approval_requests_practical_id", "certificate_approval_requests", ["practical_id"])
    op.create_index("ix_certificate_approval_requests_submission_id", "certificate_approval_requests", ["submission_id"])
    op.create_index("ix_certificate_approval_requests_status", "certificate_approval_requests", ["status"])


def downgrade() -> None:
    op.drop_table("certificate_approval_requests")
