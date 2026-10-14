"""
Comprehensive Test Suite for Chunk 5: Code Execution & Sandboxing.
Validates execution endpoint, authentication, validation boundaries, error handling,
language mapping, status normalization, and Judge0 integration.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.services.judge0 import (
    PLATFORM_TO_JUDGE0_LANG_ID,
    JUDGE0_LANG_ID_TO_PLATFORM,
    Judge0Exception,
    Judge0TimeoutException,
    Judge0UnavailableException,
    judge0_service,
    normalize_judge0_status,
)


@pytest.fixture
def test_student(db_session) -> User:
    student = User(
        name="Execution Student",
        email="student_runner@example.com",
        password_hash=hash_password("StudentPass123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def student_headers(test_student) -> dict:
    token = create_access_token(data={"sub": str(test_student.id), "role": "STUDENT"})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Language Mapping & Status Normalization Unit Tests
# ==============================================================================

def test_language_mapping_bidirectional():
    """Verifies all required platform languages map to expected Judge0 IDs."""
    expected_mappings = {
        "python": 71,
        "javascript": 63,
        "typescript": 74,
        "cpp": 54,
        "java": 62,
        "c": 50,
        "go": 60,
        "rust": 73,
    }

    for lang, expected_id in expected_mappings.items():
        assert PLATFORM_TO_JUDGE0_LANG_ID[lang] == expected_id
        assert JUDGE0_LANG_ID_TO_PLATFORM[expected_id] == lang
        assert judge0_service.get_language_id(lang) == expected_id


def test_status_normalization_categories():
    """Verifies Judge0 numeric status codes normalize to clean platform categories."""
    assert normalize_judge0_status(3)[0] == "Accepted"
    assert normalize_judge0_status(4)[0] == "Wrong Answer"
    assert normalize_judge0_status(5)[0] == "Time Limit Exceeded"
    assert normalize_judge0_status(6)[0] == "Compilation Error"
    assert normalize_judge0_status(7)[0] == "Runtime Error"   # SIGSEGV
    assert normalize_judge0_status(11)[0] == "Runtime Error"  # NZEC
    assert normalize_judge0_status(12, "Memory Limit Exceeded")[0] == "Memory Limit Exceeded"
    assert normalize_judge0_status(13)[0] == "Internal Error"
    assert normalize_judge0_status(1)[0] == "Running"         # In Queue
    assert normalize_judge0_status(2)[0] == "Running"         # Processing



# ==============================================================================
# 2. Authentication & Authorization Tests
# ==============================================================================

def test_unauthenticated_request_rejected(client):
    """Execution endpoint requires valid JWT authentication."""
    response = client.post(
        "/api/execute",
        json={"source_code": "print('hello')", "language": "python"},
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_inactive_user_cannot_execute(client, test_student):
    """Inactive accounts cannot invoke code execution."""
    test_student.is_active = False
    token = create_access_token(data={"sub": str(test_student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/execute",
        json={"source_code": "print('hello')", "language": "python"},
        headers=headers,
    )
    assert response.status_code == 403


# ==============================================================================
# 3. Payload Validation Tests
# ==============================================================================

def test_empty_source_code_rejected(client, student_headers):
    """Empty or whitespace-only code is rejected with 422."""
    response = client.post(
        "/api/execute",
        json={"source_code": "   ", "language": "python"},
        headers=student_headers,
    )
    assert response.status_code == 422


def test_unsupported_language_rejected(client, student_headers):
    """Unsupported programming language is rejected with 422."""
    response = client.post(
        "/api/execute",
        json={"source_code": "puts 'hello'", "language": "ruby"},
        headers=student_headers,
    )
    assert response.status_code == 422
    assert "Unsupported language" in str(response.json())


def test_source_code_too_large_rejected(client, student_headers):
    """Excessively large source code exceeding 64KB limit is rejected with 422."""
    huge_code = "x = 1\n" * 15000  # > 70KB
    response = client.post(
        "/api/execute",
        json={"source_code": huge_code, "language": "python"},
        headers=student_headers,
    )
    assert response.status_code == 422
    assert "exceeds the maximum allowable size" in str(response.json())


def test_stdin_too_large_rejected(client, student_headers):
    """Excessively large stdin input exceeding 64KB limit is rejected with 422."""
    huge_stdin = "a" * 70000
    response = client.post(
        "/api/execute",
        json={"source_code": "print('test')", "language": "python", "stdin": huge_stdin},
        headers=student_headers,
    )
    assert response.status_code == 422
    assert "stdin exceeds the maximum allowable size" in str(response.json())


def test_malformed_request_missing_fields_rejected(client, student_headers):
    """Malformed request missing required fields is rejected with 422 Unprocessable Entity."""
    # Missing language
    res1 = client.post(
        "/api/execute",
        json={"source_code": "print('hello')"},
        headers=student_headers,
    )
    assert res1.status_code == 422

    # Missing source_code
    res2 = client.post(
        "/api/execute",
        json={"language": "python"},
        headers=student_headers,
    )
    assert res2.status_code == 422

    # Empty payload
    res3 = client.post(
        "/api/execute",
        json={},
        headers=student_headers,
    )
    assert res3.status_code == 422



# ==============================================================================
# 4. Successful Code Execution Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_authenticated_valid_python_execution(client, student_headers, monkeypatch):
    """Valid Python execution returns Accepted status and output."""
    mock_result = {
        "status": "Accepted",
        "status_id": 3,
        "status_description": "Accepted",
        "stdout": "Hello, Platform!\n",
        "stderr": "",
        "compile_output": "",
        "time_ms": 35,
        "memory_kb": 3280,
        "exit_code": 0,
    }

    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(return_value=mock_result),
    )

    response = client.post(
        "/api/execute",
        json={
            "source_code": "import sys\nprint('Hello, Platform!')",
            "language": "python",
            "stdin": "42\n",
            "question_id": 1,
        },
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Accepted"
    assert data["stdout"] == "Hello, Platform!\n"
    assert data["time_ms"] == 35
    assert data["memory_kb"] == 3280
    assert data["exit_code"] == 0


@pytest.mark.asyncio
async def test_authenticated_valid_cpp_execution(client, student_headers, monkeypatch):
    """Valid C++ execution returns Accepted with stdout."""
    mock_result = {
        "status": "Accepted",
        "status_id": 3,
        "status_description": "Accepted",
        "stdout": "42\n",
        "stderr": "",
        "compile_output": "",
        "time_ms": 12,
        "memory_kb": 1840,
        "exit_code": 0,
    }

    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(return_value=mock_result),
    )

    response = client.post(
        "/api/execute",
        json={
            "source_code": "#include <iostream>\nint main(){ std::cout << 42 << std::endl; return 0; }",
            "language": "cpp",
        },
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Accepted"
    assert data["stdout"] == "42\n"


# ==============================================================================
# 5. Execution Error Cases (Compilation, Runtime, Timeout)
# ==============================================================================

@pytest.mark.asyncio
async def test_compilation_error_response(client, student_headers, monkeypatch):
    """Compilation errors populate compile_output and status Compilation Error."""
    mock_result = {
        "status": "Compilation Error",
        "status_id": 6,
        "status_description": "Compilation Error",
        "stdout": "",
        "stderr": "",
        "compile_output": "main.cpp:2:1: error: expected ';' before 'return'",
        "time_ms": 15,
        "memory_kb": 1200,
        "exit_code": 1,
    }

    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(return_value=mock_result),
    )

    response = client.post(
        "/api/execute",
        json={
            "source_code": "#include <iostream>\nint main(){ cout << 42 return 0; }",
            "language": "cpp",
        },
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Compilation Error"
    assert "error: expected ';'" in data["compile_output"]


@pytest.mark.asyncio
async def test_runtime_error_response(client, student_headers, monkeypatch):
    """Runtime errors populate stderr and status Runtime Error."""
    mock_result = {
        "status": "Runtime Error",
        "status_id": 11,
        "status_description": "Runtime Error (NZEC)",
        "stdout": "",
        "stderr": "ZeroDivisionError: division by zero",
        "compile_output": "",
        "time_ms": 28,
        "memory_kb": 2900,
        "exit_code": 1,
    }

    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(return_value=mock_result),
    )

    response = client.post(
        "/api/execute",
        json={
            "source_code": "print(10 / 0)",
            "language": "python",
        },
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Runtime Error"
    assert "ZeroDivisionError" in data["stderr"]


@pytest.mark.asyncio
async def test_time_limit_exceeded_response(client, student_headers, monkeypatch):
    """Infinite loop returns Time Limit Exceeded."""
    mock_result = {
        "status": "Time Limit Exceeded",
        "status_id": 5,
        "status_description": "Time Limit Exceeded",
        "stdout": "",
        "stderr": "Time limit exceeded",
        "compile_output": "",
        "time_ms": 2005,
        "memory_kb": 4100,
        "exit_code": None,
    }

    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(return_value=mock_result),
    )

    response = client.post(
        "/api/execute",
        json={
            "source_code": "while True: pass",
            "language": "python",
        },
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Time Limit Exceeded"
    assert data["time_ms"] >= 2000


@pytest.mark.asyncio
async def test_memory_limit_exceeded_response(client, student_headers, monkeypatch):
    """Memory limit exhaustion returns Memory Limit Exceeded status."""
    mock_result = {
        "status": "Memory Limit Exceeded",
        "status_id": 12,
        "status_description": "Memory Limit Exceeded",
        "stdout": "",
        "stderr": "Out of memory: process exceeded memory limit of 128MB",
        "compile_output": "",
        "time_ms": 115,
        "memory_kb": 128000,
        "exit_code": 137,
    }

    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(return_value=mock_result),
    )

    response = client.post(
        "/api/execute",
        json={
            "source_code": "x = [0] * (10**8)",
            "language": "python",
        },
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Memory Limit Exceeded"
    assert data["memory_kb"] == 128000
    assert "memory limit" in data["stderr"].lower()



# ==============================================================================
# 6. Judge0 Network & Infrastructure Exceptions
# ==============================================================================

@pytest.mark.asyncio
async def test_judge0_unavailable_returns_503(client, student_headers, monkeypatch):
    """When Judge0 sandbox is offline, returns 503 Service Unavailable."""
    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(side_effect=Judge0UnavailableException("Connection refused")),
    )

    response = client.post(
        "/api/execute",
        json={"source_code": "print(1)", "language": "python"},
        headers=student_headers,
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_judge0_timeout_returns_504(client, student_headers, monkeypatch):
    """When Judge0 request times out, returns 504 Gateway Timeout."""
    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(side_effect=Judge0TimeoutException("Timeout after 10s")),
    )

    response = client.post(
        "/api/execute",
        json={"source_code": "print(1)", "language": "python"},
        headers=student_headers,
    )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_judge0_generic_error_returns_502(client, student_headers, monkeypatch):
    """When Judge0 returns an HTTP error, returns 502 Bad Gateway."""
    monkeypatch.setattr(
        judge0_service,
        "execute_code",
        AsyncMock(side_effect=Judge0Exception("Internal upstream error")),
    )

    response = client.post(
        "/api/execute",
        json={"source_code": "print(1)", "language": "python"},
        headers=student_headers,
    )

    assert response.status_code == 502


# ==============================================================================
# 7. Local Deterministic Mock Mode
# ==============================================================================

@pytest.mark.asyncio
async def test_mock_mode_execution(client, student_headers, monkeypatch):
    """When EXECUTION_MOCK_MODE=True, returns deterministic mock response."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "EXECUTION_MOCK_MODE", True)

    response = client.post(
        "/api/execute",
        json={
            "source_code": "print('hello')",
            "language": "python",
            "stdin": "test_input",
        },
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Accepted"
    assert "test_input" in data["stdout"]


@pytest.mark.asyncio
async def test_mock_mode_triggers(client, student_headers, monkeypatch):
    """Mock mode correctly simulates compilation errors, runtime errors, timeout, and memory limits."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "EXECUTION_MOCK_MODE", True)

    # 1. Compilation Error trigger
    r1 = client.post(
        "/api/execute",
        json={"source_code": "MOCK_TRIGGER: COMPILATION_ERROR\nint main()", "language": "cpp"},
        headers=student_headers,
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "Compilation Error"
    assert "error: expected ';'" in r1.json()["compile_output"]

    # 2. Runtime Error trigger
    r2 = client.post(
        "/api/execute",
        json={"source_code": "MOCK_TRIGGER: RUNTIME_ERROR\n1/0", "language": "python"},
        headers=student_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "Runtime Error"
    assert "ZeroDivisionError" in r2.json()["stderr"]

    # 3. Timeout trigger
    r3 = client.post(
        "/api/execute",
        json={"source_code": "MOCK_TRIGGER: TIMEOUT\nwhile True: pass", "language": "python"},
        headers=student_headers,
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "Time Limit Exceeded"

    # 4. Memory limit trigger
    r4 = client.post(
        "/api/execute",
        json={"source_code": "MOCK_TRIGGER: MEMORY_LIMIT\nx = []", "language": "python"},
        headers=student_headers,
    )
    assert r4.status_code == 200
    assert r4.json()["status"] == "Memory Limit Exceeded"

