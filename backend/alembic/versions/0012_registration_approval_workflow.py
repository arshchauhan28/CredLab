"""Add registration approval workflow for faculty and administrator accounts.

Revision ID: 0012_registration_approval
Revises: 0011_certificate_approval
Create Date: 2026-10-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0012_registration_approval"
down_revision: Union[str, None] = "0011_certificate_approval"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add approval_status to users table.
    # Existing users (student, faculty, admin) default to APPROVED to preserve
    # access. New faculty and admin registrations start as PENDING.
    op.add_column(
        "users",
        sa.Column(
            "approval_status",
            sa.String(length=30),
            nullable=False,
            server_default="APPROVED",
        ),
    )
    op.create_index("ix_users_approval_status", "users", ["approval_status"])

    # Create registration_approvals audit table
    op.create_table(
        "registration_approvals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "applicant_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "account_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "reviewer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_registration_approvals_decision",
        "registration_approvals",
        ["decision"],
    )


def downgrade() -> None:
    op.drop_table("registration_approvals")
    op.drop_index("ix_users_approval_status", table_name="users")
    op.drop_column("users", "approval_status")
