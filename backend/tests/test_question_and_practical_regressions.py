"""
Regression tests for:
1. HTTP 409 question creation & slug collision handling.
2. Student practical question loading, unpublished question blocking, and role boundaries.
3. Certificate approvals listing and review compatibility endpoints.
"""

import pytest
from app.core.security import create_access_token, hash_password
from app.models.question import Question, QuestionDifficulty, QuestionLanguage, QuestionStatus
from app.models.submission import Submission, SubmissionStatus, TestCase
from app.models.university import Course, CourseEnrollment, FacultyCourseAssignment, Lab, LabPractical
from app.models.user import User, UserRole


def make_user(db_session, *, name: str, email: str, role: UserRole, job_role: str = None) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password("Password123!"),
        role=role,
        admin_job_role=job_role,
        is_active=True,
        approval_status="APPROVED",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# Question Creation & Slug Collision Tests
# ==============================================================================

def test_create_question_with_new_title(client, db_session):
    admin = make_user(db_session, name="Admin Q1", email="admin_q1@uni.edu", role=UserRole.ADMIN)

    payload = {
        "title": "Python Basics",
        "description": "Write a program that prints Hello World",
        "difficulty": "EASY",
        "status": "PUBLISHED",
        "allowed_languages": ["python"],
        "examples": [{"input": "1", "output": "Hello World"}],
    }
    res = client.post("/api/questions", json=payload, headers=auth_header(admin))
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Python Basics"
    assert data["slug"] == "python-basics"
    assert data["created_by"] == admin.id
    assert data["allowed_languages"] == ["python"]
    assert len(data["examples"]) == 1


def test_create_multiple_questions_with_same_title_generates_unique_slugs(client, db_session):
    admin = make_user(db_session, name="Admin Q2", email="admin_q2@uni.edu", role=UserRole.ADMIN)

    payload = {
        "title": "Array Sorting",
        "description": "Sort an array of integers",
        "difficulty": "MEDIUM",
        "status": "PUBLISHED",
        "allowed_languages": ["python", "cpp"],
        "examples": [],
    }

    # First question
    res1 = client.post("/api/questions", json=payload, headers=auth_header(admin))
    assert res1.status_code == 201
    assert res1.json()["slug"] == "array-sorting"

    # Second question with identical title -> array-sorting-2
    res2 = client.post("/api/questions", json=payload, headers=auth_header(admin))
    assert res2.status_code == 201
    assert res2.json()["slug"] == "array-sorting-2"

    # Third question with identical title -> array-sorting-3
    res3 = client.post("/api/questions", json=payload, headers=auth_header(admin))
    assert res3.status_code == 201
    assert res3.json()["slug"] == "array-sorting-3"

    # All three questions exist in the database with their respective IDs
    assert res1.json()["id"] != res2.json()["id"]
    assert res2.json()["id"] != res3.json()["id"]


def test_create_question_with_custom_slug(client, db_session):
    admin = make_user(db_session, name="Admin Q3", email="admin_q3@uni.edu", role=UserRole.ADMIN)

    payload = {
        "title": "Custom Problem",
        "slug": "my-special-problem-slug",
        "description": "Special problem statement description",
        "difficulty": "HARD",
        "status": "PUBLISHED",
        "allowed_languages": ["java"],
        "examples": [],
    }
    res = client.post("/api/questions", json=payload, headers=auth_header(admin))
    assert res.status_code == 201
    assert res.json()["slug"] == "my-special-problem-slug"


