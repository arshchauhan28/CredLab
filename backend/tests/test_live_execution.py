"""
Automated Verification Suite for Execution Engine Integration.
Tests real code execution for Python, C, C++, and Java against Judge0 sandbox,
validates standard I/O (2 2 -> 4), empty input, invalid input, syntax/compilation
diagnostics, runtime exceptions, timeouts, and API failure boundaries.
"""

import pytest
from app.services.judge0 import judge0_service


@pytest.mark.asyncio
async def test_live_python_execution_with_stdin():
    """Python 3: Reads two integers from stdin, prints sum (2 2 -> 4)."""
    code = "a, b = map(int, input().split())\nprint(a + b)"
    result = await judge0_service.execute_code(source_code=code, language="python", stdin="2 2")
    assert result["status"] == "Accepted"
    assert result["status_id"] == 3
    assert result["stdout"].strip() == "4"
    assert not result["stderr"]
    assert result["time_ms"] is not None


@pytest.mark.asyncio
async def test_live_c_execution_with_stdin():
    """C: Reads two integers with scanf, prints sum (2 2 -> 4)."""
    code = """#include <stdio.h>
int main(void) {
    int a, b;
    if (scanf("%d %d", &a, &b) != 2) return 1;
    printf("%d\\n", a + b);
    return 0;
}
"""
    result = await judge0_service.execute_code(source_code=code, language="c", stdin="2 2")
    assert result["status"] == "Accepted"
    assert result["status_id"] == 3
    assert result["stdout"].strip() == "4"
    assert not result["stderr"]


@pytest.mark.asyncio
async def test_live_cpp_execution_with_stdin():
    """C++: Reads two integers with cin, prints sum (2 2 -> 4)."""
    code = """#include <iostream>
using namespace std;
int main() {
    int a, b;
    if (!(cin >> a >> b)) return 1;
    cout << a + b << '\\n';
    return 0;
}
"""
    result = await judge0_service.execute_code(source_code=code, language="cpp", stdin="2 2")
    assert result["status"] == "Accepted"
    assert result["status_id"] == 3
    assert result["stdout"].strip() == "4"
    assert not result["stderr"]


@pytest.mark.asyncio
async def test_live_java_execution_with_stdin():
    """Java: Reads two integers with Scanner, prints sum (2 2 -> 4)."""
    code = """import java.util.Scanner;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int a = sc.nextInt();
        int b = sc.nextInt();
        System.out.println(a + b);
    }
}
"""
    result = await judge0_service.execute_code(source_code=code, language="java", stdin="2 2")
    assert result["status"] == "Accepted"
    assert result["status_id"] == 3
    assert result["stdout"].strip() == "4"
    assert not result["stderr"]


@pytest.mark.asyncio
async def test_live_empty_input():
    """Program that does not require input runs successfully with empty stdin."""
    code = "print('Hello, CredLab!')"
    result = await judge0_service.execute_code(source_code=code, language="python", stdin="")
    assert result["status"] == "Accepted"
    assert result["stdout"].strip() == "Hello, CredLab!"


@pytest.mark.asyncio
async def test_live_invalid_input_runtime_error():
    """Providing non-integer input to integer parsing raises runtime exception."""
    code = "a, b = map(int, input().split())\nprint(a + b)"
    result = await judge0_service.execute_code(source_code=code, language="python", stdin="abc xyz")
    assert result["status"] == "Runtime Error"
    assert "ValueError" in result["stderr"]


@pytest.mark.asyncio
async def test_live_syntax_compilation_error():
    """C++ code missing semicolon produces Compilation Error with compiler diagnostics."""
    code = """#include <iostream>
int main() {
    std::cout << "Missing semicolon"
    return 0;
}
"""
    result = await judge0_service.execute_code(source_code=code, language="cpp")
    assert result["status"] == "Compilation Error"
    assert result["status_id"] == 6
    assert result["compile_output"] != ""
    assert "error" in result["compile_output"].lower()


@pytest.mark.asyncio
async def test_live_runtime_exception():
    """Python ZeroDivisionError produces Runtime Error status and error traceback in stderr."""
    code = "print(10 / 0)"
    result = await judge0_service.execute_code(source_code=code, language="python")
    assert result["status"] == "Runtime Error"
    assert "ZeroDivisionError" in result["stderr"]


@pytest.mark.asyncio
async def test_live_bounded_timeout():
    """Infinite loop is safely terminated at the applied CPU limit."""
    code = "while True:\n    pass"
    result = await judge0_service.execute_code(
        source_code=code, language="python", cpu_time_limit=1.0
    )
    assert result["status"] == "Time Limit Exceeded"
    assert result["status_id"] == 5


@pytest.mark.asyncio
async def test_live_repeated_submissions():
    """Repeated consecutive executions succeed reliably without stale state."""
    code = "import sys\nprint('Run 1' if sys.argv else 'Run 1')"
    r1 = await judge0_service.execute_code(source_code=code, language="python")
    r2 = await judge0_service.execute_code(source_code=code, language="python")
    assert r1["status"] == "Accepted"
    assert r2["status"] == "Accepted"
    assert r1["stdout"].strip() == "Run 1"
    assert r2["stdout"].strip() == "Run 1"


@pytest.fixture
def test_student(db_session):
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    student = User(
        name="Live Runner Student",
        email="live_runner@example.com",
        password_hash=hash_password("StudentPass123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.mark.asyncio
async def test_fastapi_execute_endpoint_live(client, test_student):
    """Verifies that the /api/execute HTTP route properly serializes live sandbox execution."""
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/execute",
        json={
            "source_code": "a, b = map(int, input().split())\nprint(a + b)",
            "language": "python",
            "stdin": "2 2",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Accepted"
    assert data["stdout"].strip() == "4"
    assert data["status_id"] == 3
    assert data["time_ms"] is not None
    assert data["time"] is not None
    assert data["memory_kb"] is not None

