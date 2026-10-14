"""
Chunk 9: Sequential Practical Unlocking Test Suite.
Tests:
A. Practical-to-submission relationship (Tests 1-10)
B. Sequential unlocking progression (Tests 11-24)
C. Passing threshold and grading integrity (Tests 25-35)
D. API security, isolation, and regression (Tests 36-42)
"""

from unittest.mock import AsyncMock, patch
import pytest
from app.core.security import create_access_token, hash_password
from app.models.question import Question, QuestionDifficulty, QuestionLanguage, QuestionStatus
from app.models.submission import Submission, SubmissionStatus, SubmissionTestResult, TestCase
from app.models.university import (
    Course,
    CourseEnrollment,
    FacultyCourseAssignment,
    Lab,
    LabPractical,
)
from app.models.user import User, UserRole
from app.services.judge0 import judge0_service


# ==============================================================================
# Fixtures & Helpers
# ==============================================================================

def make_user(db_session, name: str, email: str, role: UserRole) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password("SecurePassword123"),
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


def make_question(db_session, title: str, slug: str, creator_id: int, answer: str = "42\n") -> Question:
    q = Question(
        title=title,
        slug=slug,
        description=f"Description for {title}",
        difficulty=QuestionDifficulty.EASY,
        status=QuestionStatus.PUBLISHED,
        created_by=creator_id,
    )
    db_session.add(q)
    db_session.flush()

    db_session.add(QuestionLanguage(question_id=q.id, language="python"))
    tc = TestCase(
        question_id=q.id,
        input="test_in\n",
        expected_output=answer.strip(),
        is_hidden=False,
        weight=1.0,
    )
    db_session.add(tc)
    db_session.commit()
    db_session.refresh(q)
    return q


def make_course_and_lab(db_session, admin: User, faculty: User, code: str = "CS201") -> tuple:
    course = Course(
        code=code,
        name=f"Data Structures {code}",
        semester="Fall 2026",
        academic_year="2026-2027",
        is_active=True,
        created_by=admin.id,
    )
    db_session.add(course)
    db_session.flush()

    # Assign faculty
    db_session.add(FacultyCourseAssignment(
        course_id=course.id,
        faculty_id=faculty.id,
        assigned_by=admin.id,
    ))

    # Create published Lab
    lab = Lab(
        course_id=course.id,
        title="Lab 1: Arrays & Logic",
        description="Introductory practical laboratory",
        display_order=1,
        is_published=True,
        created_by=faculty.id,
    )
    db_session.add(lab)
    db_session.commit()
    db_session.refresh(course)
    db_session.refresh(lab)
    return course, lab


def enroll_student(db_session, course: Course, student: User):
    enrollment = CourseEnrollment(
        course_id=course.id,
        student_id=student.id,
        status="ENROLLED",
    )
    db_session.add(enrollment)
    db_session.commit()
    return enrollment


def make_practical(
    db_session,
    lab: Lab,
    question: Question,
    seq: int,
    is_required: bool = True,
    threshold: float = 100.0,
    title: str = None,
) -> LabPractical:
    p = LabPractical(
        lab_id=lab.id,
        question_id=question.id,
        title=title,
        sequence_number=seq,
        is_required=is_required,
        passing_threshold=threshold,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def test_student_can_fetch_lab_practicals_and_question_details(client, db_session):
    """The dashboard's lab/practical/question request chain uses the supported IDs and shapes."""
    admin = make_user(db_session, "Admin Practical API", "admin_practical_api@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Faculty Practical API", "faculty_practical_api@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student Practical API", "student_practical_api@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CSAPI01")
    enroll_student(db_session, course, student)
    question = make_question(db_session, "Fibonacci Sequence", "fibonacci-sequence", admin.id)
    practical = make_practical(db_session, lab, question, seq=1)

    response = client.get(
        f"/api/labs/{lab.id}/practicals",
        headers=auth_header(student),
    )

    assert response.status_code == 200
    practicals = response.json()
    assert len(practicals) == 1
    assert practicals[0]["id"] == practical.id
    assert practicals[0]["lab_id"] == lab.id
    assert practicals[0]["question_id"] == question.id
    assert practicals[0]["effective_title"] == question.title
    assert practicals[0]["is_unlocked"] is True

    question_response = client.get(
        f"/api/questions/{practicals[0]['question_id']}",
        headers=auth_header(student),
    )
    assert question_response.status_code == 200
    assert question_response.json()["id"] == question.id
    assert question_response.json()["title"] == question.title
    assert question_response.json()["allowed_languages"] == ["python"]


# ==============================================================================
# Part A: Practical-to-Submission Relationship Tests (1-10)
# ==============================================================================

def test_launch_practical_and_submit_code_supported_flow(client, db_session, monkeypatch):
    """1. Launch a specific practical and submit code through the supported API flow."""
    admin = make_user(db_session, "Admin A1", "admin_a1@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof A1", "prof_a1@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student A1", "student_a1@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS101A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Problem 1", "prob-1", admin.id, answer="OK")
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "OK\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": q.id,
        "practical_id": practical.id,
        "language": "python",
        "source_code": "print('OK')",
    }
    res = client.post("/api/v1/submissions", json=payload, headers=auth_header(student))
    assert res.status_code == 201
    data = res.json()
    assert data["practical_id"] == practical.id
    assert data["status"] == "ACCEPTED"
    assert data["score"] == 100.0


