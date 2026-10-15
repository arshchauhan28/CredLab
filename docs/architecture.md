# Architecture Overview

## Secure Coding Assessment Platform

The **Secure Coding Assessment Platform** is designed to provide high-integrity, automated programming examinations and assignments with real-time code execution, proctoring signals, and automated evaluation.

---

## High-Level System Architecture

```
+-------------------------------------------------------------+
|                      Client Layer                           |
|       React + Vite + TypeScript (Single Page App)           |
|  - Modern Dark UI & Glassmorphism Components                |
|  - Centralized API Service Layer (HTTP Client)              |
|  - Real-time Health / Database Diagnostic Ping              |
+------------------------------+------------------------------+
                               |
                               | REST API (JSON)
                               | CORS Enabled
                               v
+-------------------------------------------------------------+
|                     Application Layer                       |
|               FastAPI (Python Asynchronous ASGI)             |
|  - Uvicorn Application Server                               |
|  - Pydantic Settings & Environment Validation               |
|  - Modular Versioned Routing (/api/v1)                      |
|  - Error Handling & Request Lifecycle Management            |
+------------------------------+------------------------------+
                               |
                               | SQLAlchemy 2.0 ORM
                               | Connection Pooling (pre-ping)
                               v
+-------------------------------------------------------------+
|                       Data Layer                            |
|                  PostgreSQL Database                        |
|  - Managed Schema Migrations via Alembic                    |
|  - Strict Referential Integrity                             |
|  - ACID Compliant Transactions                              |
+-------------------------------------------------------------+
```

---

## Implementation Status

### Foundation Chunk (Chunk 1) - Complete
- [x] Complete project directory structure established
- [x] React + Vite + TypeScript frontend with modern design system
- [x] FastAPI asynchronous backend configured with Uvicorn
- [x] PostgreSQL configuration via environment variables
- [x] SQLAlchemy 2.0 engine and session generator configured
- [x] Alembic migration environment initialized
- [x] CORS middleware configured for frontend origin
- [x] Health endpoint `GET /api/health` returning `{"status": "ok"}`
- [x] Database test endpoint `GET /api/db-test` and CLI diagnostic script
- [x] Safe `.env.example` configurations and `.gitignore`

### Authentication & User Management (Chunk 2) - Complete
- [x] User model with Argon2id password hashing and role-based access control (STUDENT vs ADMIN)
- [x] Public registration strictly constrained to STUDENT role
- [x] Signed JWT tokens (HS256) with role, subject, and expiration claims
- [x] Protected endpoints with `get_current_user`, `get_current_student`, and `get_current_admin` dependencies
- [x] Complete AuthContext, login/register forms, and protected routes

### Question Bank & Test Case Management (Chunk 3) - Complete
- [x] Question, QuestionExample, and QuestionLanguage ORM models with strict constraints
- [x] Difficulty and Status controlled via enums (EASY, MEDIUM, HARD; DRAFT, PUBLISHED, ARCHIVED)
- [x] Admin-only Question CRUD endpoints and authoring UI
- [x] Public catalog showing only PUBLISHED questions for students with difficulty filtering
- [x] Comprehensive test suite (29/29 passing) covering authentication and question management

### Coding Workspace & Problem Solving View (Chunk 4) - Complete
- [x] Interactive Monaco Editor integration (`@monaco-editor/react`) with syntax highlighting
- [x] Multi-pane resizable layout (draggable horizontal & vertical splitters)
- [x] Language switcher with starter boilerplate templates (Python, C, C++, Java)
- [x] Question-filtered allowed languages enforcement
- [x] Local code persistence and auto-save in localStorage per problem and language
- [x] Reset code to boilerplate with confirmation dialog
- [x] Interactive test runner console drawer with sample test cases and custom input (stdin)
- [x] Keyboard shortcuts (`Ctrl+S` save, `Ctrl+Enter` run) and layout mode toggles (Split, Problem Only, Editor Only)

