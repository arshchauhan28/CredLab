"""Create completion_certificates and certificate_signing_keys tables

Revision ID: 0007_create_completion_certificates_tables
Revises: 0006_add_practical_submissions_and_passing_threshold
Create Date: 2026-10-11 01:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007_completion_certificate'
down_revision: Union[str, None] = '0006_practical_submissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create certificate_signing_keys table (public key registry)
    op.create_table(
        'certificate_signing_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key_id', sa.String(length=100), nullable=False),
        sa.Column('public_key_hex', sa.String(length=64), nullable=False),
        sa.Column('algorithm', sa.String(length=50), nullable=False, server_default='ED25519-SHA256'),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_certificate_signing_keys_id'), 'certificate_signing_keys', ['id'], unique=False
    )
    op.create_index(
        op.f('ix_certificate_signing_keys_key_id'), 'certificate_signing_keys', ['key_id'], unique=True
    )

    # 2. Create completion_certificates table
    op.create_table(
        'completion_certificates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('practical_id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('schema_version', sa.String(length=20), nullable=False, server_default='1.0'),
        sa.Column('issuer', sa.String(length=100), nullable=False, server_default='LabOS Sentinel'),
        sa.Column('algorithm', sa.String(length=50), nullable=False, server_default='ED25519-SHA256'),
        sa.Column('key_id', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('payload_digest', sa.String(length=64), nullable=False),
        sa.Column('signature', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['practical_id'], ['lab_practicals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'practical_id', name='uq_certificate_student_practical'),
    )
    op.create_index(op.f('ix_completion_certificates_id'), 'completion_certificates', ['id'], unique=False)
    op.create_index(op.f('ix_completion_certificates_student_id'), 'completion_certificates', ['student_id'], unique=False)
    op.create_index(op.f('ix_completion_certificates_practical_id'), 'completion_certificates', ['practical_id'], unique=False)
    op.create_index(op.f('ix_completion_certificates_submission_id'), 'completion_certificates', ['submission_id'], unique=False)
    op.create_index(op.f('ix_completion_certificates_key_id'), 'completion_certificates', ['key_id'], unique=False)
    op.create_index(op.f('ix_completion_certificates_status'), 'completion_certificates', ['status'], unique=False)


def downgrade() -> None:
    # 1. Drop completion_certificates
    op.drop_index(op.f('ix_completion_certificates_status'), table_name='completion_certificates')
    op.drop_index(op.f('ix_completion_certificates_key_id'), table_name='completion_certificates')
    op.drop_index(op.f('ix_completion_certificates_submission_id'), table_name='completion_certificates')
    op.drop_index(op.f('ix_completion_certificates_practical_id'), table_name='completion_certificates')
    op.drop_index(op.f('ix_completion_certificates_student_id'), table_name='completion_certificates')
    op.drop_index(op.f('ix_completion_certificates_id'), table_name='completion_certificates')
    op.drop_table('completion_certificates')

    # 2. Drop certificate_signing_keys
    op.drop_index(op.f('ix_certificate_signing_keys_key_id'), table_name='certificate_signing_keys')
    op.drop_index(op.f('ix_certificate_signing_keys_id'), table_name='certificate_signing_keys')
    op.drop_table('certificate_signing_keys')