def test_persisted_submission_references_exact_lab_practical_id(client, db_session, monkeypatch):
    """2. Verify the persisted submission in database references the exact LabPractical ID."""
    admin = make_user(db_session, "Admin A2", "admin_a2@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof A2", "prof_a2@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student A2", "student_a2@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS102A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Problem 2", "prob-2", admin.id, answer="HELLO")
    practical = make_practical(db_session, lab, q, seq=1)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "HELLO\n", "stderr": "", "compile_output": "", "time_ms": 15, "memory_kb": 2100}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": q.id,
        "practical_id": practical.id,
        "language": "python",
        "source_code": "print('HELLO')",
    }
    res = client.post("/api/v1/submissions", json=payload, headers=auth_header(student))
    assert res.status_code == 201
    sub_id = res.json()["id"]

    sub_in_db = db_session.query(Submission).filter(Submission.id == sub_id).first()
    assert sub_in_db is not None
    assert sub_in_db.practical_id == practical.id


def test_submission_references_question_associated_with_practical(client, db_session, monkeypatch):
    """3. Verify the submission references the question associated with that practical."""
    admin = make_user(db_session, "Admin A3", "admin_a3@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof A3", "prof_a3@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student A3", "student_a3@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS103A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Problem 3", "prob-3", admin.id, answer="ANS")
    practical = make_practical(db_session, lab, q, seq=1)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "ANS\n", "stderr": "", "compile_output": "", "time_ms": 12, "memory_kb": 2200}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {"question_id": q.id, "practical_id": practical.id, "language": "python", "source_code": "print('ANS')"}
    res = client.post("/api/v1/submissions", json=payload, headers=auth_header(student))
    assert res.status_code == 201
    data = res.json()
    assert data["question_id"] == practical.question_id == q.id


def test_practical_id_retained_across_grading_and_result_retrieval(client, db_session, monkeypatch):
    """4. Verify practical ID is retained across grading and result retrieval."""
    admin = make_user(db_session, "Admin A4", "admin_a4@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof A4", "prof_a4@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student A4", "student_a4@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS104A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Problem 4", "prob-4", admin.id, answer="42")
    practical = make_practical(db_session, lab, q, seq=1)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "42\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    res = client.post("/api/v1/submissions", json={
        "question_id": q.id,
        "practical_id": practical.id,
        "language": "python",
        "source_code": "print('42')",
    }, headers=auth_header(student))
    sub_id = res.json()["id"]

    # Retrieve submission by ID
    get_res = client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(student))
    assert get_res.status_code == 200
    assert get_res.json()["practical_id"] == practical.id


def test_associate_submission_with_mismatched_practical_question_rejected(client, db_session):
    """5. Attempt to associate a submission with a practical that references another question; expect rejection."""
    admin = make_user(db_session, "Admin A5", "admin_a5@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof A5", "prof_a5@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student A5", "student_a5@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS105A")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "Question 1", "q-1", admin.id)
    q2 = make_question(db_session, "Question 2", "q-2", admin.id)
    practical = make_practical(db_session, lab, q1, seq=1)

    # Submit for question 2 but claim it's for practical 1 (which references question 1)
    res = client.post("/api/v1/submissions", json={
        "question_id": q2.id,
        "practical_id": practical.id,
        "language": "python",
        "source_code": "print(1)",
    }, headers=auth_header(student))
    assert res.status_code == 400
    assert "does not match" in res.json()["detail"].lower()


def test_associate_submission_with_nonexistent_practical_rejected(client, db_session):
    """6. Attempt to associate a submission with a nonexistent practical; expect rejection."""
    admin = make_user(db_session, "Admin A6", "admin_a6@uni.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student A6", "student_a6@uni.edu", UserRole.STUDENT)
    q = make_question(db_session, "Question 6", "q-6", admin.id)

    res = client.post("/api/v1/submissions", json={
        "question_id": q.id,
        "practical_id": 999999,
        "language": "python",
        "source_code": "print(1)",
    }, headers=auth_header(student))
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_tamper_with_unauthorized_course_practical_rejected(client, db_session):
    """7. Attempt to submit against a practical in a course the student is not enrolled in; expect rejection."""
    admin = make_user(db_session, "Admin A7", "admin_a7@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof A7", "prof_a7@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student A7", "student_a7@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS107A")
    # DO NOT enroll student
    q = make_question(db_session, "Question 7", "q-7", admin.id)
    practical = make_practical(db_session, lab, q, seq=1)

    res = client.post("/api/v1/submissions", json={
        "question_id": q.id,
        "practical_id": practical.id,
        "language": "python",
        "source_code": "print(1)",
    }, headers=auth_header(student))
    assert res.status_code == 403
    assert "not enrolled" in res.json()["detail"].lower()


def test_submit_normal_coding_question_without_practical_backward_compatible(client, db_session, monkeypatch):
    """8. Submit a normal coding question without a university practical; verify backward compatibility."""
    admin = make_user(db_session, "Admin A8", "admin_a8@uni.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student A8", "student_a8@uni.edu", UserRole.STUDENT)
    q = make_question(db_session, "Question 8", "q-8", admin.id, answer="PASS")

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "PASS\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {"question_id": q.id, "language": "python", "source_code": "print('PASS')"}
    res = client.post("/api/v1/submissions", json=payload, headers=auth_header(student))
    assert res.status_code == 201
    data = res.json()
    assert data["practical_id"] is None
    assert data["status"] == "ACCEPTED"


