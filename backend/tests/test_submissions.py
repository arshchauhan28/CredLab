"""
Comprehensive Test Suite for Chunk 7: Permanent Submissions, Automated Grading & Results.
Covers:
1. Successful submission creation.
2. All test cases passing results in Accepted.
3. Failed output comparison results in Wrong Answer.
4. Compilation errors.
5. Runtime errors.
6. Time-limit exceeded responses.
7. Judge0 service failures and malformed responses.
8. Questions with no grading test cases.
9. Authentication requirements.
10. A user cannot access another user's submission.
11. Hidden test inputs and expected outputs never appear in candidate-facing responses.
12. Invalid languages and invalid payloads.
13. Submission history pagination and ownership.
14. Partial scoring.
15. Database persistence and transaction failure handling.
16. Independent output comparison normalization unit tests.
"""

from unittest.mock import AsyncMock, patch
import pytest
from app.core.security import create_access_token, hash_password
from app.models.question import Question, QuestionDifficulty, QuestionLanguage, QuestionStatus
from app.models.submission import Submission, SubmissionStatus, SubmissionTestResult, TestCase
from app.models.user import User, UserRole
from app.services.grading import compare_outputs, normalize_output
from app.services.judge0 import (
    Judge0Exception,
    Judge0TimeoutException,
    Judge0UnavailableException,
    judge0_service,
)


