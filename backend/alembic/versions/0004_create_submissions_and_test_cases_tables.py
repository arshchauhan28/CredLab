"""Create test_cases, submissions, and submission_test_results tables

Revision ID: 0004_create_submissions_and_test_cases_tables
Revises: 0003_create_editor_events_table
Create Date: 2026-10-10 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_submissions_test_cases'
down_revision: Union[str, None] = '0003_create_editor_events_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create test_cases table
    op.create_table(
        'test_cases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('input', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=False),
        sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_test_cases_id'), 'test_cases', ['id'], unique=False)
    op.create_index(op.f('ix_test_cases_question_id'), 'test_cases', ['question_id'], unique=False)

    # 2. Create submissions table
    op.create_table(
        'submissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'PENDING',
                'RUNNING',
                'ACCEPTED',
                'WRONG_ANSWER',
                'TIME_LIMIT_EXCEEDED',
                'RUNTIME_ERROR',
                'COMPILATION_ERROR',
                'INTERNAL_ERROR',
                name='submissionstatus',
                native_enum=False,
            ),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('total_test_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_test_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('memory_kb', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_submissions_id'), 'submissions', ['id'], unique=False)
    op.create_index(op.f('ix_submissions_user_id'), 'submissions', ['user_id'], unique=False)
    op.create_index(op.f('ix_submissions_question_id'), 'submissions', ['question_id'], unique=False)
    op.create_index(op.f('ix_submissions_status'), 'submissions', ['status'], unique=False)
    op.create_index(op.f('ix_submissions_created_at'), 'submissions', ['created_at'], unique=False)

    # 3. Create submission_test_results table
    op.create_table(
        'submission_test_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('test_case_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('memory_kb', sa.Integer(), nullable=True),
        sa.Column('stdout', sa.Text(), nullable=True),
        sa.Column('stderr', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_submission_test_results_id'), 'submission_test_results', ['id'], unique=False)
    op.create_index(op.f('ix_submission_test_results_submission_id'), 'submission_test_results', ['submission_id'], unique=False)
    op.create_index(op.f('ix_submission_test_results_test_case_id'), 'submission_test_results', ['test_case_id'], unique=False)

    # 4. Seed initial test_cases from existing question_examples
    # The source table must exist for this migration to succeed.
    op.execute(
        """
        INSERT INTO test_cases (
            question_id,
            input,
            expected_output,
            is_hidden,
            display_order,
            weight,
            created_at
        )
        SELECT
            question_id,
            input,
            output,
            FALSE,
            display_order,
            1.0,
            CURRENT_TIMESTAMP
        FROM question_examples
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_submission_test_results_test_case_id'), table_name='submission_test_results')
    op.drop_index(op.f('ix_submission_test_results_submission_id'), table_name='submission_test_results')
    op.drop_index(op.f('ix_submission_test_results_id'), table_name='submission_test_results')
    op.drop_table('submission_test_results')

    op.drop_index(op.f('ix_submissions_created_at'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_status'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_question_id'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_user_id'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_id'), table_name='submissions')
    op.drop_table('submissions')

    op.drop_index(op.f('ix_test_cases_question_id'), table_name='test_cases')
    op.drop_index(op.f('ix_test_cases_id'), table_name='test_cases')
    op.drop_table('test_cases')