def test_existing_submissions_readable_after_migration(client, db_session):
    """9. Verify existing submissions remain readable after the migration."""
    admin = make_user(db_session, "Admin A9", "admin_a9@uni.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student A9", "student_a9@uni.edu", UserRole.STUDENT)
    q = make_question(db_session, "Question 9", "q-9", admin.id)

    # Insert a legacy submission directly without practical_id
    sub = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=None,
        language="python",
        source_code="print('legacy')",
        status=SubmissionStatus.ACCEPTED,
        total_test_cases=1,
        passed_test_cases=1,
        score=100.0,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)

    res = client.get(f"/api/v1/submissions/{sub.id}", headers=auth_header(student))
    assert res.status_code == 200
    assert res.json()["practical_id"] is None


def test_submission_for_same_question_different_lab_cannot_unlock_wrong_lab_practical(client, db_session, monkeypatch):
    """10. Verify that a submission for the same question but a different lab cannot unlock the wrong lab's practical."""
    admin = make_user(db_session, "Admin A10", "admin_a10@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof A10", "prof_a10@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student A10", "student_a10@uni.edu", UserRole.STUDENT)
    course, lab1 = make_course_and_lab(db_session, admin, faculty, "CS110A")
    enroll_student(db_session, course, student)

    # Create second lab in same course
    lab2 = Lab(course_id=course.id, title="Lab 2: Trees", display_order=2, is_published=True, created_by=faculty.id)
    db_session.add(lab2)
    db_session.commit()

    q1 = make_question(db_session, "Question 10", "q-10", admin.id, answer="WIN")
    q2 = make_question(db_session, "Question 10B", "q-10b", admin.id, answer="WIN")

    # Lab 1 has practical 1 (q1)
    p_lab1 = make_practical(db_session, lab1, q1, seq=1, threshold=100.0)

    # Lab 2 has practical 1 (q1) and practical 2 (q2)
    p_lab2_seq1 = make_practical(db_session, lab2, q1, seq=1, threshold=100.0)
    p_lab2_seq2 = make_practical(db_session, lab2, q2, seq=2, threshold=100.0)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "WIN\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # Student completes p_lab1 in Lab 1
    res1 = client.post("/api/v1/submissions", json={
        "question_id": q1.id,
        "practical_id": p_lab1.id,
        "language": "python",
        "source_code": "print('WIN')",
    }, headers=auth_header(student))
    assert res1.status_code == 201

    # In Lab 2, practical 2 must still be LOCKED because Lab 2's practical 1 has NOT been completed!
    res_lab2 = client.get(f"/api/v1/labs/{lab2.id}/practicals", headers=auth_header(student))
    assert res_lab2.status_code == 200
    lab2_practicals = res_lab2.json()
    assert lab2_practicals[0]["id"] == p_lab2_seq1.id
    assert lab2_practicals[0]["status"] == "AVAILABLE"
    assert lab2_practicals[1]["id"] == p_lab2_seq2.id
    assert lab2_practicals[1]["status"] == "LOCKED"


# ==============================================================================
# Part B: Sequential Unlocking Tests (11-24)
# ==============================================================================

def test_initially_first_required_practical_is_available_and_second_is_locked(client, db_session):
    """11 & 12. Initially, the first required practical is available and the second is locked."""
    admin = make_user(db_session, "Admin B1", "admin_b1@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B1", "prof_b1@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B1", "student_b1@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS201B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B1 Q1", "b1-q1", admin.id)
    q2 = make_question(db_session, "B1 Q2", "b1-q2", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1, is_required=True)
    p2 = make_practical(db_session, lab, q2, seq=2, is_required=True)

    res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    assert res.status_code == 200
    practicals = res.json()
    assert len(practicals) == 2
    assert practicals[0]["id"] == p1.id
    assert practicals[0]["status"] == "AVAILABLE"
    assert practicals[0]["is_unlocked"] is True

    assert practicals[1]["id"] == p2.id
    assert practicals[1]["status"] == "LOCKED"
    assert practicals[1]["is_unlocked"] is False
    assert practicals[1]["lock_reason"] is not None


def test_failed_first_attempt_leaves_next_required_practical_locked(client, db_session, monkeypatch):
    """13. A failed first attempt leaves the next required practical locked."""
    admin = make_user(db_session, "Admin B2", "admin_b2@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B2", "prof_b2@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B2", "student_b2@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS202B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B2 Q1", "b2-q1", admin.id, answer="CORRECT")
    q2 = make_question(db_session, "B2 Q2", "b2-q2", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1, is_required=True)
    p2 = make_practical(db_session, lab, q2, seq=2, is_required=True)

    # Mock wrong answer
    async def mock_execute(*args, **kwargs):
        return {"status": "Wrong Answer", "status_id": 4, "stdout": "WRONG\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    res = client.post("/api/v1/submissions", json={
        "question_id": q1.id,
        "practical_id": p1.id,
        "language": "python",
        "source_code": "print('WRONG')",
    }, headers=auth_header(student))
    assert res.status_code == 201
    assert res.json()["status"] == "WRONG_ANSWER"

    # Practical 2 must still be locked
    list_res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    practicals = list_res.json()
    assert practicals[0]["status"] == "AVAILABLE"
    assert practicals[1]["status"] == "LOCKED"