### Code Execution & Sandboxing (Chunk 5) - Complete
- [x] Sandboxed execution integration with Judge0 CE / Extra CE
- [x] Asynchronous HTTP client service (`Judge0Service` using `httpx.AsyncClient`)
- [x] Centralized bidirectional language ID mapping (Python, C, C++, Java)
- [x] Server-controlled execution boundaries (CPU time limit: 2.0s, Memory limit: 128 MB)
- [x] Input and source code size protection (64 KB maximum)
- [x] Status normalization (Accepted, Compilation Error, Runtime Error, Time Limit Exceeded, Memory Limit Exceeded, Internal Error)
- [x] JWT authentication required via `get_current_user` dependency (client cannot forge user ID)
- [x] Optional `question_id` for execution context; strictly stateless with no submission records or hidden test grading
- [x] Offline deterministic local mock mode via `EXECUTION_MOCK_MODE=True`
- [x] Frontend execution client (`executeCode` in `src/api/execution.ts`) with automatic Bearer token injection
- [x] Interactive execution console in `CodingWorkspace.tsx` displaying real stdout, stderr, compile diagnostics, runtime (ms), and memory (KB)
- [x] Robust error handling for service offline (503), timeouts (504), and upstream errors (502)
- [x] Comprehensive automated test suite (49/49 tests passing)

---

## ⚡ Code Execution & Sandboxing Architecture (Chunk 5)

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Workspace                   │
│   (CodingWorkspace.tsx -> executionApi.executeCode)   │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/execute
                            │ Authorization: Bearer <jwt>
                            │ Payload: {source_code, language, stdin, question_id?}
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Endpoint                     │
│               (/api/v1/endpoints/execution.py)         │
│  1. Authenticate via get_current_user dependency       │
│  2. Validate payload boundaries (<= 64KB, supported)  │
│  3. Map language slug -> Judge0 language ID            │
└───────────────────────────┬────────────────────────────┘
                            │ httpx.AsyncClient (wait=true / poll)
                            │ Server-enforced limits:
                            │   cpu_time_limit = 2.0s
                            │   memory_limit   = 128000 KB
                            ▼
┌────────────────────────────────────────────────────────┐
│              Judge0 Sandboxed Execution Engine         │
│               (Docker Container Sandbox / CE)          │
│  - Executes user process in isolated cgroup namespace │
│  - Captures stdout, stderr, compile output, exit code  │
│  - Measures CPU time (s) and resident memory (KB)     │
└───────────────────────────┬────────────────────────────┘
                            │ Raw Judge0 JSON response
                            ▼
┌────────────────────────────────────────────────────────┐
│                Normalized Response Parser              │
│               (app/services/judge0.py)                 │
│  - Status normalized to platform category              │
│  - Formats time_ms and memory_kb                       │
│  - Sanitizes output (no leaked server infrastructure)  │
└───────────────────────────┬────────────────────────────┘
                            │ Return ExecuteCodeResponse (HTTP 200)
                            ▼
