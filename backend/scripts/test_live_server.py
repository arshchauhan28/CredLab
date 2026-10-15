import httpx
from app.core.security import create_access_token

token = create_access_token({"sub": "1", "role": "STUDENT", "email": "arsh228chauhan@gmail.com"})
client = httpx.Client(timeout=30.0)

test_cases = [
    ("python", "print('Hello Python')", "Hello Python\n"),
    ("c", '#include <stdio.h>\nint main(void) { printf("Hello C\\n"); return 0; }', "Hello C\n"),
    ("cpp", '#include <iostream>\nint main() { std::cout << "Hello C++" << std::endl; return 0; }', "Hello C++\n"),
    ("java", 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello Java");\n    }\n}', "Hello Java\n"),
]

print("=== TESTING EXECUTION FOR ALL 4 LANGUAGES VIA PROXY ===")
for lang, code, expected in test_cases:
    try:
        r = client.post(
            "http://localhost:3000/api/proxy/execute",
            cookies={"scp_session": token},
            json={"source_code": code, "language": lang, "stdin": ""}
        )
        print(f"[{lang.upper()}] Status: {r.status_code}")
        print(f"[{lang.upper()}] Response: {r.text}")
    except Exception as e:
        print(f"[{lang.upper()}] Error: {e}")

print("\n=== TESTING SUBMISSION VIA PROXY FOR PRACTICAL 1 ===")
# Practical 1 is Fibonacci Sequence
fib_code = """
import sys

def main():
    lines = sys.stdin.read().split()
    if not lines:
        return
    n = int(lines[0])
    if n <= 0:
        return
    fib = [0, 1]
    while len(fib) < n:
        fib.append(fib[-1] + fib[-2])
    print(' '.join(str(x) for x in fib[:n]))

if __name__ == '__main__':
    main()
"""

try:
    r_sub = client.post(
        "http://localhost:3000/api/proxy/submissions",
        cookies={"scp_session": token},
        json={
            "question_id": 1,
            "practical_id": 1,
            "language": "python",
            "source_code": fib_code,
        }
    )
    print(f"Submission Status: {r_sub.status_code}")
    print(f"Submission Body: {r_sub.text}")
except Exception as e:
    print(f"Submission Error: {e}")