def test_passing_first_attempt_unlocks_next_required_practical(client, db_session, monkeypatch):
    """14. A passing first attempt unlocks the next required practical."""
    admin = make_user(db_session, "Admin B3", "admin_b3@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B3", "prof_b3@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B3", "student_b3@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS203B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B3 Q1", "b3-q1", admin.id, answer="PASS1")
    q2 = make_question(db_session, "B3 Q2", "b3-q2", admin.id, answer="PASS2")
    p1 = make_practical(db_session, lab, q1, seq=1, is_required=True)
    p2 = make_practical(db_session, lab, q2, seq=2, is_required=True)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "PASS1\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    res = client.post("/api/v1/submissions", json={
        "question_id": q1.id,
        "practical_id": p1.id,
        "language": "python",
        "source_code": "print('PASS1')",
    }, headers=auth_header(student))
    assert res.status_code == 201

    list_res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    practicals = list_res.json()
    assert practicals[0]["status"] == "COMPLETED"
    assert practicals[1]["status"] == "AVAILABLE"
    assert practicals[1]["is_unlocked"] is True


def test_completing_practical_two_does_not_skip_incomplete_required_practical_one(client, db_session):
    """15. Completing practical two directly while practical one is incomplete is rejected."""
    admin = make_user(db_session, "Admin B4", "admin_b4@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B4", "prof_b4@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B4", "student_b4@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS204B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B4 Q1", "b4-q1", admin.id)
    q2 = make_question(db_session, "B4 Q2", "b4-q2", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1, is_required=True)
    p2 = make_practical(db_session, lab, q2, seq=2, is_required=True)

    # Student attempts to submit code for practical 2 directly
    res = client.post("/api/v1/submissions", json={
        "question_id": q2.id,
        "practical_id": p2.id,
        "language": "python",
        "source_code": "print('bypass')",
    }, headers=auth_header(student))
    assert res.status_code == 403
    assert "locked" in res.json()["detail"].lower()


def test_completing_practical_in_another_lab_does_not_unlock_this_lab(client, db_session, monkeypatch):
    """16. Completing a practical in another lab does not unlock this lab."""
    admin = make_user(db_session, "Admin B5", "admin_b5@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B5", "prof_b5@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B5", "student_b5@uni.edu", UserRole.STUDENT)
    course, labA = make_course_and_lab(db_session, admin, faculty, "CS205B")
    enroll_student(db_session, course, student)

    labB = Lab(course_id=course.id, title="Lab B", display_order=2, is_published=True, created_by=faculty.id)
    db_session.add(labB)
    db_session.commit()

    qA = make_question(db_session, "B5 QA", "b5-qa", admin.id, answer="A")
    qB1 = make_question(db_session, "B5 QB1", "b5-qb1", admin.id, answer="B1")
    qB2 = make_question(db_session, "B5 QB2", "b5-qb2", admin.id, answer="B2")

    pA = make_practical(db_session, labA, qA, seq=1)
    pB1 = make_practical(db_session, labB, qB1, seq=1)
    pB2 = make_practical(db_session, labB, qB2, seq=2)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "A\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # Student passes Lab A's practical
    res = client.post("/api/v1/submissions", json={
        "question_id": qA.id,
        "practical_id": pA.id,
        "language": "python",
        "source_code": "print('A')",
    }, headers=auth_header(student))
    assert res.status_code == 201

    # Lab B's practical 2 must still be locked
    resB = client.get(f"/api/v1/labs/{labB.id}/practicals", headers=auth_header(student))
    practicalsB = resB.json()
    assert practicalsB[1]["status"] == "LOCKED"


def test_completing_practical_for_another_student_does_not_unlock_current_student(client, db_session, monkeypatch):
    """17. Completing a practical for another student does not unlock the current student's practical."""
    admin = make_user(db_session, "Admin B6", "admin_b6@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B6", "prof_b6@uni.edu", UserRole.FACULTY)
    student1 = make_user(db_session, "Student 1", "s1@uni.edu", UserRole.STUDENT)
    student2 = make_user(db_session, "Student 2", "s2@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS206B")
    enroll_student(db_session, course, student1)
    enroll_student(db_session, course, student2)

    q1 = make_question(db_session, "B6 Q1", "b6-q1", admin.id, answer="S1")
    q2 = make_question(db_session, "B6 Q2", "b6-q2", admin.id, answer="S2")
    p1 = make_practical(db_session, lab, q1, seq=1)
    p2 = make_practical(db_session, lab, q2, seq=2)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "S1\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # Student 1 passes practical 1
    res1 = client.post("/api/v1/submissions", json={
        "question_id": q1.id,
        "practical_id": p1.id,
        "language": "python",
        "source_code": "print('S1')",
    }, headers=auth_header(student1))
    assert res1.status_code == 201

    # Practical 2 must be available for Student 1
    res_s1 = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student1))
    assert res_s1.json()[1]["status"] == "AVAILABLE"

    # Practical 2 must remain LOCKED for Student 2
    res_s2 = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student2))
    assert res_s2.json()[0]["status"] == "AVAILABLE"
    assert res_s2.json()[1]["status"] == "LOCKED"


