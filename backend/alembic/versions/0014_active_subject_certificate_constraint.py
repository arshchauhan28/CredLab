"""Add partial unique index for active subject certificates.

Revision ID: 0014_subj_cert_uniq_idx
Revises: 0013_badges_and_subject_certs
Create Date: 2026-10-19
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0014_subj_cert_uniq_idx"
down_revision: Union[str, None] = "0013_badges_and_subject_certs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create partial unique index ensuring a student can only have ONE active subject certificate per course
    op.create_index(
        "uq_active_subject_certificate",
        "completion_certificates",
        ["student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("certificate_type = 'SUBJECT' AND status = 'ACTIVE'"),
        sqlite_where=sa.text("certificate_type = 'SUBJECT' AND status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_active_subject_certificate",
        table_name="completion_certificates",
    )