def test_create_question_with_duplicate_custom_slug_returns_409(client, db_session):
    admin = make_user(db_session, name="Admin Q4", email="admin_q4@uni.edu", role=UserRole.ADMIN)

    payload1 = {
        "title": "Original Problem",
        "slug": "unique-custom-slug",
        "description": "Original problem description",
        "difficulty": "EASY",
        "status": "PUBLISHED",
        "allowed_languages": ["python"],
        "examples": [],
    }
    res1 = client.post("/api/questions", json=payload1, headers=auth_header(admin))
    assert res1.status_code == 201

    payload2 = {
        "title": "Different Title But Same Slug",
        "slug": "unique-custom-slug",
        "description": "Another problem statement",
        "difficulty": "MEDIUM",
        "status": "PUBLISHED",
        "allowed_languages": ["cpp"],
        "examples": [],
    }
    res2 = client.post("/api/questions", json=payload2, headers=auth_header(admin))
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_student_cannot_create_questions(client, db_session):
    student = make_user(db_session, name="Student Hacker", email="hacker@uni.edu", role=UserRole.STUDENT)

    payload = {
        "title": "Unauthorized Problem",
        "description": "Students should not be able to create questions",
        "difficulty": "EASY",
        "allowed_languages": ["python"],
        "examples": [],
    }
    res = client.post("/api/questions", json=payload, headers=auth_header(student))
    assert res.status_code == 403


# ==============================================================================
# Student Practical Question Loading & Role Access Tests
# ==============================================================================

def test_student_can_access_published_question_via_id_and_slug(client, db_session):
    admin = make_user(db_session, name="Admin Pub", email="admin_pub@uni.edu", role=UserRole.ADMIN)
    student = make_user(db_session, name="Student Reader", email="reader@uni.edu", role=UserRole.STUDENT)

    q = Question(
        title="Published Task",
        slug="published-task",
        description="Public description",
        difficulty=QuestionDifficulty.EASY,
        status=QuestionStatus.PUBLISHED,
        created_by=admin.id,
    )
    db_session.add(q)
    db_session.commit()
    db_session.add(QuestionLanguage(question_id=q.id, language="python"))
    db_session.commit()

    # Access by ID
    res_id = client.get(f"/api/questions/{q.id}", headers=auth_header(student))
    assert res_id.status_code == 200
    assert res_id.json()["id"] == q.id
    assert res_id.json()["title"] == "Published Task"

    # Access by Slug
    res_slug = client.get(f"/api/questions/{q.slug}", headers=auth_header(student))
    assert res_slug.status_code == 200
    assert res_slug.json()["slug"] == "published-task"


def test_student_cannot_access_draft_or_unpublished_question(client, db_session):
    admin = make_user(db_session, name="Admin Draft", email="admin_draft@uni.edu", role=UserRole.ADMIN)
    student = make_user(db_session, name="Student Peeker", email="peeker@uni.edu", role=UserRole.STUDENT)

    q_draft = Question(
        title="Secret Exam Question",
        slug="secret-exam-question",
        description="Confidential description",
        difficulty=QuestionDifficulty.HARD,
        status=QuestionStatus.DRAFT,
        created_by=admin.id,
    )
    db_session.add(q_draft)
    db_session.commit()

    # Student receives 404 Not Found to prevent leaking draft existence
    res_student = client.get(f"/api/questions/{q_draft.id}", headers=auth_header(student))
    assert res_student.status_code == 404
    assert res_student.json()["detail"] == "Question not found."

    # But Admin can retrieve the draft question
    res_admin = client.get(f"/api/questions/{q_draft.id}", headers=auth_header(admin))
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "DRAFT"


def test_practical_referencing_nonexistent_question(client, db_session):
    admin = make_user(db_session, name="Admin Nonexistent", email="admin_none@uni.edu", role=UserRole.ADMIN)
    student = make_user(db_session, name="Student None", email="student_none@uni.edu", role=UserRole.STUDENT)

    # Attempting to load nonexistent question 99999
    res = client.get("/api/questions/99999", headers=auth_header(student))
    assert res.status_code == 404
    assert res.json()["detail"] == "Question not found."


def test_faculty_member_can_access_questions(client, db_session):
    faculty = make_user(db_session, name="Prof Author", email="prof_author@uni.edu", role=UserRole.FACULTY)

    q = Question(
        title="Faculty Problem",
        slug="faculty-problem",
        description="Faculty created problem",
        difficulty=QuestionDifficulty.MEDIUM,
        status=QuestionStatus.DRAFT,
        created_by=faculty.id,
    )
    db_session.add(q)
    db_session.commit()

    res = client.get(f"/api/questions/{q.id}", headers=auth_header(faculty))
    assert res.status_code == 200
    assert res.json()["title"] == "Faculty Problem"


