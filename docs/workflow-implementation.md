# Workflow implementation notes

## Academic subject assignment

`Course` now stores program, year of study, semester, and academic session. The subject code is optional. Admin subject creation creates the selected faculty assignment in the same API operation. Student profile updates run exact normalized matching over all four academic dimensions and avoid duplicate enrollments.

## Faculty practical workflow

Faculty can list only assigned subjects, create/publish labs, create practicals from a title/problem statement, choose allowed languages, optionally provide a sample test, and request AI-generated hidden tests. Faculty can review submissions from assigned subjects and approve/reject lab completion certificate requests.

## Student workflow

The student dashboard loads server-authorized enrolled subjects and published labs, exposes practical unlock state from the backend, supports run-with-stdin and submit-for-grading actions, shows submission history and progress, and lists certificates and pending certificate approvals. The editor blocks paste, drag/drop, and context-menu actions at the UI layer; these are not a substitute for server-side assessment controls.

## Evaluation and AI

- `/api/execute` runs a snippet in the configured Judge0 sandbox.
- `/api/submissions` executes authoritative saved test cases and stores results.
- `/api/questions/{id}/generate-tests` calls the configured OpenAI-compatible API and persists generated cases as hidden test cases.
- `/api/submissions/{id}/feedback` produces optional AI-assisted feedback without exposing hidden test inputs or expected outputs.
- Test-based grading is authoritative. AI-generated tests and feedback should be reviewed; the system does not treat an LLM's opinion as proof of correctness.

## Certificate workflow

When all required practicals in a lab have accepted submissions, a unique pending request is created in `certificate_approval_requests`. Assigned faculty or an administrator can approve or reject the request. Approval calls the existing Ed25519 certificate service, then records the request as approved. Student-facing endpoints expose the request state and issued certificate metadata.

## Migration

The migration chain ends at `0011_certificate_approval`. Back up PostgreSQL before applying it. Run `alembic upgrade head` from `backend/` after configuring `.env`.