def test_later_failed_attempt_does_not_erase_previously_earned_completion(client, db_session, monkeypatch):
    """18. A later failed attempt does not erase a previously earned completion."""
    admin = make_user(db_session, "Admin B7", "admin_b7@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B7", "prof_b7@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B7", "student_b7@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS207B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B7 Q1", "b7-q1", admin.id, answer="GOOD")
    q2 = make_question(db_session, "B7 Q2", "b7-q2", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1)
    p2 = make_practical(db_session, lab, q2, seq=2)

    # 1st attempt: passing
    async def mock_execute_pass(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "GOOD\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute_pass)

    client.post("/api/v1/submissions", json={
        "question_id": q1.id, "practical_id": p1.id, "language": "python", "source_code": "print('GOOD')",
    }, headers=auth_header(student))

    # 2nd attempt: compilation error
    async def mock_execute_fail(*args, **kwargs):
        return {"status": "Compilation Error", "status_id": 6, "stdout": "", "stderr": "SyntaxError", "compile_output": "SyntaxError", "time_ms": 0, "memory_kb": 0}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute_fail)

    client.post("/api/v1/submissions", json={
        "question_id": q1.id, "practical_id": p1.id, "language": "python", "source_code": "invalid python syntax!",
    }, headers=auth_header(student))

    # Status must STILL be COMPLETED, best score 100.0, and practical 2 AVAILABLE
    res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    practicals = res.json()
    assert practicals[0]["status"] == "COMPLETED"
    assert practicals[0]["best_score"] == 100.0
    assert practicals[1]["status"] == "AVAILABLE"


def test_required_practical_remains_blocked_if_score_below_threshold(client, db_session, monkeypatch):
    """19. A required practical remains blocked if its best score is below the configured threshold."""
    admin = make_user(db_session, "Admin B8", "admin_b8@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B8", "prof_b8@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B8", "student_b8@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS208B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B8 Q1", "b8-q1", admin.id, answer="ANSWER")
    # Add a second test case to q1 so partial credit is possible
    db_session.add(TestCase(question_id=q1.id, input="in2\n", expected_output="ANS2", is_hidden=False, weight=1.0))
    db_session.commit()

    q2 = make_question(db_session, "B8 Q2", "b8-q2", admin.id)
    # Threshold is 80.0
    p1 = make_practical(db_session, lab, q1, seq=1, threshold=80.0)
    p2 = make_practical(db_session, lab, q2, seq=2)

    # Candidate passes only 1 of 2 test cases (score = 50.0%)
    async def mock_execute_partial(source_code, language, stdin="", **kwargs):
        if "test_in" in stdin:
            return {"status": "Accepted", "status_id": 3, "stdout": "ANSWER\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
        return {"status": "Wrong Answer", "status_id": 4, "stdout": "WRONG\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute_partial)

    res = client.post("/api/v1/submissions", json={
        "question_id": q1.id, "practical_id": p1.id, "language": "python", "source_code": "partial()",
    }, headers=auth_header(student))
    assert res.json()["score"] == 50.0

    # 50.0 < 80.0, so practical 1 is NOT completed and practical 2 is LOCKED
    list_res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    practicals = list_res.json()
    assert practicals[0]["status"] == "AVAILABLE"
    assert practicals[0]["best_score"] == 50.0
    assert practicals[1]["status"] == "LOCKED"


def test_optional_practicals_do_not_block_required_progression(client, db_session, monkeypatch):
    """20. Optional practicals do not block progression through required practicals."""
    admin = make_user(db_session, "Admin B9", "admin_b9@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B9", "prof_b9@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B9", "student_b9@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS209B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B9 Q1", "b9-q1", admin.id, answer="P1")
    q2 = make_question(db_session, "B9 Q2", "b9-q2", admin.id, answer="P2")
    q3 = make_question(db_session, "B9 Q3", "b9-q3", admin.id, answer="P3")

    p1 = make_practical(db_session, lab, q1, seq=1, is_required=True)
    p2 = make_practical(db_session, lab, q2, seq=2, is_required=False)  # OPTIONAL
    p3 = make_practical(db_session, lab, q3, seq=3, is_required=True)  # REQUIRED

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "P1\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # Complete practical 1
    client.post("/api/v1/submissions", json={
        "question_id": q1.id, "practical_id": p1.id, "language": "python", "source_code": "print('P1')",
    }, headers=auth_header(student))

    # Both optional P2 and required P3 must be AVAILABLE! P2 being incomplete must not block P3.
    res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    practicals = res.json()
    assert practicals[0]["status"] == "COMPLETED"
    assert practicals[1]["status"] == "AVAILABLE"
    assert practicals[1]["is_required"] is False
    assert practicals[2]["status"] == "AVAILABLE"
    assert practicals[2]["is_required"] is True


def test_unpublished_labs_and_unenrolled_students_enforce_visibility(client, db_session):
    """21. Unpublished labs and unenrolled students follow existing authorization and visibility rules."""
    admin = make_user(db_session, "Admin B10", "admin_b10@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B10", "prof_b10@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B10", "student_b10@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS210B")

    # Lab is unpublished
    lab.is_published = False
    db_session.commit()
    enroll_student(db_session, course, student)

    # Student cannot view practicals of unpublished lab
    res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    assert res.status_code == 404


def test_empty_lab_and_lab_with_no_required_practicals_safe(client, db_session):
    """22. An empty lab and a lab with no required practicals do not crash or incorrectly expose locked tasks."""
    admin = make_user(db_session, "Admin B11", "admin_b11@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B11", "prof_b11@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B11", "student_b11@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS211B")
    enroll_student(db_session, course, student)

    # Empty lab
    res_empty = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    assert res_empty.status_code == 200
    assert res_empty.json() == []

    # Lab with all optional practicals
    q1 = make_question(db_session, "B11 Q1", "b11-q1", admin.id)
    q2 = make_question(db_session, "B11 Q2", "b11-q2", admin.id)
    make_practical(db_session, lab, q1, seq=1, is_required=False)
    make_practical(db_session, lab, q2, seq=2, is_required=False)

    res_all_opt = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    practicals = res_all_opt.json()
    assert len(practicals) == 2
    assert practicals[0]["status"] == "AVAILABLE"
    assert practicals[1]["status"] == "AVAILABLE"


def test_sequence_gaps_behave_consistently(client, db_session, monkeypatch):
    """23. Sequence gaps behave consistently with ordered progression."""
    admin = make_user(db_session, "Admin B12", "admin_b12@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B12", "prof_b12@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B12", "student_b12@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS212B")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "B12 Q1", "b12-q1", admin.id, answer="GAP1")
    q2 = make_question(db_session, "B12 Q2", "b12-q2", admin.id, answer="GAP2")
    p1 = make_practical(db_session, lab, q1, seq=5, is_required=True)
    p2 = make_practical(db_session, lab, q2, seq=20, is_required=True)

    res = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    assert res.json()[0]["status"] == "AVAILABLE"
    assert res.json()[1]["status"] == "LOCKED"

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "GAP1\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    client.post("/api/v1/submissions", json={
        "question_id": q1.id, "practical_id": p1.id, "language": "python", "source_code": "print('GAP1')",
    }, headers=auth_header(student))

    res_after = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    assert res_after.json()[0]["status"] == "COMPLETED"
    assert res_after.json()[1]["status"] == "AVAILABLE"


