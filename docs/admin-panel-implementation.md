# Admin Panel Implementation Notes

## Architecture inspected

- Frontend: `frontend/`, Next.js App Router, React, TypeScript, Tailwind CSS 4.
- Existing admin entry point: `frontend/app/admin/dashboard/page.tsx`.
- Existing session: `scp_session` HTTP-only cookie managed by Next.js auth route handlers.
- Backend: `backend/app/`, FastAPI, SQLAlchemy, Pydantic and Alembic.
- API prefix: `/api` by default.
- Existing domain models include users, courses, faculty-course assignments, course enrollments, questions, question examples/languages, submissions, labs/practicals, certificates and authorized enrollments.
- No separate timed-assessment model was present in the inspected project. The question bank is not presented as a timed-assessment scheduler.

## Admin API capability matrix

| Feature | Endpoint | Method | Authorization / notes |
|---|---|---|---|
| User list | `/api/users` | GET | Active authenticated ADMIN |
| User role change | `/api/users/{user_id}/role` | PATCH | SUPER_ADMIN job role; cannot promote a non-admin to ADMIN; last active administrator safeguards |
| Courses | `/api/courses` | GET, POST | GET requires authentication; POST supports ADMIN/FACULTY |
| Course update | `/api/courses/{course_id}` | PATCH | ADMIN or faculty assigned to that course |
| Question bank | `/api/questions` | GET, POST | Authenticated; creation uses existing question schema |
| Question details/update | `/api/questions/{id}` | GET, PUT | Authenticated, with existing role visibility |
| Question status | `/api/questions/{id}/status` | PATCH | Authenticated ADMIN/FACULTY |
| Submission history for current user | `/api/submissions` | GET | Owner-only, paginated |
| All platform submissions | `/api/submissions/admin/list` | GET | ADMIN-only, paginated metadata, filters for user, question and status; does not return source code |
| Enrollment authorization registry | `/api/authorized-enrollments` | GET, POST | SUPER_ADMIN job role only |
| Update authorization active state / admin job role | `/api/authorized-enrollments/{id}` | PATCH | SUPER_ADMIN job role only |

The dashboard uses a same-origin Next.js route at `/api/admin/[...path]` to forward requests with the server-held HTTP-only session cookie. The cookie value is not read by browser JavaScript.

## Security changes

1. Added an `admin_job_role` field to authorized enrollment records.
2. Administrator registration now requires the requested job role to exactly match the role explicitly provisioned on that enrollment authorization.
3. Existing ADMIN authorization records with a NULL `admin_job_role` remain intact but cannot be used for administrator registration until explicitly provisioned.
4. Enrollment authorization management is restricted to a user whose database account has `role=ADMIN` and `admin_job_role=SUPER_ADMIN`.
5. Role updates require SUPER_ADMIN permission and cannot create new ADMIN accounts through the role-update endpoint.
6. The platform-wide submission list is metadata-only and ADMIN-only.

## Database migration

A new Alembic migration was added:

- Revision: `0009_authorized_admin_job_role`
- Parent: `82d1a741d8f7`

Before running this in a deployed environment, back up the database and review the migration. Do not reset the database. Existing authorization rows are preserved. The nullable column intentionally avoids silently assigning a privileged role to legacy records.

Run from `backend/` after configuring the intended database URL:

```bash
alembic upgrade head
```

Do not run this against production without reviewing the migration and obtaining approval.

If there is no existing SUPER_ADMIN account, bootstrap the first one through a reviewed, controlled database administration procedure. Do not make the public registration endpoint self-provision SUPER_ADMIN.

## Supported UI actions

- Overview: live counts for users, courses, questions and total submissions, where the corresponding API is available.
- User and faculty management: search the loaded account list and change roles with confirmation; role changes require SUPER_ADMIN.
- Courses: create courses and activate/deactivate courses.
- Assessment management: create coding questions and update question status.
- Submissions: inspect paginated metadata for all platform submissions.
- Results & analytics: database-backed account/course/question/submission counts and question status distribution.
- Authorization: SUPER_ADMIN-only enrollment authorization creation, listing, activation/deactivation and administrative job-role provisioning.
- Settings: view current account/session information and sign out.

## Intentionally not represented as implemented

- User activation/deactivation: no dedicated safe endpoint was present.
- Full question editing, sample-example editing and hidden test-case management: backend capabilities exist in parts, but this UI does not yet expose a complete editor for them.
- Timed assessment scheduling: no separate timed-assessment model/API was found.
- Faculty-course assignment management and enrollment management UI: underlying APIs exist, but the dashboard currently reports available course assignment counts instead of exposing all assignment workflows.
- Profile editing, password change, notification preferences and global settings writes: no verified admin settings API was present.
- Audit event history: no general administrative audit-log model/source was found; the UI does not fabricate activity events.

These are deliberately disclosed rather than represented by nonfunctional controls.

## Verification performed

- Python `compileall` succeeded for backend app and tests.
- Full backend test suite: **176 passed** using an isolated SQLite test database via `DATABASE_URL=sqlite:////tmp/scap_test_app.db`.
- Frontend TypeScript check, lint and production build were not verified in this environment because the npm dependency installation did not complete. Run these locally from `frontend/`:

```bash
npm ci
npx tsc --noEmit
npm run lint
npm run build
```

The frontend was not built or deployed as part of this change.
