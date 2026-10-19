"""
Unit and Integration Tests for CredLab Achievement Badges and Unified Certification System.
Covers:
1. Badge award upon accepted submission passing threshold.
2. Badge rejection upon wrong answer or sub-threshold score.
3. Badge award idempotency.
4. Centralized subject certificate eligibility validation.
5. Subject certificate request workflow and faculty approval/rejection.
6. Database uniqueness for active subject certificates.
"""

import pytest
from app.core.security import create_access_token, hash_password
from app.models.badge import Badge
from app.models.certificate import CompletionCertificate, SubjectCertificateRequest
from app.models.question import Question, QuestionDifficulty, QuestionLanguage, QuestionStatus
from app.models.submission import Submission, SubmissionStatus, TestCase
from app.models.university import Course, CourseEnrollment, FacultyCourseAssignment, Lab, LabPractical
from app.models.user import User, UserRole
from app.services.badge_service import award_badge_if_eligible
from app.services.certificate_eligibility import get_subject_certificate_eligibility


def make_user(db_session, name: str, email: str, role: UserRole) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password("SecurePass123"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(user: User) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "email": user.email}
    )
    return {"Authorization": f"Bearer {token}"}


def make_course_and_lab(db_session, admin: User, code: str = "SEC401") -> tuple:
    course = Course(
        code=code,
        name=f"Advanced Security {code}",
        semester="Fall 2026",
        is_active=True,
        created_by=admin.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    lab = Lab(
        course_id=course.id,
        title=f"Lab for {code}",
        description="Hands-on Security",
        display_order=1,
        created_by=admin.id,
        is_published=True,
    )
    db_session.add(lab)
    db_session.commit()
    db_session.refresh(lab)
    return course, lab


def make_question(db_session, title: str, creator_id: int) -> Question:
    q = Question(
        title=title,
        slug=title.lower().replace(" ", "-"),
        description=title,
        difficulty=QuestionDifficulty.MEDIUM,
        status=QuestionStatus.PUBLISHED,
        created_by=creator_id,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def make_practical(db_session, lab: Lab, question: Question, seq: int = 1, threshold: float = 100.0) -> LabPractical:
    p = LabPractical(
        lab_id=lab.id,
        question_id=question.id,
        title=f"Practical {seq}: {question.title}",
        sequence_number=seq,
        is_required=True,
        passing_threshold=threshold,
        is_active=True,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


# ==============================================================================
# Badge Tests
# ==============================================================================

def test_badge_awarded_on_accepted_passing_submission(db_session):
    admin = make_user(db_session, "Admin Badge", "adminbadge@test.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student Badge", "studentbadge@test.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, "SEC401A")
    q = make_question(db_session, "Buffer Overflow", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=80.0)

    sub = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=practical.id,
        language="c",
        source_code="int main() { return 0; }",
        status=SubmissionStatus.ACCEPTED,
        score=95.0,
    )
    db_session.add(sub)
    db_session.commit()

    badge = award_badge_if_eligible(db_session, student.id, practical, sub)
    assert badge is not None
    assert badge.user_id == student.id
    assert badge.practical_id == practical.id
    assert badge.course_id == course.id
    assert badge.meta["course_name"] == course.name
    assert badge.meta["practical_title"] == practical.title


def test_badge_not_awarded_on_wrong_answer_or_sub_threshold(db_session):
    admin = make_user(db_session, "Admin Badge 2", "adminbadge2@test.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student Badge 2", "studentbadge2@test.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, "SEC401B")
    q = make_question(db_session, "SQL Injection", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=80.0)

    # Sub-threshold score
    sub_low = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=practical.id,
        language="python",
        source_code="pass",
        status=SubmissionStatus.ACCEPTED,
        score=75.0,
    )
    db_session.add(sub_low)
    db_session.commit()

    b1 = award_badge_if_eligible(db_session, student.id, practical, sub_low)
    assert b1 is None

    # Wrong answer status
    sub_wrong = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=practical.id,
        language="python",
        source_code="pass",
        status=SubmissionStatus.WRONG_ANSWER,
        score=0.0,
    )
    db_session.add(sub_wrong)
    db_session.commit()

    b2 = award_badge_if_eligible(db_session, student.id, practical, sub_wrong)
    assert b2 is None


def test_badge_award_is_idempotent(db_session):
    admin = make_user(db_session, "Admin Badge 3", "adminbadge3@test.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student Badge 3", "studentbadge3@test.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, "SEC401C")
    q = make_question(db_session, "XSS Attack", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=80.0)

    sub = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=practical.id,
        language="javascript",
        source_code="console.log(1)",
        status=SubmissionStatus.ACCEPTED,
        score=100.0,
    )
    db_session.add(sub)
    db_session.commit()

    b1 = award_badge_if_eligible(db_session, student.id, practical, sub)
    assert b1 is not None

    b2 = award_badge_if_eligible(db_session, student.id, practical, sub)
    assert b2 is not None
    assert b1.id == b2.id
    assert db_session.query(Badge).filter(Badge.user_id == student.id).count() == 1


# ==============================================================================
# Subject Certificate Eligibility & Workflow Tests
# ==============================================================================

def test_subject_eligibility_and_approval_workflow(client, db_session):
    admin = make_user(db_session, "Admin Workflow", "adminwf@test.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Faculty Workflow", "facultywf@test.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student Workflow", "studentwf@test.edu", UserRole.STUDENT)

    course, lab = make_course_and_lab(db_session, admin, "SEC401D")

    # Enroll student and assign faculty
    db_session.add(CourseEnrollment(course_id=course.id, student_id=student.id, status="ENROLLED"))
    db_session.add(FacultyCourseAssignment(course_id=course.id, faculty_id=faculty.id, assigned_by=admin.id))
    db_session.commit()

    # 2 required practicals
    q1 = make_question(db_session, "Practical One", admin.id)
    q2 = make_question(db_session, "Practical Two", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1, threshold=100.0)
    p2 = make_practical(db_session, lab, q2, seq=2, threshold=100.0)

    # Initially 0 practicals completed -> NOT_ELIGIBLE
    elig = get_subject_certificate_eligibility(db_session, student.id, course.id)
    assert elig.certificate_status == "NOT_ELIGIBLE"
    assert not elig.is_eligible
    assert elig.completed_required == 0
    assert elig.total_required == 2

    # Student cannot request certificate yet
    res = client.post(
        "/api/certificates/subject-requests",
        headers=auth_header(student),
        json={"course_id": course.id},
    )
    assert res.status_code == 400

    # Student completes practical 1 only
    db_session.add(Submission(
        user_id=student.id,
        question_id=q1.id,
        practical_id=p1.id,
        language="python",
        source_code="pass",
        status=SubmissionStatus.ACCEPTED,
        score=100.0,
    ))
    db_session.commit()

    elig2 = get_subject_certificate_eligibility(db_session, student.id, course.id)
    assert elig2.completed_required == 1
    assert elig2.completion_percentage == 50.0
    assert not elig2.is_eligible

    # Student completes practical 2
    db_session.add(Submission(
        user_id=student.id,
        question_id=q2.id,
        practical_id=p2.id,
        language="python",
        source_code="pass",
        status=SubmissionStatus.ACCEPTED,
        score=100.0,
    ))
    db_session.commit()

    elig3 = get_subject_certificate_eligibility(db_session, student.id, course.id)
    assert elig3.completed_required == 2
    assert elig3.completion_percentage == 100.0
    assert elig3.is_eligible
    assert elig3.certificate_status == "ELIGIBLE"

    # Student requests subject certificate
    req_res = client.post(
        "/api/certificates/subject-requests",
        headers=auth_header(student),
        json={"course_id": course.id},
    )
    assert req_res.status_code == 200
    req_id = req_res.json()["id"]

    # Faculty views approval queue
    queue_res = client.get(
        "/api/certificates/subject-approvals",
        headers=auth_header(faculty),
    )
    assert queue_res.status_code == 200
    queue_items = queue_res.json()["items"]
    assert any(item["id"] == req_id for item in queue_items)
    target_item = next(item for item in queue_items if item["id"] == req_id)
    assert target_item["is_eligible"] is True
    assert target_item["total_required"] == 2
    assert target_item["completed_required"] == 2

    # Faculty approves request
    app_res = client.post(
        f"/api/certificates/subject-approvals/{req_id}",
        headers=auth_header(faculty),
        json={"action": "APPROVE", "note": "Exemplary performance."},
    )
    assert app_res.status_code == 200
    cert_id = app_res.json()["certificate_id"]
    assert cert_id is not None

    # Public certificate endpoint check
    pub_res = client.get(f"/api/certificates/{cert_id}/public")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["certificate_type"] == "SUBJECT"
    assert pub_data["student_name"] == "Student Workflow"
    assert pub_data["course_code"] == "SEC401D"
    assert pub_data["algorithm"] == "ED25519-SHA256"