def test_repeated_submissions_produce_consistent_completion_state(client, db_session, monkeypatch):
    """24. Repeated submissions and multiple attempts do not produce inconsistent completion state."""
    admin = make_user(db_session, "Admin B13", "admin_b13@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof B13", "prof_b13@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student B13", "student_b13@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS213B")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "B13 Q", "b13-q", admin.id, answer="REP")
    p = make_practical(db_session, lab, q, seq=1)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "REP\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # 3 identical successful submissions
    for i in range(3):
        res = client.post("/api/v1/submissions", json={
            "question_id": q.id, "practical_id": p.id, "language": "python", "source_code": f"# run {i}\nprint('REP')",
        }, headers=auth_header(student))
        assert res.status_code == 201

    res_state = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student))
    assert res_state.json()[0]["status"] == "COMPLETED"
    assert res_state.json()[0]["best_score"] == 100.0


# ==============================================================================
# Part C: Passing Threshold and Grading Integrity Tests (25-35)
# ==============================================================================

def test_practical_defaults_to_100_percent_passing_threshold(client, db_session):
    """25. A practical defaults to a 100% passing threshold."""
    admin = make_user(db_session, "Admin C1", "admin_c1@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof C1", "prof_c1@uni.edu", UserRole.FACULTY)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS301C")
    q = make_question(db_session, "C1 Q", "c1-q", admin.id)

    res = client.post(f"/api/v1/labs/{lab.id}/practicals", json={
        "question_id": q.id,
        "sequence_number": 1,
    }, headers=auth_header(admin))
    assert res.status_code == 201
    assert res.json()["passing_threshold"] == 100.0


def test_score_meeting_configured_threshold_70_passes(client, db_session, monkeypatch):
    """26, 27, 28. Configured threshold (e.g. 70%) passes with 75% and fails below 70%."""
    admin = make_user(db_session, "Admin C2", "admin_c2@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof C2", "prof_c2@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student C2", "student_c2@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS302C")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "C2 Q", "c2-q", admin.id, answer="A")
    # Add 3 more test cases for 4 total test cases (25% each)
    for i in range(3):
        db_session.add(TestCase(question_id=q.id, input=f"in{i}\n", expected_output=f"out{i}", is_hidden=False, weight=1.0))
    db_session.commit()

    p = make_practical(db_session, lab, q, seq=1, threshold=70.0)

    # 1. Candidate passes 2 of 4 (50% < 70%) -> Fails
    async def mock_execute_50(source_code, language, stdin="", **kwargs):
        if "test_in" in stdin or "in0" in stdin:
            return {"status": "Accepted", "status_id": 3, "stdout": "A\n" if "test_in" in stdin else "out0\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
        return {"status": "Wrong Answer", "status_id": 4, "stdout": "WRONG\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute_50)

    res1 = client.post("/api/v1/submissions", json={
        "question_id": q.id, "practical_id": p.id, "language": "python", "source_code": "try1()",
    }, headers=auth_header(student))
    assert res1.json()["score"] == 50.0

    state1 = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student)).json()
    assert state1[0]["status"] == "AVAILABLE"  # Not completed

    # 2. Candidate passes 3 of 4 (75% >= 70%) -> Passes!
    async def mock_execute_75(source_code, language, stdin="", **kwargs):
        if "in2" not in stdin:
            return {"status": "Accepted", "status_id": 3, "stdout": "A\n" if "test_in" in stdin else ("out0\n" if "in0" in stdin else "out1\n"), "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
        return {"status": "Wrong Answer", "status_id": 4, "stdout": "WRONG\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute_75)

    res2 = client.post("/api/v1/submissions", json={
        "question_id": q.id, "practical_id": p.id, "language": "python", "source_code": "try2()",
    }, headers=auth_header(student))
    assert res2.json()["score"] == 75.0

    state2 = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student)).json()
    assert state2[0]["status"] == "COMPLETED"
    assert state2[0]["best_score"] == 75.0