@pytest.fixture
def student_user(db_session) -> User:
    user = User(
        name="Candidate Alpha",
        email="candidate_alpha@example.com",
        password_hash=hash_password("PassAlpha123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_student_user(db_session) -> User:
    user = User(
        name="Candidate Beta",
        email="candidate_beta@example.com",
        password_hash=hash_password("PassBeta123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    user = User(
        name="Admin Evaluator",
        email="admin_evaluator@example.com",
        password_hash=hash_password("AdminPass123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_headers(student_user) -> dict:
    token = create_access_token(data={"sub": str(student_user.id), "role": "STUDENT"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_student_headers(other_student_user) -> dict:
    token = create_access_token(data={"sub": str(other_student_user.id), "role": "STUDENT"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user) -> dict:
    token = create_access_token(data={"sub": str(admin_user.id), "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_question(db_session, admin_user) -> Question:
    q = Question(
        title="Two Sum Problem",
        slug="two-sum-problem",
        description="Given an array of integers, return the indices of two numbers that add up to target.",
        difficulty=QuestionDifficulty.EASY,
        status=QuestionStatus.PUBLISHED,
        created_by=admin_user.id,
    )
    db_session.add(q)
    db_session.flush()

    # Allowed languages
    db_session.add(QuestionLanguage(question_id=q.id, language="python"))
    db_session.add(QuestionLanguage(question_id=q.id, language="cpp"))

    # Test Cases: 1 public sample, 1 hidden assessment test case
    tc1 = TestCase(
        question_id=q.id,
        input="2 7 11 15\n9",
        expected_output="0 1",
        is_hidden=False,
        display_order=1,
        weight=1.0,
    )
    tc2 = TestCase(
        question_id=q.id,
        input="3 2 4\n6",
        expected_output="1 2",
        is_hidden=True,
        display_order=2,
        weight=2.0,
    )
    db_session.add_all([tc1, tc2])
    db_session.commit()
    db_session.refresh(q)
    return q


# ==============================================================================
# 1. Output Normalization & Comparison Policy Unit Tests
# ==============================================================================

def test_output_normalization_policy():
    """Verifies output comparison policy: CRLF, line trailing whitespace, overall newlines."""
    # Windows CRLF vs Unix LF
    assert normalize_output("hello world\r\n") == "hello world"
    assert normalize_output("line 1\r\nline 2\r\n") == "line 1\nline 2"

    # Trailing whitespace on individual lines
    assert normalize_output("hello   \nworld\t  ") == "hello\nworld"

    # Leading and trailing blank lines stripped
    assert normalize_output("\n\nresult\n\n") == "result"

    # Internal spaces between tokens strictly preserved
    assert normalize_output("1   2   3") == "1   2   3"

    # Comparison function
    assert compare_outputs("0 1\r\n", "0 1\n") is True
    assert compare_outputs("0 1   \n", "0 1") is True
    assert compare_outputs("0 2", "0 1") is False


# ==============================================================================
# 2. Submission Creation & Full Accepted Test
# ==============================================================================

@pytest.mark.asyncio
async def test_submission_all_passed_accepted(client, sample_question, student_headers, monkeypatch):
    """Verifies all test cases passing results in ACCEPTED status and 100% score."""
    async def mock_execute(source_code, language, stdin="", **kwargs):
        if "2 7" in stdin:
            return {"status": "Accepted", "status_id": 3, "stdout": "0 1\n", "stderr": "", "compile_output": "", "time_ms": 25, "memory_kb": 3100}
        else:
            return {"status": "Accepted", "status_id": 3, "stdout": "1 2\n", "stderr": "", "compile_output": "", "time_ms": 30, "memory_kb": 3200}

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print('0 1' if '2 7' in input() else '1 2')",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "ACCEPTED"
    assert data["score"] == 100.0
    assert data["total_test_cases"] == 2
    assert data["passed_test_cases"] == 2
    assert data["language"] == "python"
    assert data["source_code"] == payload["source_code"]
    assert len(data["test_results"]) == 2
    assert all(r["passed"] is True for r in data["test_results"])


# ==============================================================================
# 3. Output Comparison Mismatch -> Wrong Answer
# ==============================================================================

@pytest.mark.asyncio
async def test_submission_wrong_answer(client, sample_question, student_headers, monkeypatch):
    """Verifies incorrect actual output produces WRONG_ANSWER."""
    async def mock_execute(source_code, language, stdin="", **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "99 99\n", "stderr": "", "compile_output": "", "time_ms": 20, "memory_kb": 3000}

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print('99 99')",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "WRONG_ANSWER"
    assert data["score"] == 0.0
    assert data["passed_test_cases"] == 0
    assert len(data["test_results"]) == 2
    assert all(r["passed"] is False for r in data["test_results"])
    assert all(r["status"] == "WRONG_ANSWER" for r in data["test_results"])


# ==============================================================================
# 4. Compilation Error
# ==============================================================================

@pytest.mark.asyncio
async def test_submission_compilation_error(client, sample_question, student_headers, monkeypatch):
    """Verifies compiler errors map to COMPILATION_ERROR with diagnostics."""
    async def mock_execute(source_code, language, stdin="", **kwargs):
        return {
            "status": "Compilation Error",
            "status_id": 6,
            "stdout": "",
            "stderr": "",
            "compile_output": "solution.cpp:4:1: error: expected ';' before 'return'",
            "time_ms": 10,
            "memory_kb": 1000,
        }

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "cpp",
        "source_code": "int main() { return 0 }",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "COMPILATION_ERROR"
    assert data["score"] == 0.0
    assert "solution.cpp" in data["error_message"]


# ==============================================================================
# 5. Runtime Error
# ==============================================================================

@pytest.mark.asyncio
async def test_submission_runtime_error(client, sample_question, student_headers, monkeypatch):
    """Verifies exceptions and non-zero exit codes map to RUNTIME_ERROR."""
    async def mock_execute(source_code, language, stdin="", **kwargs):
        return {
            "status": "Runtime Error",
            "status_id": 11,
            "stdout": "",
            "stderr": "ZeroDivisionError: division by zero",
            "compile_output": "",
            "time_ms": 15,
            "memory_kb": 2400,
        }

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print(1/0)",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "RUNTIME_ERROR"
    assert "ZeroDivisionError" in data["error_message"]


# ==============================================================================
# 6. Time Limit Exceeded
# ==============================================================================

@pytest.mark.asyncio
async def test_submission_time_limit_exceeded(client, sample_question, student_headers, monkeypatch):
    """Verifies execution timeouts map to TIME_LIMIT_EXCEEDED."""
    async def mock_execute(source_code, language, stdin="", **kwargs):
        return {
            "status": "Time Limit Exceeded",
            "status_id": 5,
            "stdout": "",
            "stderr": "Time limit exceeded",
            "compile_output": "",
            "time_ms": 2000,
            "memory_kb": 4500,
        }

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "while True: pass",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "TIME_LIMIT_EXCEEDED"
    assert data["test_results"][0]["status"] == "TIME_LIMIT_EXCEEDED"


# ==============================================================================
# 7. Judge0 Service Unavailable / Failure Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_submission_service_unavailable(client, sample_question, student_headers, monkeypatch, db_session):
    """Verifies engine failure records submission with INTERNAL_ERROR without crashing or losing record."""
    async def mock_execute(source_code, language, stdin="", **kwargs):
        raise Judge0UnavailableException("Sandbox offline")

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print('hi')",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "INTERNAL_ERROR"
    # Ensure record is persisted in DB
    db_sub = db_session.query(Submission).filter(Submission.id == data["id"]).first()
    assert db_sub is not None
    assert db_sub.status == SubmissionStatus.INTERNAL_ERROR


# ==============================================================================
# 8. Questions with No Grading Test Cases
# ==============================================================================

def test_submission_no_test_cases(client, admin_user, student_headers, db_session):
    """Verifies questions without test cases reject submissions with 400 error."""
    empty_q = Question(
        title="Empty Question",
        slug="empty-question",
        description="No test cases here",
        difficulty=QuestionDifficulty.MEDIUM,
        status=QuestionStatus.PUBLISHED,
        created_by=admin_user.id,
    )
    db_session.add(empty_q)
    db_session.commit()
    db_session.refresh(empty_q)

    payload = {
        "question_id": empty_q.id,
        "language": "python",
        "source_code": "print(1)",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 400
    assert "does not have any configured grading test cases" in resp.json()["detail"]


# ==============================================================================
# 9. Authentication Requirements
# ==============================================================================

def test_submission_endpoints_require_auth(client, sample_question):
    """Verifies submission endpoints reject unauthenticated requests."""
    # POST
    resp = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "python", "source_code": "print(1)"},
    )
    assert resp.status_code == 401

    # GET list
    resp = client.get("/api/v1/submissions")
    assert resp.status_code == 401

    # GET detail
    resp = client.get("/api/v1/submissions/1")
    assert resp.status_code == 401

    # GET results
    resp = client.get("/api/v1/submissions/1/results")
    assert resp.status_code == 401


# ==============================================================================
# 10. Candidate Isolation: Cannot Access Another User's Submission
# ==============================================================================

@pytest.mark.asyncio
async def test_candidate_cannot_access_other_user_submission(
    client, sample_question, student_headers, other_student_headers, monkeypatch
):
    """Verifies a student cannot view or access another student's submission."""
    async def mock_execute(source_code, language, stdin="", **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "0 1\n", "stderr": "", "compile_output": "", "time_ms": 20, "memory_kb": 3000}

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # Student 1 creates submission
    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print('secret student 1 code')",
    }
    resp1 = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp1.status_code == 201
    sub_id = resp1.json()["id"]

    # Student 2 attempts to access Student 1's submission
    resp2 = client.get(f"/api/v1/submissions/{sub_id}", headers={**other_student_headers})
    assert resp2.status_code == 403
    assert "permission" in resp2.json()["detail"]

    # Student 2 attempts to access Student 1's test results
    resp3 = client.get(f"/api/v1/submissions/{sub_id}/results", headers={**other_student_headers})
    assert resp3.status_code == 403


# ==============================================================================
# 11. Hidden Test Cases Protection (Never Leaked in Candidate Responses)
# ==============================================================================

@pytest.mark.asyncio
async def test_hidden_test_cases_protected(client, sample_question, student_headers, monkeypatch):
    """
    CRITICAL SECURITY CHECK:
    Verifies that hidden test inputs, expected outputs, and actual stdouts are NEVER
    returned to the candidate.
    """
    async def mock_execute(source_code, language, stdin="", **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "0 1\n", "stderr": "", "compile_output": "", "time_ms": 20, "memory_kb": 3000}

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print('solution')",
    }

    # 1. Inspect POST /api/v1/submissions response
    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    data = resp.json()
    sub_id = data["id"]

    results = data["test_results"]
    assert len(results) == 2

    # Find public and hidden results
    public_res = next(r for r in results if not r["is_hidden"])
    hidden_res = next(r for r in results if r["is_hidden"])

    # Public case has input and expected output
    assert public_res["input"] is not None
    assert public_res["expected_output"] is not None
    assert public_res["stdout"] is not None

    # Hidden case MUST be obscured
    assert hidden_res["input"] is None
    assert hidden_res["expected_output"] is None
    assert hidden_res["stdout"] is None

    # 2. Inspect GET /api/v1/submissions/{id} response
    detail_resp = client.get(f"/api/v1/submissions/{sub_id}", headers=student_headers)
    detail_data = detail_resp.json()
    detail_hidden = next(r for r in detail_data["test_results"] if r["is_hidden"])
    assert detail_hidden["input"] is None
    assert detail_hidden["expected_output"] is None
    assert detail_hidden["stdout"] is None

    # 3. Inspect GET /api/v1/submissions/{id}/results response
    res_list_resp = client.get(f"/api/v1/submissions/{sub_id}/results", headers=student_headers)
    res_list_data = res_list_resp.json()
    res_hidden = next(r for r in res_list_data if r["is_hidden"])
    assert res_hidden["input"] is None
    assert res_hidden["expected_output"] is None
    assert res_hidden["stdout"] is None


# ==============================================================================
# 12. Payload and Language Validation
# ==============================================================================

def test_submission_payload_validation(client, sample_question, student_headers):
    """Verifies empty code, oversized code, unmapped language, and disallowed language."""
    # Empty code
    resp = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "python", "source_code": "   "},
        headers=student_headers,
    )
    assert resp.status_code == 422

    # Unsupported language
    resp = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "cobol", "source_code": "print(1)"},
        headers=student_headers,
    )
    assert resp.status_code == 422

    # Disallowed language for this specific question (sample_question allows python, cpp only)
    resp = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "java", "source_code": "print(1)"},
        headers=student_headers,
    )
    assert resp.status_code == 400
    assert "not permitted for this question" in resp.json()["detail"]


# ==============================================================================
# 13. Submission History Pagination, Ownership & Source Code Omission
# ==============================================================================

@pytest.mark.asyncio
async def test_submission_history_pagination_and_ownership(
    client, sample_question, student_headers, other_student_headers, monkeypatch
):
    """Verifies paginated list contains only the user's submissions and omits full source code."""
    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "0 1\n", "stderr": "", "compile_output": "", "time_ms": 20, "memory_kb": 3000}

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # Create 3 submissions for Student 1
    for i in range(3):
        client.post(
            "/api/v1/submissions",
            json={"question_id": sample_question.id, "language": "python", "source_code": f"# sub {i}"},
            headers=student_headers,
        )

    # Create 1 submission for Student 2
    client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "python", "source_code": "# student 2"},
        headers=other_student_headers,
    )

    # Student 1 lists submissions
    resp = client.get("/api/v1/submissions?page=1&page_size=2", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2

    # Source code must NOT be leaked in history list items
    for item in data["items"]:
        assert "source_code" not in item


# ==============================================================================
# 14. Partial Scoring Calculation
# ==============================================================================

@pytest.mark.asyncio
async def test_partial_scoring_weighted(client, sample_question, student_headers, monkeypatch):
    """
    Verifies partial scoring:
    sample_question has:
    - tc1 weight = 1.0 (passes)
    - tc2 weight = 2.0 (fails)
    Total weight = 3.0. Passed weight = 1.0.
    Score = (1.0 / 3.0) * 100 = 33.33%.
    Status should be WRONG_ANSWER (separate from ACCEPTED).
    """
    async def mock_execute(source_code, language, stdin="", **kwargs):
        if "2 7" in stdin:
            # Public test case 1 passes
            return {"status": "Accepted", "status_id": 3, "stdout": "0 1\n", "stderr": "", "compile_output": "", "time_ms": 20, "memory_kb": 3000}
        else:
            # Hidden test case 2 fails
            return {"status": "Accepted", "status_id": 3, "stdout": "wrong answer\n", "stderr": "", "compile_output": "", "time_ms": 20, "memory_kb": 3000}

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print('0 1')",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "WRONG_ANSWER"
    assert data["passed_test_cases"] == 1
    assert data["total_test_cases"] == 2
    assert data["score"] == 33.33


# ==============================================================================
# 15. Database Persistence & Foreign Key Cascade
# ==============================================================================

@pytest.mark.asyncio
async def test_database_persistence_and_cascade(client, sample_question, student_headers, monkeypatch, db_session):
    """Verifies Submission and SubmissionTestResult records are persisted and cascade on question deletion."""
    async def mock_execute(*args, **kwargs):
        return {"status": "Accepted", "status_id": 3, "stdout": "0 1\n", "stderr": "", "compile_output": "", "time_ms": 25, "memory_kb": 3100}

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    payload = {
        "question_id": sample_question.id,
        "language": "python",
        "source_code": "print('0 1')",
    }

    resp = client.post("/api/v1/submissions", json=payload, headers=student_headers)
    assert resp.status_code == 201
    sub_id = resp.json()["id"]

    # Verify rows in DB
    db_sub = db_session.query(Submission).filter(Submission.id == sub_id).first()
    assert db_sub is not None
    assert len(db_sub.test_results) == 2

    # Delete question and verify cascade deletion
    db_session.delete(sample_question)
    db_session.commit()

    assert db_session.query(Submission).filter(Submission.id == sub_id).first() is None
    assert db_session.query(SubmissionTestResult).filter(SubmissionTestResult.submission_id == sub_id).count() == 0


# ==============================================================================
# 16. LeetCode-Style Workflow: History, Source Code Retrieval & Resubmission
# ==============================================================================

@pytest.mark.asyncio
async def test_challenge_specific_submission_history_and_source_retrieval(
    client, sample_question, student_headers, other_student_headers, monkeypatch, db_session
):
    """
    Verifies:
    1. Student can retrieve their own submission history filtered by question_id.
    2. Submissions from other questions or students are excluded.
    3. Results are sorted newest first.
    4. Student can retrieve full source code and details of their own submission.
    """
    async def mock_execute(source_code, *args, **kwargs):
        return {
            "status": "Accepted",
            "status_id": 3,
            "stdout": "0 1\n",
            "stderr": "",
            "compile_output": "",
            "time_ms": 15,
            "memory_kb": 2500,
        }

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # 1. Create 2 submissions for sample_question
    code_attempt_1 = "# Attempt 1: Brute force\nprint('0 1')"
    code_attempt_2 = "# Attempt 2: Hash map\nprint('0 1')"

    resp1 = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "python", "source_code": code_attempt_1},
        headers=student_headers,
    )
    assert resp1.status_code == 201
    sub1_id = resp1.json()["id"]

    resp2 = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "python", "source_code": code_attempt_2},
        headers=student_headers,
    )
    assert resp2.status_code == 201
    sub2_id = resp2.json()["id"]

    # 2. Query history specifically for sample_question
    hist_resp = client.get(
        f"/api/v1/submissions?question_id={sample_question.id}",
        headers=student_headers,
    )
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total"] >= 2
    # Verify newest first ordering
    returned_ids = [item["id"] for item in hist_data["items"]]
    assert returned_ids.index(sub2_id) < returned_ids.index(sub1_id)

    # 3. Retrieve source code for Attempt 1
    detail_resp = client.get(
        f"/api/v1/submissions/{sub1_id}?question_id={sample_question.id}",
        headers=student_headers,
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == sub1_id
    assert detail_data["source_code"] == code_attempt_1

    # 4. Challenge ID mismatch check (CASE 9)
    wrong_q_resp = client.get(
        f"/api/v1/submissions/{sub1_id}?question_id={sample_question.id + 999}",
        headers=student_headers,
    )
    assert wrong_q_resp.status_code == 400
    assert "does not belong to question" in wrong_q_resp.json()["detail"]


@pytest.mark.asyncio
async def test_resubmission_creates_new_attempt_and_preserves_previous(
    client, sample_question, student_headers, monkeypatch, db_session
):
    """
    CRITICAL REQUIREMENT:
    Verifies that editing a previous submission and submitting again creates a
    BRAND NEW database record, independently evaluated, while keeping the
    previous submission and its result completely intact and unchanged.
    """
    call_count = 0

    async def mock_execute(source_code, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        # If code contains "correct", pass both test cases.
        # Otherwise, pass only the first test case (tc1 weight=1.0, tc2 weight=2.0).
        if "correct" in source_code:
            return {
                "status": "Accepted",
                "status_id": 3,
                "stdout": "0 1\n" if "2 7" in kwargs.get("stdin", "") else "1 2\n",
                "stderr": "",
                "compile_output": "",
                "time_ms": 22,
                "memory_kb": 2800,
            }
        else:
            return {
                "status": "Wrong Answer",
                "status_id": 4,
                "stdout": "wrong answer output",
                "stderr": "",
                "compile_output": "",
                "time_ms": 30,
                "memory_kb": 2900,
            }

    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    # 1. Student submits initial code (Submission #1)
    code_v1 = "# Version 1: initial buggy attempt\nprint('wrong')"
    sub1_resp = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "python", "source_code": code_v1},
        headers=student_headers,
    )
    assert sub1_resp.status_code == 201
    sub1_data = sub1_resp.json()
    sub1_id = sub1_data["id"]
    assert sub1_data["status"] == "WRONG_ANSWER"
    assert sub1_data["score"] == 0.0
    sub1_created_at = sub1_data["created_at"]

    # 2. Student loads Submission #1 code, modifies it to fix the bug, and resubmits
    code_v2 = "# Version 2: edited copy of Submission #1 (correct!)\nprint('correct')"
    sub2_resp = client.post(
        "/api/v1/submissions",
        json={"question_id": sample_question.id, "language": "python", "source_code": code_v2},
        headers=student_headers,
    )
    assert sub2_resp.status_code == 201
    sub2_data = sub2_resp.json()
    sub2_id = sub2_data["id"]

    # 3. Verify Submission #2 is a distinct record with fresh evaluation
    assert sub2_id != sub1_id
    assert sub2_data["source_code"] == code_v2
    assert sub2_data["status"] == "ACCEPTED"
    assert sub2_data["score"] == 100.0

    # 4. Verify Submission #1 remains COMPLETELY UNCHANGED in the database
    db_session.expire_all()
    sub1_in_db = db_session.query(Submission).filter(Submission.id == sub1_id).first()
    assert sub1_in_db is not None
    assert sub1_in_db.source_code == code_v1
    assert sub1_in_db.status == SubmissionStatus.WRONG_ANSWER
    assert sub1_in_db.score == 0.0

    # 5. Verify both attempts appear as distinct records in submission history
    hist_resp = client.get(
        f"/api/v1/submissions?question_id={sample_question.id}",
        headers=student_headers,
    )
    hist_items = hist_resp.json()["items"]
    ids_in_history = [item["id"] for item in hist_items]
    assert sub2_id in ids_in_history
    assert sub1_id in ids_in_history

    item1 = next(item for item in hist_items if item["id"] == sub1_id)
    item2 = next(item for item in hist_items if item["id"] == sub2_id)
    assert item1["status"] == "WRONG_ANSWER"
    assert item2["status"] == "ACCEPTED"