# ==============================================================================
# Certificate Approvals Compatibility Endpoint Tests
# ==============================================================================

def test_certificate_approvals_endpoints_faculty_access(client, db_session):
    admin = make_user(db_session, name="Admin CertApp", email="admin_certapp@uni.edu", role=UserRole.ADMIN)
    faculty = make_user(db_session, name="Prof CertApp", email="prof_certapp@uni.edu", role=UserRole.FACULTY)
    student = make_user(db_session, name="Student CertApp", email="stud_certapp@uni.edu", role=UserRole.STUDENT)

    # Both /approvals and /requests return 200 with items array
    res_approvals = client.get("/api/certificates/approvals", headers=auth_header(faculty))
    assert res_approvals.status_code == 200
    assert "items" in res_approvals.json()

    res_requests = client.get("/api/certificates/requests", headers=auth_header(faculty))
    assert res_requests.status_code == 200
    assert "items" in res_requests.json()

    # Student cannot access approvals endpoint
    res_stud = client.get("/api/certificates/approvals", headers=auth_header(student))
    assert res_stud.status_code == 403


# ==============================================================================
# Supported Language Policy Tests (Only Python, C, C++, Java)
# ==============================================================================

@pytest.mark.parametrize("unsupported_lang", ["javascript", "typescript", "go", "rust", "ruby"])
def test_create_question_with_unsupported_language_returns_422(client, db_session, unsupported_lang):
    """Creating a question with unsupported language fails validation with 422."""
    admin = make_user(db_session, name=f"Admin {unsupported_lang}", email=f"admin_{unsupported_lang}@uni.edu", role=UserRole.ADMIN)

    payload = {
        "title": f"Question {unsupported_lang}",
        "description": "Problem description",
        "difficulty": "EASY",
        "status": "DRAFT",
        "allowed_languages": ["python", unsupported_lang],
        "examples": [],
    }
    res = client.post("/api/questions", json=payload, headers=auth_header(admin))
    assert res.status_code == 422
    assert "Unsupported programming language" in str(res.json())


def test_create_question_with_all_supported_languages_succeeds(client, db_session):
    """Creating a question specifying all 4 supported languages succeeds."""
    admin = make_user(db_session, name="Admin All4", email="admin_all4@uni.edu", role=UserRole.ADMIN)

    payload = {
        "title": "Quad Language Challenge",
        "description": "Problem solvable in Python, C, C++, and Java",
        "difficulty": "MEDIUM",
        "status": "PUBLISHED",
        "allowed_languages": ["python", "c", "cpp", "java"],
        "examples": [],
    }
    res = client.post("/api/questions", json=payload, headers=auth_header(admin))
    assert res.status_code == 201
    assert set(res.json()["allowed_languages"]) == {"python", "c", "cpp", "java"}


def test_update_question_with_unsupported_language_returns_422(client, db_session):
    """Updating a question with unsupported language fails validation with 422."""
    admin = make_user(db_session, name="Admin UpdateFail", email="admin_updatefail@uni.edu", role=UserRole.ADMIN)

    # First create valid question
    res = client.post("/api/questions", json={
        "title": "Valid Initial Question",
        "description": "Valid problem description",
        "difficulty": "EASY",
        "status": "DRAFT",
        "allowed_languages": ["python"],
        "examples": [],
    }, headers=auth_header(admin))
    assert res.status_code == 201
    qid = res.json()["id"]

    # Try updating with unsupported language
    update_res = client.put(f"/api/questions/{qid}", json={
        "allowed_languages": ["javascript", "rust"],
    }, headers=auth_header(admin))
    assert update_res.status_code == 422
    assert "Unsupported programming language" in str(update_res.json())