def test_invalid_thresholds_rejected(client, db_session):
    """29. Invalid thresholds, including negative values and values above 100, are rejected."""
    admin = make_user(db_session, "Admin C3", "admin_c3@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof C3", "prof_c3@uni.edu", UserRole.FACULTY)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS303C")
    q = make_question(db_session, "C3 Q", "c3-q", admin.id)

    res_neg = client.post(f"/api/v1/labs/{lab.id}/practicals", json={
        "question_id": q.id, "sequence_number": 1, "passing_threshold": -10.0,
    }, headers=auth_header(admin))
    assert res_neg.status_code == 422

    res_over = client.post(f"/api/v1/labs/{lab.id}/practicals", json={
        "question_id": q.id, "sequence_number": 1, "passing_threshold": 120.0,
    }, headers=auth_header(admin))
    assert res_over.status_code == 422


def test_threshold_authorization_permissions(client, db_session):
    """30, 31, 32. Unauthorized students and unassigned faculty cannot change threshold, while assigned faculty & admins can."""
    admin = make_user(db_session, "Admin C4", "admin_c4@uni.edu", UserRole.ADMIN)
    assigned_faculty = make_user(db_session, "Prof C4", "prof_c4@uni.edu", UserRole.FACULTY)
    unassigned_faculty = make_user(db_session, "Prof Other", "prof_other@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student C4", "student_c4@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, assigned_faculty, "CS304C")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "C4 Q", "c4-q", admin.id)
    p = make_practical(db_session, lab, q, seq=1)

    # 30. Student attempts to change threshold -> 403
    res_student = client.patch(f"/api/v1/practicals/{p.id}", json={"passing_threshold": 50.0}, headers=auth_header(student))
    assert res_student.status_code == 403

    # 31. Unassigned faculty attempts to change threshold -> 403
    res_unassigned = client.patch(f"/api/v1/practicals/{p.id}", json={"passing_threshold": 50.0}, headers=auth_header(unassigned_faculty))
    assert res_unassigned.status_code == 403

    # 32. Assigned faculty updates threshold -> 200
    res_assigned = client.patch(f"/api/v1/practicals/{p.id}", json={"passing_threshold": 80.0}, headers=auth_header(assigned_faculty))
    assert res_assigned.status_code == 200
    assert res_assigned.json()["passing_threshold"] == 80.0

    # 32. Admin updates threshold -> 200
    res_admin = client.patch(f"/api/v1/practicals/{p.id}", json={"passing_threshold": 90.0}, headers=auth_header(admin))
    assert res_admin.status_code == 200
    assert res_admin.json()["passing_threshold"] == 90.0


def test_compilation_and_runtime_errors_never_unlock_next_practical(client, db_session, monkeypatch):
    """33. Compilation errors, runtime errors, timeouts, and internal errors never unlock the next practical."""
    admin = make_user(db_session, "Admin C5", "admin_c5@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof C5", "prof_c5@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student C5", "student_c5@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS305C")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "C5 Q1", "c5-q1", admin.id, answer="OK")
    q2 = make_question(db_session, "C5 Q2", "c5-q2", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1, threshold=0.0)  # Even with threshold 0%, errors must NEVER pass!
    p2 = make_practical(db_session, lab, q2, seq=2)

    for sid, err_status, err_name in [
        (6, "Compilation Error", "COMPILATION_ERROR"),
        (11, "Runtime Error (SIGSEGV)", "RUNTIME_ERROR"),
        (5, "Time Limit Exceeded", "TIME_LIMIT_EXCEEDED"),
        (13, "Internal Error", "INTERNAL_ERROR"),
    ]:
        def make_mock(s_id, s_text):
            async def mock_execute(*args, **kwargs):
                return {
                    "status": s_text,
                    "status_id": s_id,
                    "stdout": "",
                    "stderr": "error" if s_id != 6 else "",
                    "compile_output": "error" if s_id == 6 else "",
                    "time_ms": 0,
                    "memory_kb": 0,
                }
            return mock_execute

        monkeypatch.setattr(judge0_service, "execute_code", make_mock(sid, err_status))

        res = client.post("/api/v1/submissions", json={
            "question_id": q1.id, "practical_id": p1.id, "language": "python", "source_code": "err",
        }, headers=auth_header(student))
        assert res.json()["status"] == err_name

        # Practical 2 must remain LOCKED
        state = client.get(f"/api/v1/labs/{lab.id}/practicals", headers=auth_header(student)).json()
        assert state[1]["status"] == "LOCKED"


def test_client_cannot_forge_score_or_completion_flag(client, db_session, monkeypatch):
    """34. A client cannot forge a score, grading status or completion flag in request body."""
    admin = make_user(db_session, "Admin C6", "admin_c6@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof C6", "prof_c6@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student C6", "student_c6@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS306C")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "C6 Q", "c6-q", admin.id, answer="EXPECTED")
    p = make_practical(db_session, lab, q, seq=1)

    async def mock_execute(*args, **kwargs):
        return {"status": "Wrong Answer", "status_id": 4, "stdout": "FAIL\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # Forged fields in payload
    res = client.post("/api/v1/submissions", json={
        "question_id": q.id,
        "practical_id": p.id,
        "language": "python",
        "source_code": "print('FAIL')",
        "score": 100.0,
        "status": "ACCEPTED",
        "is_completed": True,
    }, headers=auth_header(student))
    assert res.status_code == 201
    assert res.json()["status"] == "WRONG_ANSWER"
    assert res.json()["score"] == 0.0


def test_hidden_test_case_data_remains_private(client, db_session, monkeypatch):
    """35. Hidden test-case data remains strictly private in practical submission results."""
    admin = make_user(db_session, "Admin C7", "admin_c7@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof C7", "prof_c7@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student C7", "student_c7@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS307C")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "C7 Q", "c7-q", admin.id, answer="SECRET")
    # Add hidden test case
    db_session.add(TestCase(
        question_id=q.id,
        input="SECRET_INPUT_123",
        expected_output="SECRET_OUTPUT_456",
        is_hidden=True,
        weight=2.0,
    ))
    db_session.commit()

    p = make_practical(db_session, lab, q, seq=1)

    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "SECRET\n", "stderr": "", "compile_output": "", "time_ms": 10, "memory_kb": 2000}
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    res = client.post("/api/v1/submissions", json={
        "question_id": q.id, "practical_id": p.id, "language": "python", "source_code": "code",
    }, headers=auth_header(student))
    results = res.json()["test_results"]
    hidden_case = next(r for r in results if r["is_hidden"] is True)
    assert hidden_case["input"] is None
    assert hidden_case["expected_output"] is None


