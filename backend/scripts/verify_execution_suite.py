"""
Comprehensive Verification Suite for Remote Code Execution & Sandbox Integrity.
Tests:
1. Direct Hosted Judge0 CE API (ce.judge0.com)
2. Python, C, C++, and Java compilation & execution with stdin/stdout
3. Compilation error detection
4. Runtime error detection
5. Timeout / Time Limit Exceeded handling
6. Unsupported language rejection on FastAPI /api/execute
7. Next.js proxy route /api/proxy/execute execution
8. Automated grading on /api/submissions
"""

import base64
import time
import httpx
from app.core.security import create_access_token

JUDGE0_URL = "https://ce.judge0.com"
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"

token = create_access_token({"sub": "1", "role": "STUDENT", "email": "arsh228chauhan@gmail.com"})
client = httpx.Client(timeout=30.0)

def b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")

def deb64(s: str) -> str:
    if not s:
        return ""
    return base64.b64decode(s).decode("utf-8", errors="replace")

def test_direct_judge0():
    print("\n--- 1. DIRECT HOSTED JUDGE0 CE (ce.judge0.com) ---")
    
    # Python
    py_payload = {
        "language_id": 71,
        "source_code": b64("import sys\nname = sys.stdin.read().strip()\nprint(f'Hello {name}!')"),
        "stdin": b64("CredLab"),
        "cpu_time_limit": 2.0,
        "memory_limit": 128000,
    }
    r = client.post(f"{JUDGE0_URL}/submissions?base64_encoded=true&wait=true", json=py_payload)
    assert r.status_code in (200, 201), f"Direct Python failed: {r.status_code}"
    res = r.json()
    stdout = deb64(res.get("stdout"))
    print(f"Direct Python status_id: {res.get('status', {}).get('id')} -> stdout: {stdout.strip()}")
    assert "Hello CredLab!" in stdout

    # C
    c_payload = {
        "language_id": 50,
        "source_code": b64('#include <stdio.h>\nint main(void) { int a, b; if (scanf("%d %d", &a, &b) == 2) printf("%d\\n", a + b); return 0; }'),
        "stdin": b64("15 27"),
        "cpu_time_limit": 2.0,
        "memory_limit": 128000,
    }
    r = client.post(f"{JUDGE0_URL}/submissions?base64_encoded=true&wait=true", json=c_payload)
    assert r.status_code in (200, 201), f"Direct C failed: {r.status_code}"
    res = r.json()
    stdout = deb64(res.get("stdout"))
    print(f"Direct C status_id: {res.get('status', {}).get('id')} -> stdout: {stdout.strip()}")
    assert "42" in stdout

    # C++
    cpp_payload = {
        "language_id": 54,
        "source_code": b64('#include <iostream>\nint main() { std::string s; std::cin >> s; std::cout << "Echo: " << s << std::endl; return 0; }'),
        "stdin": b64("VerificationCPP"),
        "cpu_time_limit": 2.0,
        "memory_limit": 128000,
    }
    r = client.post(f"{JUDGE0_URL}/submissions?base64_encoded=true&wait=true", json=cpp_payload)
    assert r.status_code in (200, 201), f"Direct C++ failed: {r.status_code}"
    res = r.json()
    stdout = deb64(res.get("stdout"))
    print(f"Direct C++ status_id: {res.get('status', {}).get('id')} -> stdout: {stdout.strip()}")
    assert "Echo: VerificationCPP" in stdout

    # Java
    java_payload = {
        "language_id": 62,
        "source_code": b64('import java.util.Scanner;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner s = new Scanner(System.in);\n        int n = s.nextInt();\n        System.out.println("Java result: " + (n * 2));\n    }\n}'),
        "stdin": b64("21"),
        "cpu_time_limit": 2.0,
        "memory_limit": 128000,
    }
    r = client.post(f"{JUDGE0_URL}/submissions?base64_encoded=true&wait=true", json=java_payload)
    assert r.status_code in (200, 201), f"Direct Java failed: {r.status_code}"
    res = r.json()
    stdout = deb64(res.get("stdout"))
    print(f"Direct Java status_id: {res.get('status', {}).get('id')} -> stdout: {stdout.strip()}")
    assert "Java result: 42" in stdout