┌────────────────────────────────────────────────────────┐
│             Execution Console Terminal                 │
│  - Displays Status badge, Runtime (ms), Memory (KB)    │
│  - Displays stdout, stderr, and compilation errors     │
└────────────────────────────────────────────────────────┘
```

### Centralized Language Mapping

| Platform Slug | Judge0 ID | Language Runtime / Compiler |
| :--- | :--- | :--- |
| `python` | `71` | Python 3.8.1 |
| `c` | `50` | C (GCC 9.2.0) |
| `cpp` | `54` | C++ (GCC 9.2.0) |
| `java` | `62` | Java (OpenJDK 13.0.1) |

### Local Development & Mock Mode
When running without a local Judge0 Docker cluster, developers can enable:
```ini
EXECUTION_MOCK_MODE=True
```
in `.env`. The backend returns deterministic simulated execution responses including support for mock error triggers:
- `MOCK_TRIGGER: COMPILATION_ERROR` in source code triggers simulated compilation diagnostic.
- `MOCK_TRIGGER: RUNTIME_ERROR` in source code triggers simulated `ZeroDivisionError` on stderr.
- `MOCK_TRIGGER: TIMEOUT` in source code triggers simulated Time Limit Exceeded.
- `MOCK_TRIGGER: MEMORY_LIMIT` in source code triggers simulated Memory Limit Exceeded.

### Scope Guardrails
> **IMPORTANT:** Chunk 5 executes code and presents execution outputs for user verification. It does **NOT** evaluate solutions against hidden test cases, compute persistent grades, or save submissions in the database. Automated grading, test evaluation suites, and submissions are reserved for **Chunk 7**. Anti-cheating monitoring and keystroke telemetry belong to **Chunk 6**.

---

## 🛡️ Anti-Cheating & Editor Activity Monitoring (Chunk 6) - Complete

### 1. Purpose & Deterrence Philosophy
Chunk 6 enforces editor-level integrity restrictions and activity telemetry without deploying invasive rootkits, OS hooks, or spyware. Browser-side restrictions act as deterrents against casual unauthorized pasting and cutting. Client telemetry provides an audit trail of editing activity for future evaluation.

> **Security Limitation Note:** Browser-side JavaScript restrictions are client-side deterrents and do not constitute an absolute cryptographic boundary. Dedicated adversaries with developer tools can theoretically manipulate client state. Telemetry timestamps, character deltas, and server-side auditing provide the tamper-evident layer.

### 2. Editor Restrictions (Monaco Integration)
Applied strictly to the code editor in `CodingWorkspace.tsx`:
- **Blocked Actions**:
  - Clipboard Copy (`Ctrl+C`, `Cmd+C`, DOM `copy` event, context menu)
  - Clipboard Cut (`Ctrl+X`, `Cmd+X`, DOM `cut` event, context menu)
  - Clipboard Paste (`Ctrl+V`, `Cmd+V`, `Ctrl+Shift+V`, `Cmd+Shift+V`, `Shift+Insert`, DOM `paste` event, context menu)
  - Drag-and-drop text insertion (DOM `drop` and `dragover` events)
- **Subtle Feedback**: Non-disruptive warning notification with a 2.5s cooldown to avoid spamming the student.
- **Allowed Normal Operations**: Normal typing, text selection, arrow keys, Backspace/Delete, undo/redo (`Ctrl+Z`, `Ctrl+Y`), multi-line editing, language switching, settings adjustment, Run Code & Judge0 sandboxed execution.

### 3. Normalized Event Types & Telemetry Schema
Events are queued and sent in bounded batches to `POST /api/editor-events`:
- `TYPE`: Character additions (normal typing, large insertions, replacements) with character deltas.
- `DELETE`: Character deletions with removal counts.
- `PASTE_ATTEMPT`: Intercepted paste attempts via shortcut, context menu, or browser event.
- `COPY_ATTEMPT`: Intercepted copy attempts.
- `CUT_ATTEMPT`: Intercepted cut attempts.
- `DROP_ATTEMPT`: Intercepted drag-and-drop text insertion attempts.

### 4. Data Minimization & Privacy
- **Source code is NEVER stored** in event telemetry records.
- **Clipboard contents are NEVER captured, stored, or transmitted**.
- Events store character counts, change categories (`typing`, `deletion`, `replacement`, `large_insertion`), event types, and timestamps.
- Authenticated `user_id` is derived strictly from the JWT session on the server.

### 5. Ingestion API: `POST /api/editor-events`
- **Authentication**: Required (`Bearer <jwt>`).
- **Batch Size Limit**: 1 to 200 events per request.
- **Metadata Size Limit**: Max 4 KB per event.
- **Database Table**: `editor_events` (managed via migration `0003_create_editor_events_table`).

---

## 📦 Submissions, Automated Grading & Evaluation (Chunk 7) - Complete

### 1. High-Level Submission & Grading Pipeline

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Workspace                   │
│      CodingWorkspace.tsx -> "Submit Solution"          │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/submissions
                            │ Authorization: Bearer <jwt>
                            │ Payload: {question_id, language, source_code}
                            ▼
┌────────────────────────────────────────────────────────┐
│                FastAPI Submission Endpoint             │
│            (/api/v1/endpoints/submissions.py)          │
│  1. Authenticate candidate via JWT (get_current_user)  │
│  2. Validate payload boundaries (source_code <= 64KB)  │
│  3. Verify question exists and has test cases          │
│  4. Verify language allowed for question               │
│  5. Persist initial Submission record (PENDING)        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              Authoritative Grading Engine              │
│               (app/services/grading.py)                │
│  1. Query backend TestCase records (public + hidden)   │
│  2. Execute solution for each test case via Judge0     │
│  3. Parse raw output and compare with expected output  │
│  4. Persist SubmissionTestResult for each test case    │
│  5. Compute aggregate score, status, and metrics       │
│  6. Commit transaction updates to Submission record    │
└───────────────────────────┬────────────────────────────┘
                            │ Safe response serialization
                            │ (Obscure hidden test inputs & outputs)
                            ▼
┌────────────────────────────────────────────────────────┐
│           Candidate Evaluation Results Modal           │
│  - Aggregate Status Badge (ACCEPTED / WRONG_ANSWER...) │
│  - Calculated Score & Passed Test Cases Counter        │
│  - Max Runtime (ms) & Peak Memory (KB) Metrics         │
│  - Breakdown of individual test cases (Safe candidate) │
│  - Historical Submissions Explorer Drawer              │
└────────────────────────────────────────────────────────┘
```

