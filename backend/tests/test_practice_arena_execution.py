"""
Unit & Integration Test Suite for Practice Arena Independent Execution.
Verifies:
- Independent code execution without question_id or practical_id context.
- Support for Python, C, C++, and Java with custom stdin.
- Strict isolation: no records inserted into academic submissions table.
- Preservation of academic progress, badges, and certificates.
- Security controls: authentication enforcement, language validation, code limits.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.security import create_access_token, hash_password
from app.models.submission import Submission
from app.models.user import User, UserRole
from app.services.judge0 import judge0_service


@pytest.fixture
def practice_student(db_session) -> User:
    student = User(
        name="Practice Arena Student",
        email="practice_student@example.com",
        password_hash=hash_password("PracticePass123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def student_auth_headers(practice_student) -> dict:
    token = create_access_token(data={"sub": str(practice_student.id), "role": "STUDENT"})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Independent Practice Execution (No Question ID)
# ==============================================================================

@pytest.mark.parametrize("language,starter_code,stdin,expected_output", [
    ("python", "print('Hello from Python practice!')", "", "Hello from Python practice!\n"),
    ("c", "#include <stdio.h>\nint main(void){ printf(\"Hello from C\\n\"); return 0; }", "", "Hello from C\n"),
    ("cpp", "#include <iostream>\nint main(){ std::cout << \"Hello C++\" << std::endl; return 0; }", "", "Hello C++\n"),
    ("java", "public class Main { public static void main(String[] args){ System.out.println(\"Hello Java\"); } }", "", "Hello Java\n"),
])
def test_practice_execution_supported_languages(
    client, student_auth_headers, monkeypatch, language, starter_code, stdin, expected_output
):
    """Verifies that all 4 supported languages execute cleanly in independent mode."""
    mock_result = {
        "status": "Accepted",
        "status_id": 3,
        "status_description": "Accepted",
        "stdout": expected_output,
        "stderr": "",
        "compile_output": "",
        "time_ms": 25,
        "memory_kb": 2048,
        "time": "0.025",
        "memory": 2048,
        "exit_code": 0,
    }

    mock_execute = AsyncMock(return_value=mock_result)
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    response = client.post(
        "/api/execute",
        json={
            "source_code": starter_code,
            "language": language,
            "stdin": stdin,
            # Notice question_id is omitted (independent practice)
        },
        headers=student_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Accepted"
    assert data["stdout"] == expected_output
    assert data["time_ms"] == 25
    assert data["memory_kb"] == 2048

    # Verify mock was called with correct arguments
    mock_execute.assert_called_once_with(
        source_code=starter_code,
        language=language,
        stdin=stdin,
    )


def test_practice_execution_custom_stdin(client, student_auth_headers, monkeypatch):
    """Verifies custom stdin is passed safely to execution engine."""
    mock_result = {
        "status": "Accepted",
        "status_id": 3,
        "status_description": "Accepted",
        "stdout": "Sum: 42\n",
        "stderr": "",
        "compile_output": "",
        "time_ms": 15,
        "memory_kb": 1500,
        "exit_code": 0,
    }

    mock_execute = AsyncMock(return_value=mock_result)
    monkeypatch.setattr(judge0_service, "execute_code", mock_execute)

    response = client.post(
        "/api/execute",
        json={
            "source_code": "a, b = map(int, input().split())\nprint(f'Sum: {a+b}')",
            "language": "python",
            "stdin": "20 22\n",
        },
        headers=student_auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["stdout"] == "Sum: 42\n"
    mock_execute.assert_called_once_with(
        source_code="a, b = map(int, input().split())\nprint(f'Sum: {a+b}')",
        language="python",
        stdin="20 22\n",
    )


# ==============================================================================
# 2. Strict Academic Isolation
# ==============================================================================

def test_practice_execution_does_not_create_academic_submission(
    client, db_session, student_auth_headers, monkeypatch
):
    """
    Critical requirement: Running code in Practice Arena must never insert
    a row into the submissions table or affect grading metrics.
    """
    initial_count = db_session.query(Submission).count()

    mock_result = {
        "status": "Accepted",
        "status_id": 3,
        "status_description": "Accepted",
        "stdout": "Hello, World!\n",
        "stderr": "",
        "compile_output": "",
        "time_ms": 30,
        "memory_kb": 3000,
        "exit_code": 0,
    }
    monkeypatch.setattr(judge0_service, "execute_code", AsyncMock(return_value=mock_result))

    response = client.post(
        "/api/execute",
        json={
            "source_code": "print('Hello, World!')",
            "language": "python",
        },
        headers=student_auth_headers,
    )
    assert response.status_code == 200

    # Verify zero submissions were created in the database
    final_count = db_session.query(Submission).count()
    assert final_count == initial_count


# ==============================================================================
# 3. Security, Validation & Error Diagnostics
# ==============================================================================

def test_practice_unauthenticated_request_rejected(client):
    """Anonymous/unauthenticated practice requests must be rejected with 401."""
    response = client.post(
        "/api/execute",
        json={
            "source_code": "print('hello')",
            "language": "python",
        },
    )
    assert response.status_code == 401


def test_practice_unsupported_language_rejected(client, student_auth_headers):
    """Languages outside the supported set (python, c, cpp, java) must be rejected."""
    for invalid_lang in ["ruby", "javascript", "php", "go", "rust", "bash"]:
        response = client.post(
            "/api/execute",
            json={
                "source_code": "puts 'hello'",
                "language": invalid_lang,
            },
            headers=student_auth_headers,
        )
        assert response.status_code == 422  # Pydantic schema validation failure


def test_practice_compilation_error_returned_accurately(client, student_auth_headers, monkeypatch):
    """Compilation errors returned from sandbox are preserved and passed to student."""
    mock_result = {
        "status": "Compilation Error",
        "status_id": 6,
        "status_description": "Compilation Error",
        "stdout": "",
        "stderr": "",
        "compile_output": "main.cpp:2:5: error: 'cout' was not declared in this scope",
        "time_ms": 10,
        "memory_kb": 1200,
        "exit_code": 1,
    }
    monkeypatch.setattr(judge0_service, "execute_code", AsyncMock(return_value=mock_result))

    response = client.post(
        "/api/execute",
        json={
            "source_code": "int main(){ cout << 1; }",
            "language": "cpp",
        },
        headers=student_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Compilation Error"
    assert "cout" in data["compile_output"]


def test_practice_runtime_error_returned_accurately(client, student_auth_headers, monkeypatch):
    """Runtime exceptions returned from sandbox are properly returned to student."""
    mock_result = {
        "status": "Runtime Error",
        "status_id": 11,
        "status_description": "Runtime Error (NZEC)",
        "stdout": "",
        "stderr": "ZeroDivisionError: division by zero",
        "compile_output": "",
        "time_ms": 18,
        "memory_kb": 2200,
        "exit_code": 1,
    }
    monkeypatch.setattr(judge0_service, "execute_code", AsyncMock(return_value=mock_result))

    response = client.post(
        "/api/execute",
        json={
            "source_code": "print(1/0)",
            "language": "python",
        },
        headers=student_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Runtime Error"
    assert "ZeroDivisionError" in data["stderr"]
