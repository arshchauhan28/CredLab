"""Create question, language, and example tables

Revision ID: 0002_create_question_tables
Revises: 0001_create_users_table
Create Date: 2026-10-06 02:11:30.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_create_question_tables'
down_revision: Union[str, None] = '0001_create_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('input_format', sa.Text(), nullable=True),
        sa.Column('output_format', sa.Text(), nullable=True),
        sa.Column('constraints', sa.Text(), nullable=True),
        sa.Column(
            'difficulty',
            sa.Enum('EASY', 'MEDIUM', 'HARD', name='questiondifficulty', native_enum=False),
            nullable=False,
            server_default='EASY',
        ),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='questionstatus', native_enum=False),
            nullable=False,
            server_default='DRAFT',
        ),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)
    op.create_index(op.f('ix_questions_slug'), 'questions', ['slug'], unique=True)

    # 2. Create question_languages table
    op.create_table(
        'question_languages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id', 'language', name='uq_question_language'),
    )
    op.create_index(op.f('ix_question_languages_question_id'), 'question_languages', ['question_id'], unique=False)

    # 3. Create question_examples table
    op.create_table(
        'question_examples',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('input', sa.Text(), nullable=False),
        sa.Column('output', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_question_examples_question_id'), 'question_examples', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_question_examples_question_id'), table_name='question_examples')
    op.drop_table('question_examples')
    op.drop_index(op.f('ix_question_languages_question_id'), table_name='question_languages')
    op.drop_table('question_languages')
    op.drop_index(op.f('ix_questions_slug'), table_name='questions')
    op.drop_index(op.f('ix_questions_id'), table_name='questions')
    op.drop_table('questions')
