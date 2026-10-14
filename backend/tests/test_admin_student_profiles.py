from datetime import datetime, timezone

import pytest

from app.core.security import create_access_token, hash_password
from app.models.certificate import CompletionCertificate
from app.models.question import Question, QuestionDifficulty, QuestionStatus
from app.models.submission import (
    Submission,
    SubmissionStatus,
    SubmissionTestResult,
    TestCase,
)
from app.models.university import (
    Course,
    CourseEnrollment,
    Lab,
    LabPractical,
)
from app.models.user import User, UserRole


def make_user(db_session, *, role: UserRole, enrollment: str) -> User:
    user = User(
        name=f"Test {role.value}",
        email=f"{enrollment.lower()}@example.com",
        password_hash=hash_password("SecurePassword123"),
        role=role,
        enrollment_number=enrollment,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "email": user.email}
    )
    return {"Authorization": f"Bearer {token}"}


def make_course(db_session, admin: User, *, program="B.Tech (AI & ML)",
                year="2nd Year", semester="Semester 3", session="2026-2027") -> Course:
    course = Course(
        name=f"Subject {program} {year} {semester} {session}",
        program=program,
        year_of_study=year,
        semester=semester,
        academic_year=session,
        is_active=True,
        created_by=admin.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    return course


VALID_PROFILE = {
    "academic_course": "B.Tech (AI & ML)",
    "year_of_study": "2nd Year",
    "semester": "Semester 3",
    "academic_year": "2026-2027",
}


def test_admin_updates_profile_matches_all_dimensions_and_preserves_history(
    client, db_session
):
    admin = make_user(db_session, role=UserRole.ADMIN, enrollment="EMP2500001")
    student = make_user(db_session, role=UserRole.STUDENT, enrollment="MUR2500001")
    student.academic_course = "Data Science and AI"
    db_session.commit()

    matches = make_course(db_session, admin)
    mismatches = [
        make_course(db_session, admin, program="B.Tech (CSE)"),
        make_course(db_session, admin, year="3rd Year"),
        make_course(db_session, admin, semester="Semester 4"),
        make_course(db_session, admin, session="2027-2028"),
    ]

    old_course = make_course(
        db_session, admin, program="B.Tech (CSE)", year="1st Year",
        semester="Semester 1", session="2025-2026",
    )
    old_enrollment = CourseEnrollment(
        course_id=old_course.id, student_id=student.id, status="COMPLETED"
    )
    question = Question(
        title="Historical assessment",
        slug="historical-assessment",
        description="A preserved submission and achievement.",
        difficulty=QuestionDifficulty.EASY,
        status=QuestionStatus.PUBLISHED,
        created_by=admin.id,
    )
    db_session.add_all([old_enrollment, question])
    db_session.flush()
    lab = Lab(
        course_id=old_course.id,
        title="Historical lab",
        is_published=True,
        created_by=admin.id,
    )
    db_session.add(lab)
    db_session.flush()
    practical = LabPractical(lab_id=lab.id, question_id=question.id)
    test_case = TestCase(
        question_id=question.id,
        input="1",
        expected_output="1",
        is_hidden=False,
    )
    db_session.add_all([practical, test_case])
    db_session.flush()
    submission = Submission(
        user_id=student.id,
        question_id=question.id,
        practical_id=practical.id,
        language="python",
        source_code="print(1)",
        status=SubmissionStatus.ACCEPTED,
        total_test_cases=1,
        passed_test_cases=1,
        score=100,
    )
    db_session.add(submission)
    db_session.flush()
    result = SubmissionTestResult(
        submission_id=submission.id,
        test_case_id=test_case.id,
        status="PASSED",
        passed=True,
    )
    certificate = CompletionCertificate(
        student_id=student.id,
        practical_id=practical.id,
        submission_id=submission.id,
        key_id="test-key",
        payload={},
        payload_digest="a" * 64,
        signature="b" * 128,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add_all([result, certificate])
    db_session.commit()

    response = client.patch(
        f"/api/users/{student.id}/academic-profile",
        json=VALID_PROFILE,
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    body = response.json()
    assert {key: body[key] for key in VALID_PROFILE} == VALID_PROFILE
    assert "password_hash" not in body
    assert "password" not in body
    assert "student_id_number" not in body or body["student_id_number"] is None

    enrollment_ids = {
        row.course_id
        for row in db_session.query(CourseEnrollment)
        .filter(CourseEnrollment.student_id == student.id)
        .all()
    }
    assert matches.id in enrollment_ids
    assert old_course.id in enrollment_ids
    assert not enrollment_ids.intersection(course.id for course in mismatches)

    repeated = client.patch(
        f"/api/users/{student.id}/academic-profile",
        json=VALID_PROFILE,
        headers=auth_headers(admin),
    )
    assert repeated.status_code == 200
    assert (
        db_session.query(CourseEnrollment)
        .filter(
            CourseEnrollment.student_id == student.id,
            CourseEnrollment.course_id == matches.id,
        )
        .count()
        == 1
    )
    assert db_session.query(Submission).filter_by(id=submission.id).count() == 1
    assert db_session.query(SubmissionTestResult).filter_by(id=result.id).count() == 1
    assert (
        db_session.query(CompletionCertificate)
        .filter_by(id=certificate.id, status="ACTIVE")
        .count()
        == 1
    )
    student_headers = auth_headers(student)
    assert client.get("/api/auth/me", headers=student_headers).status_code == 200
    existing_profile = client.patch(
        "/api/users/me/academic-profile",
        json={
            "student_id_number": "STU-0001",
            **VALID_PROFILE,
        },
        headers=student_headers,
    )
    assert existing_profile.status_code == 200


@pytest.mark.parametrize(
    "role,enrollment",
    [
        (UserRole.FACULTY, "EMP2500002"),
        (UserRole.STUDENT, "MUR2500002"),
    ],
)
def test_non_admin_cannot_update_academic_profiles(
    client, db_session, role, enrollment
):
    caller = make_user(db_session, role=role, enrollment=enrollment)
    target = make_user(db_session, role=UserRole.STUDENT, enrollment="MUR2500003")

    response = client.patch(
        f"/api/users/{target.id}/academic-profile",
        json=VALID_PROFILE,
        headers=auth_headers(caller),
    )

    assert response.status_code == 403
    assert target.academic_course is None


def test_admin_profile_update_returns_404_for_missing_student(client, db_session):
    admin = make_user(db_session, role=UserRole.ADMIN, enrollment="EMP2500004")
    response = client.patch(
        "/api/users/99999/academic-profile",
        json=VALID_PROFILE,
        headers=auth_headers(admin),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("academic_course", "Data Science and AI"),
        ("year_of_study", "Year 2"),
        ("semester", "Semester 11"),
        ("academic_year", "2026-2028"),
        ("academic_year", "not-a-session"),
    ],
)
def test_admin_profile_update_rejects_invalid_academic_fields(
    client, db_session, field, value
):
    admin = make_user(db_session, role=UserRole.ADMIN, enrollment="EMP2500005")
    student = make_user(db_session, role=UserRole.STUDENT, enrollment="MUR2500005")
    payload = {**VALID_PROFILE, field: value}

    response = client.patch(
        f"/api/users/{student.id}/academic-profile",
        json=payload,
        headers=auth_headers(admin),
    )

    assert response.status_code == 422
    assert student.academic_course is None