# ==============================================================================
# Part D: API Security & Integration Tests (36-42)
# ==============================================================================

def test_direct_api_request_to_locked_practical_rejected(client, db_session):
    """36. Direct API requests to locked practicals are rejected with 403."""
    admin = make_user(db_session, "Admin D1", "admin_d1@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof D1", "prof_d1@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student D1", "student_d1@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS401D")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "D1 Q1", "d1-q1", admin.id)
    q2 = make_question(db_session, "D1 Q2", "d1-q2", admin.id)
    make_practical(db_session, lab, q1, seq=1)
    p2 = make_practical(db_session, lab, q2, seq=2)

    res = client.get(f"/api/v1/practicals/{p2.id}", headers=auth_header(student))
    assert res.status_code == 403
    assert "locked" in res.json()["detail"].lower()


def test_cross_student_progress_isolation(client, db_session):
    """37. Cross-student progress and submission access is strictly denied."""
    admin = make_user(db_session, "Admin D2", "admin_d2@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof D2", "prof_d2@uni.edu", UserRole.FACULTY)
    s1 = make_user(db_session, "Student D2_1", "sd2_1@uni.edu", UserRole.STUDENT)
    s2 = make_user(db_session, "Student D2_2", "sd2_2@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS402D")
    enroll_student(db_session, course, s1)
    enroll_student(db_session, course, s2)

    q = make_question(db_session, "D2 Q", "d2-q", admin.id)
    p = make_practical(db_session, lab, q, seq=1)

    # Insert submission owned by s1
    sub1 = Submission(
        user_id=s1.id, question_id=q.id, practical_id=p.id, language="python",
        source_code="print('s1')", status=SubmissionStatus.ACCEPTED, score=100.0,
    )
    db_session.add(sub1)
    db_session.commit()

    # s2 attempts to access s1's submission -> 403
    res = client.get(f"/api/v1/submissions/{sub1.id}", headers=auth_header(s2))
    assert res.status_code == 403


def test_submissions_filter_by_practical_id(client, db_session):
    """40. The submissions endpoint filters strictly by practical_id."""
    admin = make_user(db_session, "Admin D3", "admin_d3@uni.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student D3", "student_d3@uni.edu", UserRole.STUDENT)
    q = make_question(db_session, "D3 Q", "d3-q", admin.id)

    course = Course(code="CS403D", name="Course D3", semester="Fall 2026", is_active=True, created_by=admin.id)
    db_session.add(course)
    db_session.flush()
    lab = Lab(course_id=course.id, title="Lab D3", display_order=1, is_published=True, created_by=admin.id)
    db_session.add(lab)
    db_session.flush()
    p1 = make_practical(db_session, lab, q, seq=1)
    p2 = make_practical(db_session, lab, make_question(db_session, "D3 Q2", "d3-q2", admin.id), seq=2)

    sub1 = Submission(user_id=student.id, question_id=q.id, practical_id=p1.id, language="python", source_code="s1", status=SubmissionStatus.ACCEPTED, score=100.0)
    sub2 = Submission(user_id=student.id, question_id=q.id, practical_id=p2.id, language="python", source_code="s2", status=SubmissionStatus.ACCEPTED, score=100.0)
    sub3 = Submission(user_id=student.id, question_id=q.id, practical_id=None, language="python", source_code="s3", status=SubmissionStatus.ACCEPTED, score=100.0)
    db_session.add_all([sub1, sub2, sub3])
    db_session.commit()

    res = client.get(f"/api/v1/submissions?practical_id={p1.id}", headers=auth_header(student))
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == sub1.id
    assert items[0]["practical_id"] == p1.id


def test_cascade_deletion_safety_with_practical_submissions(client, db_session):
    """42. Deleting a practical that has associated submissions is rejected with 409 Conflict."""
    admin = make_user(db_session, "Admin D4", "admin_d4@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof D4", "prof_d4@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student D4", "student_d4@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS404D")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "D4 Q", "d4-q", admin.id)
    p = make_practical(db_session, lab, q, seq=1)

    sub = Submission(
        user_id=student.id, question_id=q.id, practical_id=p.id, language="python",
        source_code="code", status=SubmissionStatus.ACCEPTED, score=100.0,
    )
    db_session.add(sub)
    db_session.commit()

    # Attempt to delete practical
    del_res = client.delete(f"/api/v1/practicals/{p.id}", headers=auth_header(admin))
    assert del_res.status_code == 409
    assert "cannot delete practical" in del_res.json()["detail"].lower()
