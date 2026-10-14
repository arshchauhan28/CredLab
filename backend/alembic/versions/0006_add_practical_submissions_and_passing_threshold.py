"""Add practical_id to submissions and passing_threshold to lab_practicals

Revision ID: 0006_add_practical_submissions_and_passing_threshold
Revises: 0005_create_university_management_tables
Create Date: 2026-10-10 23:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006_practical_submissions'
down_revision: Union[str, None] = '0005_university_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add passing_threshold to lab_practicals
    with op.batch_alter_table('lab_practicals', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('passing_threshold', sa.Float(), nullable=False, server_default='100.0')
        )

    # 2. Add practical_id to submissions with foreign key and index
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('practical_id', sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            batch_op.f('ix_submissions_practical_id'), ['practical_id'], unique=False
        )
        batch_op.create_foreign_key(
            'fk_submissions_practical_id',
            'lab_practicals',
            ['practical_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    # 1. Remove practical_id from submissions
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_submissions_practical_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_submissions_practical_id'))
        batch_op.drop_column('practical_id')

    # 2. Remove passing_threshold from lab_practicals
    with op.batch_alter_table('lab_practicals', schema=None) as batch_op:
        batch_op.drop_column('passing_threshold')
