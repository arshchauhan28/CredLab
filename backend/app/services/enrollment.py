"""Automatic subject enrollment based on a student's academic profile."""

import re
from typing import List
from sqlalchemy.orm import Session

from app.models.university import Course, CourseEnrollment
from app.models.user import User, UserRole


def _normalized(value: str | None) -> str:
    """Normalize common formatting differences without fuzzy matching programs."""
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _normalized_program(value: str | None) -> str:
    key = _normalized(value)
    aliases = {
        "btechcse": "btechcse",
        "btechcomputerengineering": "btechcse",
        "btechaiml": "btechaiml",
        "btechartificialintelligencemachinelearning": "btechaiml",
        "btechaids": "btechaids",
        "btechartificialintelligencedatascience": "btechaids",
        "btechaianddatascience": "btechaids",
        "btechartificialintelligenceanddatascience": "btechaids",
        "btechcomputerscienceandengineering": "btechcse",
        "btechaiandml": "btechaiml",
        "mtech": "mtech",
        "bca": "bca",
        "mca": "mca",
        "diploma": "diploma",
    }
    return aliases.get(key, key)


def _student_matches_course(student: User, course: Course) -> bool:
    """All four academic dimensions must match to prevent cross-course enrollment."""
    return bool(
        student.academic_course
        and student.year_of_study
        and student.semester
        and student.academic_year
        and _normalized_program(student.academic_course) == _normalized_program(course.program)
        and _normalized(student.year_of_study) == _normalized(course.year_of_study)
        and _normalized(student.semester) == _normalized(course.semester)
        and _normalized(student.academic_year) == _normalized(course.academic_year)
    )


def auto_enroll_student_in_matching_courses(
    student: User,
    db: Session,
    *,
    commit: bool = True,
) -> List[CourseEnrollment]:
    """Enroll a student in every active subject matching their complete profile."""
    if student.role != UserRole.STUDENT or not student.is_active:
        return []
    if not all((student.academic_course, student.year_of_study, student.semester, student.academic_year)):
        return []

    active_courses = db.query(Course).filter(Course.is_active.is_(True)).all()
    new_enrollments: List[CourseEnrollment] = []
    for course in active_courses:
        if not _student_matches_course(student, course):
            continue
        existing = db.query(CourseEnrollment.id).filter(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.student_id == student.id,
        ).first()
        if not existing:
            enrollment = CourseEnrollment(course_id=course.id, student_id=student.id, status="ENROLLED")
            db.add(enrollment)
            new_enrollments.append(enrollment)

    if new_enrollments and commit:
        db.commit()
    return new_enrollments


def auto_enroll_students_in_new_course(course: Course, db: Session) -> List[CourseEnrollment]:
    """Immediately enroll active students whose full profile matches a new subject."""
    if not course.academic_year or not course.semester or not course.is_active:
        return []

    students = db.query(User).filter(
        User.role == UserRole.STUDENT,
        User.is_active.is_(True),
    ).all()
    new_enrollments: List[CourseEnrollment] = []
    for student in students:
        if not _student_matches_course(student, course):
            continue
        existing = db.query(CourseEnrollment.id).filter(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.student_id == student.id,
        ).first()
        if not existing:
            enrollment = CourseEnrollment(course_id=course.id, student_id=student.id, status="ENROLLED")
            db.add(enrollment)
            new_enrollments.append(enrollment)

    if new_enrollments:
        db.commit()
    return new_enrollments