### 2. Database Schema & Models
Managed via Alembic migration `backend/alembic/versions/0004_create_submissions_and_test_cases_tables.py`:

- **`test_cases`**:
  - `id` (PK, Integer, Indexed)
  - `question_id` (FK `questions.id`, ON DELETE CASCADE, Indexed)
  - `input` (Text, standard input provided to process)
  - `expected_output` (Text, authoritative expected output)
  - `is_hidden` (Boolean, default False)
  - `display_order` (Integer, default 0)
  - `weight` (Float, default 1.0)
  - `created_at` (TIMESTAMPTZ)

- **`submissions`**:
  - `id` (PK, Integer, Indexed)
  - `user_id` (FK `users.id`, ON DELETE CASCADE, Indexed)
  - `question_id` (FK `questions.id`, ON DELETE CASCADE, Indexed)
  - `language` (VARCHAR(50))
  - `source_code` (Text, stored securely; never leaked in listing endpoints)
  - `status` (Enum: `PENDING`, `RUNNING`, `ACCEPTED`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `RUNTIME_ERROR`, `COMPILATION_ERROR`, `INTERNAL_ERROR`)
  - `total_test_cases` (Integer)
  - `passed_test_cases` (Integer)
  - `score` (Float, percentage score e.g. 0.0 - 100.0)
  - `execution_time_ms` (Integer, max execution time in milliseconds)
  - `memory_kb` (Integer, peak memory in kilobytes)
  - `error_message` (Text, sanitized compiler diagnostic or runtime error)
  - `created_at` (TIMESTAMPTZ, Indexed)
  - `updated_at` (TIMESTAMPTZ)

- **`submission_test_results`**:
  - `id` (PK, Integer, Indexed)
  - `submission_id` (FK `submissions.id`, ON DELETE CASCADE, Indexed)
  - `test_case_id` (FK `test_cases.id`, ON DELETE SET NULL, Indexed)
  - `status` (VARCHAR(50))
  - `passed` (Boolean, default False)
  - `execution_time_ms` (Integer, nullable)
  - `memory_kb` (Integer, nullable)
  - `stdout` (Text, candidate stdout)
  - `stderr` (Text, candidate stderr)
  - `error_message` (Text, nullable)
  - `created_at` (TIMESTAMPTZ)

