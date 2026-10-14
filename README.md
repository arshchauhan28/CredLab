# Secure Coding Assessment Platform

A Next.js + FastAPI platform for academic subjects, automatic student enrollment, faculty-managed practical labs, sandboxed coding, test-case grading, submission history, progress statistics, and faculty-approved completion certificates.

## Current stack

- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS 4.
- **Backend:** FastAPI, Pydantic, SQLAlchemy 2, Alembic.
- **Database:** PostgreSQL.
- **Execution:** Judge0-compatible sandbox. Python, C, C++, and Java are supported by the platform's language mapping.
- **Authentication:** Argon2 password hashes, JWT session in an HttpOnly cookie, server-side Next.js API proxy.
- **AI integration:** Optional OpenAI-compatible API for hidden test generation and post-submission feedback. Automated correctness remains based on sandbox execution against saved test cases, not an AI opinion.
- **Certificates:** Existing Ed25519-signed certificate infrastructure plus faculty approval requests for lab completion.

## Main workflow

1. An administrator creates a subject by selecting academic program, year of study, semester, academic session, subject name, optional subject code, and an active faculty member.
2. Students complete their academic profile. The backend automatically enrolls them in active subjects that exactly match program, year, semester, and session. Duplicate enrollment is prevented.
3. Assigned faculty creates a lab under a subject and publishes it when ready.
4. Faculty creates a practical using a title and problem statement, selects supported languages, and can add a sample test. If AI is configured, hidden test cases can be generated from the statement.
5. Students open their enrolled labs, select an unlocked practical, write code, run it with optional custom input, and submit it for grading.
6. The backend evaluates code in Judge0 against authoritative test cases, saves submissions, and calculates progress. Required practicals unlock in sequence.
7. After all required practicals in a lab have passing submissions, the platform creates a certificate approval request. Assigned faculty can approve or reject it. Approval issues a signed certificate that the student can view and verify.

## Local setup

### 1. Backend

Use Python 3.10+.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set at least:

- `DATABASE_URL` to your PostgreSQL database URL (or set the `POSTGRES_*` fields).
- `JWT_SECRET_KEY` to a long random secret.
- `JUDGE0_API_URL` to your running Judge0 API. For a hosted Judge0 instance, set `JUDGE0_API_KEY` if required.
- `AI_API_KEY`, `AI_BASE_URL`, and `AI_MODEL` if you want AI-generated hidden tests and AI feedback. Leave `AI_API_KEY` empty to disable AI features.

Back up your database before applying migrations. From the `backend` directory:

```powershell
alembic current
alembic heads
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation: `http://127.0.0.1:8000/docs`.

### 2. Frontend

Open a second terminal:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

`frontend/.env.local` should contain:

```dotenv
API_BASE_URL=http://127.0.0.1:8000
```

Open `http://localhost:3000`. The Next.js server reads the HttpOnly `scp_session` cookie and forwards the JWT as a Bearer token to FastAPI; browser code does not need to store or expose the JWT.

## Important configuration notes

- AI features require a valid provider key and an OpenAI-compatible `/chat/completions` endpoint. Without it, faculty can still add a sample test case, but the platform cannot generate hidden tests or AI feedback.
- Student correctness is determined by sandbox execution and configured test cases. AI-generated tests should be reviewed for correctness before relying on them for high-stakes grading.
- The code editor blocks paste, drag/drop, and the context menu in the page UI. These are client-side deterrents, not a complete anti-cheating security boundary; browser restrictions can be bypassed. Authoritative grading and access control remain server-side.
- A real Judge0 service must be available for real execution. `EXECUTION_MOCK_MODE` is for tests/development only and must not be used to assess real submissions.
- `.env`, `.env.local`, private certificate keys, `.keys/`, `.venv/`, `node_modules/`, and build output must not be committed. The delivered ZIP intentionally excludes real environment files and private credentials.

## Tests and verification

From `backend` with a configured database/environment:

```powershell
pytest -q
alembic heads
```

The migration chain now ends at `0011_certificate_approval`. For isolated local tests, the test suite can run against SQLite by setting `DATABASE_URL=sqlite:///./test.db` in the shell before invoking pytest; production deployments should use PostgreSQL.

## Key routes

- Auth: `/api/auth/login`, `/api/auth/me`, `/api/users/me/academic-profile`
- Subjects and enrollments: `/api/courses`, `/api/courses/{course_id}/labs`, `/api/courses/{course_id}/faculty`, `/api/courses/{course_id}/enrollments`
- Labs and practicals: `/api/labs/{lab_id}/practicals`, `/api/practicals/{practical_id}`
- Problems and tests: `/api/questions`, `/api/questions/{question_id}/generate-tests`
- Execution and submissions: `/api/execute`, `/api/submissions`, `/api/submissions/{submission_id}/feedback`, `/api/submissions/faculty/list`
- Certificates: `/api/certificates/mine`, `/api/certificates/approvals`, `/api/certificates/approvals/{request_id}`, `/api/certificates/verify`