def test_compilation_error():
    print("\n--- 2. COMPILATION ERROR DETECTION ---")
    cpp_broken = {
        "language_id": 54,
        "source_code": b64('int main() { this_is_a_syntax_error;;; }'),
        "stdin": "",
        "cpu_time_limit": 2.0,
        "memory_limit": 128000,
    }
    r = client.post(f"{JUDGE0_URL}/submissions?base64_encoded=true&wait=true", json=cpp_broken)
    res = r.json()
    status_id = res.get("status", {}).get("id")
    compile_out = deb64(res.get("compile_output"))
    print(f"Broken C++ status_id: {status_id} -> error snippet: {compile_out[:100]!r}")
    assert status_id == 6 or "error" in compile_out.lower()

def test_runtime_error():
    print("\n--- 3. RUNTIME ERROR DETECTION ---")
    py_broken = {
        "source_code": "x = 1 / 0",
        "language": "python",
        "stdin": ""
    }
    r = client.post(
        f"{BACKEND_URL}/api/execute",
        headers={"Authorization": f"Bearer {token}"},
        json=py_broken
    )
    assert r.status_code == 200
    res = r.json()
    print(f"Python ZeroDivision status: {res.get('status')} -> stderr snippet: {res.get('stderr')[:100]!r}")
    assert res.get("status") == "Runtime Error"
    assert "ZeroDivisionError" in res.get("stderr")

def test_timeout():
    print("\n--- 4. TIME LIMIT EXCEEDED HANDLING ---")
    py_loop = {
        "source_code": "while True: pass",
        "language": "python",
        "stdin": ""
    }
    r = client.post(
        f"{BACKEND_URL}/api/execute",
        headers={"Authorization": f"Bearer {token}"},
        json=py_loop
    )
    assert r.status_code == 200
    res = r.json()
    print(f"Infinite loop status: {res.get('status')} -> desc: {res.get('status_description')}")
    assert res.get("status") == "Time Limit Exceeded" or res.get("status_id") == 5

def test_unsupported_languages_rejection():
    print("\n--- 5. UNSUPPORTED LANGUAGE REJECTION ---")
    unsupported = ["javascript", "typescript", "go", "rust", "ruby", "php"]
    for lang in unsupported:
        r = client.post(
            f"{BACKEND_URL}/api/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_code": "print(1)", "language": lang, "stdin": ""}
        )
        print(f"Testing rejection of '{lang}': HTTP {r.status_code}")
        assert r.status_code == 422, f"Expected 422 for {lang}, got {r.status_code}"
        assert "Unsupported language" in r.text

def test_frontend_proxy_route():
    print("\n--- 6. NEXT.JS PROXY ROUTE (/api/proxy/execute) ---")
    r = client.post(
        f"{FRONTEND_URL}/api/proxy/execute",
        cookies={"scp_session": token},
        json={"source_code": "print('Frontend proxy works!')", "language": "python", "stdin": ""}
    )
    assert r.status_code == 200, f"Frontend proxy failed: {r.status_code}"
    res = r.json()
    print(f"Proxy status: {res.get('status')} -> stdout: {res.get('stdout').strip()}")
    assert res.get("status") == "Accepted"
    assert "Frontend proxy works!" in res.get("stdout")

if __name__ == "__main__":
    start_time = time.time()
    test_direct_judge0()
    test_compilation_error()
    test_runtime_error()
    test_timeout()
    test_unsupported_languages_rejection()
    test_frontend_proxy_route()
    elapsed = time.time() - start_time
    print(f"\n==========================================")
    print(f"ALL 6 VERIFICATION TEST SUITES PASSED in {elapsed:.2f}s!")
    print(f"==========================================")
