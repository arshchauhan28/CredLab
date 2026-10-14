"""Create university management tables (courses, labs, practicals, faculty assignments, enrollments)

Revision ID: 0005_create_university_management_tables
Revises: 0004_create_submissions_and_test_cases_tables
Create Date: 2026-10-10 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_university_management'
down_revision: Union[str, None] = '0004_submissions_test_cases'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Support FACULTY role check constraint in PostgreSQL if present
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS userrole")
            op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role")
            op.execute("ALTER TABLE users ADD CONSTRAINT ck_users_role CHECK (role IN ('STUDENT', 'FACULTY', 'ADMIN'))")
        except Exception:
            pass

    # 1. Create courses table
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('semester', sa.String(length=50), nullable=False),
        sa.Column('academic_year', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)
    op.create_index(op.f('ix_courses_code'), 'courses', ['code'], unique=True)

    # 2. Create faculty_course_assignments table
    op.create_table(
        'faculty_course_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('faculty_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['faculty_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', 'faculty_id', name='uq_course_faculty_assignment'),
    )
    op.create_index(op.f('ix_faculty_course_assignments_id'), 'faculty_course_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_faculty_course_assignments_course_id'), 'faculty_course_assignments', ['course_id'], unique=False)
    op.create_index(op.f('ix_faculty_course_assignments_faculty_id'), 'faculty_course_assignments', ['faculty_id'], unique=False)

    # 3. Create course_enrollments table
    op.create_table(
        'course_enrollments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ENROLLED'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', 'student_id', name='uq_course_student_enrollment'),
    )
    op.create_index(op.f('ix_course_enrollments_id'), 'course_enrollments', ['id'], unique=False)
    op.create_index(op.f('ix_course_enrollments_course_id'), 'course_enrollments', ['course_id'], unique=False)
    op.create_index(op.f('ix_course_enrollments_student_id'), 'course_enrollments', ['student_id'], unique=False)

    # 4. Create labs table
    op.create_table(
        'labs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_labs_id'), 'labs', ['id'], unique=False)
    op.create_index(op.f('ix_labs_course_id'), 'labs', ['course_id'], unique=False)

    # 5. Create lab_practicals table
    op.create_table(
        'lab_practicals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lab_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('sequence_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_id', 'sequence_number', name='uq_lab_practical_sequence'),
        sa.UniqueConstraint('lab_id', 'question_id', name='uq_lab_practical_question'),
    )
    op.create_index(op.f('ix_lab_practicals_id'), 'lab_practicals', ['id'], unique=False)
    op.create_index(op.f('ix_lab_practicals_lab_id'), 'lab_practicals', ['lab_id'], unique=False)
    op.create_index(op.f('ix_lab_practicals_question_id'), 'lab_practicals', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lab_practicals_question_id'), table_name='lab_practicals')
    op.drop_index(op.f('ix_lab_practicals_lab_id'), table_name='lab_practicals')
    op.drop_index(op.f('ix_lab_practicals_id'), table_name='lab_practicals')
    op.drop_table('lab_practicals')

    op.drop_index(op.f('ix_labs_course_id'), table_name='labs')
    op.drop_index(op.f('ix_labs_id'), table_name='labs')
    op.drop_table('labs')

    op.drop_index(op.f('ix_course_enrollments_student_id'), table_name='course_enrollments')
    op.drop_index(op.f('ix_course_enrollments_course_id'), table_name='course_enrollments')
    op.drop_index(op.f('ix_course_enrollments_id'), table_name='course_enrollments')
    op.drop_table('course_enrollments')

    op.drop_index(op.f('ix_faculty_course_assignments_faculty_id'), table_name='faculty_course_assignments')
    op.drop_index(op.f('ix_faculty_course_assignments_course_id'), table_name='faculty_course_assignments')
    op.drop_index(op.f('ix_faculty_course_assignments_id'), table_name='faculty_course_assignments')
    op.drop_table('faculty_course_assignments')

    op.drop_index(op.f('ix_courses_code'), table_name='courses')
    op.drop_index(op.f('ix_courses_id'), table_name='courses')
    op.drop_table('courses')