### 3. Output Comparison Policy
Implemented in [`app/services/grading.py`](file:///c:/Users/pc/Desktop/coding_platform/backend/app/services/grading.py):
1. **Newline Normalization**: Windows CRLF (`\r\n`) and legacy Mac CR (`\r`) are converted to standard Unix line feeds (`\n`).
2. **Trailing Line Whitespace**: Trailing spaces and tabs on each individual output line are stripped (`line.rstrip()`).
3. **Surrounding Blank Lines**: Leading and trailing newlines/blank lines across the overall output are trimmed (`.strip()`).
4. **Internal Token Integrity**: Internal spaces between tokens on the same line and internal blank lines are strictly preserved. Numbers and tokens are compared as exact strings without arbitrary floating-point rounding.

### 4. Status Determination & Scoring Logic
- **`ACCEPTED`**: All authoritative test cases passed (`passed_test_cases == total_test_cases` and `score == 100.0%`).
- **`WRONG_ANSWER`**: Code executed successfully, but output comparison failed on one or more test cases.
- **`COMPILATION_ERROR`**: Language compiler failed with diagnostic output. Subsequent test cases are skipped to preserve resources.
- **`RUNTIME_ERROR`**: Execution exited with a non-zero exit code or uncaught exception (NZEC, SIGSEGV, ZeroDivisionError, etc.).
- **`TIME_LIMIT_EXCEEDED`**: Process exceeded the sandbox CPU timeout boundary.
- **`INTERNAL_ERROR`**: Sandbox connectivity issues or unexpected execution engine exceptions.
- **Scoring**: $Score = \frac{\sum_{t \in Passed} t.weight}{\sum_{t \in All} t.weight} \times 100.0$. Partial credit is reflected in the numerical score while keeping status distinct from acceptance.

### 5. Hidden Test Case & Candidate Data Protection
- **Candidate-Facing Responses**: Hidden test case inputs, expected outputs, and actual candidate output are obscured (`input=None`, `expected_output=None`, `stdout=None`). Candidates only see status and permitted aggregate counts.
- **Candidate Isolation**: Candidates can only inspect their own submissions. Unauthorized access attempts to another user's submissions return `HTTP 403 Forbidden`.
- **Source Code Protection**: Source code is only returned when retrieving single submission details owned by the user, never in paginated submission history listings.

### 6. API Endpoints
- `POST /api/submissions`: Authenticated submission creation and automated grading.
- `GET /api/submissions`: Authenticated user's paginated submission history (filtered optionally by `question_id`).
- `GET /api/submissions/{id}`: Detailed submission outcome owned by authenticated user.
- `GET /api/submissions/{id}/results`: Permitted individual test case outcomes for owned submission.
- `POST /api/questions/{id}/test-cases`: Admin-only endpoint to add authoritative test cases.
- `GET /api/questions/{id}/test-cases`: Admin-only endpoint to list authoritative test cases (including hidden cases).
- `DELETE /api/questions/{id}/test-cases/{tc_id}`: Admin-only endpoint to delete a test case.

---

## 🏛️ University Labs & Practical Management + RBAC Audit (Chunk 8) - Complete

### 1. High-Level University Structure

```
┌─────────────────────────────────────────────────────────────┐
│                      University Course                      │
│             (Code: CS101, Semester, Academic Year)          │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
       1:N     ▼                       1:N     ▼
┌───────────────────────────────┐ ┌───────────────────────────┐
│   Faculty Course Assignment   │ │     Course Enrollment     │
│   (Assigned Faculty Member)   │ │     (Enrolled Student)    │
└───────────────────────────────┘ └───────────────────────────┘
               │
       1:N     ▼
┌─────────────────────────────────────────────────────────────┐
│                       Practical Lab                         │
│           (Title, Instructions, Display Order, Published)   │
└──────────────┬──────────────────────────────────────────────┘
               │
       1:N     ▼
┌─────────────────────────────────────────────────────────────┐
│                       Lab Practical                         │
│   (Sequence Number, Required Flag, Question Ref, Overrides) │
└──────────────┬──────────────────────────────────────────────┘
               │
       N:1     ▼
┌─────────────────────────────────────────────────────────────┐
│             Existing Authoritative Question Catalog         │
│          (Problem Statement, Judge0 Test Cases, Scoring)    │
└─────────────────────────────────────────────────────────────┘
```

### 2. User Roles & Permission Boundaries

| Role | Scope | Permissions |
| :--- | :--- | :--- |
| **`ADMIN`** | Platform-Wide | Create/edit/delete courses, assign faculty to courses, enroll students, manage all labs and practicals, manage question catalog, manage test cases, promote user roles. |
| **`FACULTY`** | Assigned Courses Only | View assigned courses, create/edit labs in assigned courses, attach coding questions as ordered practicals, publish/unpublish labs, view enrolled student rosters. Cannot manage unassigned courses or promote users. |
| **`STUDENT`** | Enrolled Courses Only | View enrolled courses, browse published labs, inspect practicals (sequence #, problem title, difficulty), launch practical directly in CodingWorkspace. Cannot view unpublished labs, rosters of other students, or create courses/labs. |

### 3. Resource-Level Authorization Rules
1. **Course Isolation**: Faculty members can only manage labs for courses where an authorized `FacultyCourseAssignment` exists.
2. **Student Privacy**: Students can only view courses where they are enrolled (`CourseEnrollment`). Students cannot access class rosters or other students' enrollment records.
3. **Draft Lab Protection**: Unpublished labs (`is_published=False`) are visible only to platform administrators and assigned course faculty.
4. **Hierarchical Traversal**: Direct access via lab ID or practical ID resolves parent course ownership on the server; callers cannot bypass parent course permissions.
5. **Server-Side Trust**: Roles and permissions are strictly evaluated against active database user records. Claims in request bodies or JWTs are never trusted for authorization elevation.

### 4. Relationship and Deletion Safety
- **Question Preservation**: Deleting a lab practical removes the curriculum link but **never** deletes the underlying problem from the question catalog (`ondelete="RESTRICT"`).
- **Submission Integrity**: Courses, labs, or practicals cannot be deleted if historical student submissions exist from enrolled candidates. Deletion requests return `HTTP 409 Conflict` advising instructors to unpublish or archive instead.

### 5. API Endpoints

#### Courses
- `POST /api/v1/courses`: Create a new course (Admin only).
- `GET /api/v1/courses`: List visible courses (Admin: all; Faculty: assigned; Student: enrolled).
- `GET /api/v1/courses/{course_id}`: View course details (Authorized members).
- `PATCH /api/v1/courses/{course_id}`: Update course (Admin: all fields; Faculty: name, description, semester, academic_year, is_active).
- `DELETE /api/v1/courses/{course_id}`: Delete course with dependency safety (Admin only).

#### Faculty Course Assignments
- `POST /api/v1/courses/{course_id}/faculty`: Assign faculty member (Admin only).
- `GET /api/v1/courses/{course_id}/faculty`: View course faculty roster (Admin or Assigned Faculty).
- `DELETE /api/v1/courses/{course_id}/faculty/{faculty_id}`: Revoke faculty assignment (Admin only).

#### Student Course Enrollments
- `POST /api/v1/courses/{course_id}/enrollments`: Enroll student (Admin only).
- `GET /api/v1/courses/{course_id}/enrollments`: View student enrollment roster (Admin or Assigned Faculty).
- `DELETE /api/v1/courses/{course_id}/enrollments/{student_id}`: Remove student enrollment (Admin or Assigned Faculty).

#### Practical Labs
- `POST /api/v1/courses/{course_id}/labs`: Create a lab in course (Admin or Assigned Faculty).
- `GET /api/v1/courses/{course_id}/labs`: List labs in course (Admin/Faculty: all; Student: published only).
- `GET /api/v1/labs/{lab_id}`: Get lab details (Authorized course members; students only if published).
- `PATCH /api/v1/labs/{lab_id}`: Update lab details / publish toggle (Admin or Assigned Faculty).
- `DELETE /api/v1/labs/{lab_id}`: Delete lab with dependency safety (Admin or Assigned Faculty).

#### Lab Practicals
- `POST /api/v1/labs/{lab_id}/practicals`: Add ordered practical to lab (Admin or Assigned Faculty).
- `GET /api/v1/labs/{lab_id}/practicals`: List ordered practicals (Authorized course members).
- `PATCH /api/v1/practicals/{practical_id}`: Update sequence or overrides (Admin or Assigned Faculty).
- `DELETE /api/v1/practicals/{practical_id}`: Remove practical with submission safety (Admin or Assigned Faculty).

#### Administrative User Management
- `GET /api/v1/users`: List users filtered by role (`STUDENT`, `FACULTY`, `ADMIN`) (Admin only).
- `PATCH /api/v1/users/{user_id}/role`: Promote/update user role (Admin only).

### 6. Database Migration
Managed via Alembic migration `backend/alembic/versions/0005_create_university_management_tables.py`:
- Creates `courses`, `faculty_course_assignments`, `course_enrollments`, `labs`, `lab_practicals`.
- Updates `users.role` check constraint for PostgreSQL/SQLite to safely support `FACULTY`.
- Applies uniqueness constraints:
  - `uq_courses_code` (`code`)
  - `uq_course_faculty_assignment` (`course_id`, `faculty_id`)
  - `uq_course_student_enrollment` (`course_id`, `student_id`)
  - `uq_lab_practical_sequence` (`lab_id`, `sequence_number`)
  - `uq_lab_practical_question` (`lab_id`, `question_id`)

---

## Chunk 9: Sequential Practical Unlocking & Passing Thresholds - Complete

### 1. Data Model Extensions
- **`lab_practicals.passing_threshold`**: `Float`, nullable=False, default=100.0 (validated 0.0% to 100.0%). Defines the minimum score a student must earn on this practical to unlock subsequent required practicals.
- **`submissions.practical_id`**: `Integer`, nullable=True, ForeignKey(`lab_practicals.id`, ondelete="SET NULL"), indexed. Reliably links permanent code submissions to the specific laboratory practical instance.
- **Alembic Migration**: `0006_add_practical_submissions_and_passing_threshold.py`. Fully backward-compatible; existing standalone question submissions retain `practical_id = NULL`.

### 2. Practical-to-Submission Relationship & Integrity
- **Bidirectional Validation**:
  - The submission endpoint verifies that `practical_id` references a valid `LabPractical`.
  - The endpoint verifies that `practical.question_id == payload.question_id` (a student cannot submit code for an easy question to satisfy a difficult practical).
  - For students, the endpoint verifies that the parent lab is published, the student is actively enrolled in the course, and the practical is currently unlocked. Submitting directly to a locked practical returns `HTTP 403 Forbidden`.
- **Identity & Context**:
  - Student identity is derived exclusively from the authenticated JWT session (`get_current_student`).
  - Submission ownership is preserved; students cannot query or tamper with submissions of other students.

### 3. Sequential Unlocking Algorithm
Practicals in a lab are ordered strictly by `sequence_number`:
1. **Initial Access**: The first required practical in a published lab is immediately `AVAILABLE` to enrolled students.
2. **Sequential Prerequisite Rule**: Practical `N` (where `is_required=True`) remains `LOCKED` until every preceding required practical `i < N` in the same lab has been `COMPLETED`.
3. **Completion Criteria**: A practical is `COMPLETED` when the student has at least one valid submission with:
   - `status` not in `['COMPILATION_ERROR', 'RUNTIME_ERROR', 'INTERNAL_ERROR', 'TIME_LIMIT_EXCEEDED']`
   - `score >= passing_threshold`
4. **Idempotence & Non-Revocation**: Once a student achieves completion for a practical, subsequent failed retakes or submissions never revoke that completion.
5. **Optional Practical Isolation**: Practicals marked `is_required=False` do not block progression through required practicals. They are available whenever preceding required practicals are satisfied.
6. **Scoped Context**: Completion is strictly scoped to the specific `(student_id, practical_id)` pair. Submissions in standalone catalogs or different labs never bleed across boundaries.

### 4. API Endpoints Implemented / Extended
- `GET /api/v1/labs/{lab_id}/practicals`: Computes dynamic unlock state per enrolled student. Returns `status` (`AVAILABLE`, `LOCKED`, `COMPLETED`), `is_unlocked`, `best_score`, and human-readable `lock_reason`.
- `GET /api/v1/practicals/{practical_id}`: Fetches individual practical details. Returns `HTTP 403 Forbidden` if practical is locked for the requesting student.
- `POST /api/v1/submissions`: Accepts `practical_id` in payload. Associates submission with practical, validates prerequisites and unlocks, and records permanent grading result.
- `GET /api/v1/submissions`: Supports filtering by `practical_id`.

---

## Chunk 10: Cryptographic Lab Completion Certificates & Ed25519 Signing - Complete

### 1. Cryptographic Design Principles
Chunk 10 implements high-assurance, tamper-evident completion credentials for laboratory practicals. The integrity design is based on three pillars:
1. **RFC 8785 Canonical JSON Serialization**: Eliminates non-deterministic JSON representation variance (whitespace, property order, float representations) before hashing.
2. **Cryptographic SHA-256 Digest**: Generates a 256-bit collision-resistant hash of the canonical bytes.
3. **Pure EdDSA (Ed25519) Signatures**: Signs the 64-character digest using an asymmetric Ed25519 private key, producing a 64-byte raw signature (128 hex chars) verifiable by any entity possessing the platform's public key.

```
┌────────────────────────────────────────────────────────┐
│             Student Passes Practical Exam              │
│       (score >= practical.passing_threshold)           │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/certificates/issue
                            ▼
┌────────────────────────────────────────────────────────┐
│            Canonical Payload Serialization             │
│    {student_id, student_name, course_code, lab_title,  │
│     practical_id, score, passing_threshold, etc.}     │
│             (Sorted keys, UTF-8 compact)               │
└───────────────────────────┬────────────────────────────┘
                            │ SHA-256 Hash
                            ▼
┌────────────────────────────────────────────────────────┐
│                 64-Char Payload Digest                 │
│         e.g., "7f83b1657ff1fc53b92dc18148a1d65b..."   │
└───────────────────────────┬────────────────────────────┘
                            │ Sign with Ed25519 Private Key
                            ▼
┌────────────────────────────────────────────────────────┐
│           Asymmetric Ed25519 Digital Signature         │
│         (128 hex chars / 64 bytes raw signature)       │
└───────────────────────────┬────────────────────────────┘
                            │ Persist in PostgreSQL
                            ▼
┌────────────────────────────────────────────────────────┐
│             `completion_certificates` Record           │
│   - id: UUIDv4                                         │
│   - key_id: "labos-sentinel-dev-2026"                  │
│   - payload: canonical JSON dict                       │
│   - payload_digest: sha256_hex                         │
│   - signature: ed25519_hex                             │
└────────────────────────────────────────────────────────┘
```

### 2. Threat Model & Tamper Detection
- **Identity Forgery**: Modifying student ID or name alters the recomputed SHA-256 digest, triggering `DIGEST_MISMATCH`.
- **Grade Inflation**: Altering score or passing threshold alters the recomputed digest, triggering `DIGEST_MISMATCH`.
- **Timestamp Manipulation**: Modifying completion or issuance timestamps invalidates the digest.
- **Signature Forgery**: Forging a signature without the private key fails Ed25519 verification (`INVALID_SIGNATURE`).
- **Key Impersonation**: Signing with an unauthorized key fails validation against registered `key_id` in `certificate_signing_keys` (`UNKNOWN_KEY`).

### 3. API Endpoints
- `POST /api/v1/certificates/issue`: Issue certificate for a completed practical (Student session).
- `GET /api/v1/certificates/practicals/{practical_id}`: Retrieve current student's certificate for practical.
- `GET /api/v1/certificates/{id}`: Detailed certificate retrieval (Authorized student, assigned faculty, admin).
- `GET /api/v1/certificates/{id}/public`: Sanitized public certificate retrieval (Unauthenticated).
- `POST /api/v1/certificates/verify`: Public verification endpoint comparing canonical payload, stored digest, and signature.
- `GET /api/v1/certificates/public-keys/list`: Public key registry export for independent verifiers.

---

## Chunk 11: Public Tamper-Verification Portal - Complete

### 1. Purpose & Unauthenticated Access
Chunk 11 provides a publicly accessible portal where external verifiers (academic registrars, potential employers, auditors) can verify certificate credentials without logging in or holding platform credentials.

```
┌────────────────────────────────────────────────────────┐
│               Public Verification Portal               │
│               (VerificationPortal.tsx)                 │
├───────────────────────────┬────────────────────────────┤
│ Mode A: Certificate UUID  │ Mode B: Drag-and-Drop JSON │
│  Input UUID or QR URL     │ Drop exported .json cert   │
└─────────────┬─────────────┴─────────────┬──────────────┘
              │                           │
              │ POST /api/v1/certificates/verify
              ▼                           ▼
┌────────────────────────────────────────────────────────┐
│               Backend Cryptographic Engine             │
│  - Reconstructs RFC 8785 canonical JSON payload        │
│  - Recomputes SHA-256 digest                           │
│  - Fetches trusted public key for key_id               │
│  - Executes Ed25519 asymmetric signature check         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            Audit Outcome Diagnostic Report             │
│  🟢 VALID & AUTHENTIC (Untampered, signed by issuer)   │
│  🔴 DIGEST_MISMATCH (Altered payload detected)         │
│  🔴 INVALID_SIGNATURE (Signature verification failed)  │
│  🟡 UNKNOWN_KEY (Key ID not in trusted registry)       │
│  ⚪ NOT_FOUND (Certificate UUID does not exist)        │
└────────────────────────────────────────────────────────┘
```

### 2. Deep-Link & QR Integration
- Supports automatic inspection via query parameters: `?cert_id=<UUID>` or `#verify?id=<UUID>`.
- In `CertificateModal.tsx`, students can click "Copy Verification Link" or "Open in Public Portal" to share or preview the public audit card.
- Incorporates active Curve25519 public key inspection drawer with hex copy feature for third-party command line verification.

---

## Future Chunks Roadmap
1. **Chunk 12**: Faculty Performance Analytics & Submission Auditing.
2. **Chunk 13**: Decentralized Ledger & Blockchain Verification.



