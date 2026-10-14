"""Create editor_events table

Revision ID: 0003_create_editor_events_table
Revises: 0002_create_question_tables
Create Date: 2026-10-10 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_create_editor_events_table'
down_revision: Union[str, None] = '0002_create_question_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'editor_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_editor_events_id'), 'editor_events', ['id'], unique=False)
    op.create_index(op.f('ix_editor_events_user_id'), 'editor_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_editor_events_question_id'), 'editor_events', ['question_id'], unique=False)
    op.create_index(op.f('ix_editor_events_event_type'), 'editor_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_editor_events_session_id'), 'editor_events', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_editor_events_session_id'), table_name='editor_events')
    op.drop_index(op.f('ix_editor_events_event_type'), table_name='editor_events')
    op.drop_index(op.f('ix_editor_events_question_id'), table_name='editor_events')
    op.drop_index(op.f('ix_editor_events_user_id'), table_name='editor_events')
    op.drop_index(op.f('ix_editor_events_id'), table_name='editor_events')
    op.drop_table('editor_events')
