"""
Comprehensive automated tests for LabOS Platform Upgrade features:
1. Student Academic Profile (Year of Study & Semester validation)
2. Administrative Designations & Public Registration Restrictions
3. Faculty and Admin Registration Approval Workflow (Pending, Approve, Reject with Reason)
4. Automatic Badge Awarding (Idempotent 100% Score Milestone Badges)
5. Subject-Level Certificates (Ed25519 Cryptographic Signing & Approval Workflow)
6. Student Academic Progress & Badges Retrieval
7. Safe Subject and Practical Deletion Impact Assessment & Archival
"""

import pytest
from app.core.security import create_access_token, hash_password
from app.models.authorized_enrollment import AuthorizedEnrollment
from app.models.badge import Badge
from app.models.certificate import CompletionCertificate, SubjectCertificateRequest
from app.models.registration_approval import RegistrationApproval
from app.models.submission import Submission, SubmissionStatus
from app.models.university import Course, CourseEnrollment, FacultyCourseAssignment, Lab, LabPractical
from app.models.user import User, UserRole


def make_auth_user(db_session, *, name, email, enrollment, role, job_role=None, approval_status="APPROVED"):
    user = User(
        name=name,
        email=email,
        enrollment_number=enrollment,
        password_hash=hash_password("Pass1234!"),
        role=role,
        admin_job_role=job_role,
        is_active=True,
        approval_status=approval_status,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(user):
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Student Academic Profile Fields (Part 6)
# ==============================================================================

def test_student_registration_with_year_and_semester(client, db_session):
    auth = AuthorizedEnrollment(
        enrollment_number="MUR2599001",
        expected_role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(auth)
    db_session.commit()

    res = client.post(
        "/api/auth/register",
        json={
            "name": "Academic Student",
            "email": "acadstudent@example.com",
            "enrollment_number": "MUR2599001",
            "academic_course": "B.Tech (AI & DS)",
            "year_of_study": "2nd Year",
            "semester": "Semester 3",
            "password": "StrongPassword123",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["year_of_study"] == "2nd Year"
    assert data["semester"] == "Semester 3"


# ==============================================================================
# 2. Administrative Role Options (Part 7)
# ==============================================================================

def test_public_admin_registration_rejects_super_admin(client, db_session):
    auth = AuthorizedEnrollment(
        enrollment_number="EMP2599002",
        expected_role=UserRole.ADMIN,
        admin_job_role="SUPER_ADMIN",
        is_active=True,
    )
    db_session.add(auth)
    db_session.commit()

    res = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Super Admin Applicant",
            "email": "superapplicant@example.com",
            "enrollment_number": "EMP2599002",
            "admin_job_role": "SUPER_ADMIN",
            "password": "StrongPassword123",
        },
    )
    assert res.status_code == 403


def test_public_admin_registration_accepts_valid_designations(client, db_session):
    auth = AuthorizedEnrollment(
        enrollment_number="EMP2599003",
        expected_role=UserRole.ADMIN,
        admin_job_role="HEAD_OF_DEPARTMENT",
        is_active=True,
    )
    db_session.add(auth)
    db_session.commit()

    res = client.post(
        "/api/auth/register/admin",
        json={
            "name": "HOD Admin",
            "email": "hodadmin@example.com",
            "enrollment_number": "EMP2599003",
            "admin_job_role": "HEAD_OF_DEPARTMENT",
            "password": "StrongPassword123",
        },
    )
    assert res.status_code == 201
    assert res.json()["admin_job_role"] == "HEAD_OF_DEPARTMENT"
    assert res.json()["approval_status"] == "PENDING"


# ==============================================================================
# 3. Registration Approval Workflow (Part 8)
# ==============================================================================

def test_registration_approval_workflow_lifecycle(client, db_session):
    super_admin = make_auth_user(
        db_session,
        name="Chief Super Admin",
        email="superadmin@uni.edu",
        enrollment="EMP2599010",
        role=UserRole.ADMIN,
        job_role="SUPER_ADMIN",
    )
    regular_admin = make_auth_user(
        db_session,
        name="Dean Admin",
        email="dean@uni.edu",
        enrollment="EMP2599011",
        role=UserRole.ADMIN,
        job_role="DEAN",
    )

    # 1. Authorize & register faculty
    auth_fac = AuthorizedEnrollment(
        enrollment_number="EMP2599012",
        expected_role=UserRole.FACULTY,
        is_active=True,
    )
    db_session.add(auth_fac)
    db_session.commit()

    reg_fac = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Pending Faculty",
            "email": "pendingfac@uni.edu",
            "enrollment_number": "EMP2599012",
            "teaching_subjects": ["Data Structures"],
            "password": "Password123!",
        },
    )
    assert reg_fac.status_code == 201
    fac_data = reg_fac.json()
    assert fac_data["approval_status"] == "PENDING"

    # Pending faculty cannot log in
    login_fac = client.post(
        "/api/auth/login",
        json={"enrollment_number": "EMP2599012", "password": "Password123!"},
    )
    assert login_fac.status_code == 403

    # List pending approvals as admin
    approvals_res = client.get("/api/approvals", headers=auth_header(regular_admin))
    assert approvals_res.status_code == 200
    approval_items = approvals_res.json()
    fac_approval = next(a for a in approval_items if a["applicant_enrollment_number"] == "EMP2599012")

    # Regular admin can approve faculty
    approve_res = client.post(
        f"/api/approvals/{fac_approval['id']}/approve",
        headers=auth_header(regular_admin),
    )
    assert approve_res.status_code == 200

    # Now faculty can log in
    login_fac_ok = client.post(
        "/api/auth/login",
        json={"enrollment_number": "EMP2599012", "password": "Password123!"},
    )
    assert login_fac_ok.status_code == 200

    # 2. Authorize & register admin
    auth_adm = AuthorizedEnrollment(
        enrollment_number="EMP2599013",
        expected_role=UserRole.ADMIN,
        admin_job_role="SENIOR_FACULTY",
        is_active=True,
    )
    db_session.add(auth_adm)
    db_session.commit()

    reg_adm = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Pending Admin",
            "email": "pendingadm@uni.edu",
            "enrollment_number": "EMP2599013",
            "admin_job_role": "SENIOR_FACULTY",
            "password": "Password123!",
        },
    )
    assert reg_adm.status_code == 201

    # Regular admin CANNOT approve another admin
    approvals_res2 = client.get("/api/approvals", headers=auth_header(super_admin))
    adm_approval = next(a for a in approvals_res2.json() if a["applicant_enrollment_number"] == "EMP2599013")

    regular_try_approve = client.post(
        f"/api/approvals/{adm_approval['id']}/approve",
        headers=auth_header(regular_admin),
    )
    assert regular_try_approve.status_code == 403

    # Rejection requires reason note
    empty_reject = client.post(
        f"/api/approvals/{adm_approval['id']}/reject",
        headers=auth_header(super_admin),
        json={"reason": ""},
    )
    assert empty_reject.status_code in (400, 422)

    # Super admin rejects with reason
    valid_reject = client.post(
        f"/api/approvals/{adm_approval['id']}/reject",
        headers=auth_header(super_admin),
        json={"reason": "Incomplete institutional credentials provided."},
    )
    assert valid_reject.status_code == 200
    assert valid_reject.json()["status"] == "REJECTED"


# ==============================================================================
# 4. Automatic Badges (Part 10)
# ==============================================================================

def test_automatic_badge_awarded_on_full_score(client, db_session):
    super_admin = make_auth_user(
        db_session,
        name="Admin Badge",
        email="adminbadge@uni.edu",
        enrollment="EMP2599020",
        role=UserRole.ADMIN,
        job_role="SUPER_ADMIN",
    )
    student = make_auth_user(
        db_session,
        name="Badge Earner",
        email="badgeearner@uni.edu",
        enrollment="MUR2599020",
        role=UserRole.STUDENT,
    )

    course = Course(
        name="Algorithm Architecture",
        code="CS501",
        program="B.Tech (CSE)",
        year_of_study="3rd Year",
        semester="Semester 5",
        created_by=super_admin.id,
    )
    db_session.add(course)
    db_session.commit()

    lab = Lab(course_id=course.id, title="Graph Algorithms", is_published=True, created_by=super_admin.id)
    db_session.add(lab)
    db_session.commit()

    from app.models.question import Question, QuestionDifficulty, QuestionStatus
    q = Question(
        title="Graph BFS Traversal",
        slug="graph-bfs-traversal",
        description="Traverse graph breadth first",
        difficulty=QuestionDifficulty.MEDIUM,
        status=QuestionStatus.PUBLISHED,
        created_by=super_admin.id,
    )
    db_session.add(q)
    db_session.commit()

    practical = LabPractical(
        lab_id=lab.id,
        question_id=q.id,
        title="Graph BFS Traversal",
        sequence_number=1,
        is_required=True,
        passing_threshold=100.0,
    )
    db_session.add(practical)
    db_session.commit()

    # Enroll student
    enr = CourseEnrollment(course_id=course.id, student_id=student.id, status="ENROLLED")
    db_session.add(enr)
    db_session.commit()

    # Pass practical with 100% score via mock submission
    sub = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=practical.id,
        language="python",
        source_code="print('ok')",
        status=SubmissionStatus.ACCEPTED,
        score=100.0,
        total_test_cases=2,
        passed_test_cases=2,
    )
    db_session.add(sub)
    db_session.commit()

    # Trigger badge service
    from app.services.badge_service import award_badge_if_eligible
    badge = award_badge_if_eligible(db_session, student.id, practical, sub)
    assert badge is not None
    assert "Graph" in badge.name or "BFS" in badge.name or "Achiever" in badge.name

    # Idempotency check: awarding again returns existing badge
    badge2 = award_badge_if_eligible(db_session, student.id, practical, sub)
    assert badge2.id == badge.id


# ==============================================================================
# 5. Subject Certificates & Student Progress (Parts 11 & 12)
# ==============================================================================

def test_subject_certificate_request_review_and_progress(client, db_session):
    super_admin = make_auth_user(
        db_session,
        name="Admin Cert",
        email="admincert@uni.edu",
        enrollment="EMP2599030",
        role=UserRole.ADMIN,
        job_role="SUPER_ADMIN",
    )
    student = make_auth_user(
        db_session,
        name="Diploma Student",
        email="diplomastudent@uni.edu",
        enrollment="MUR2599030",
        role=UserRole.STUDENT,
    )

    course = Course(
        name="Operating Systems Design",
        code="CS303",
        program="B.Tech (CSE)",
        year_of_study="2nd Year",
        semester="Semester 4",
        created_by=super_admin.id,
    )
    db_session.add(course)
    db_session.commit()

    lab = Lab(course_id=course.id, title="OS Lab", is_published=True, created_by=super_admin.id)
    db_session.add(lab)
    db_session.commit()

    from app.models.question import Question, QuestionDifficulty, QuestionStatus
    q = Question(
        title="Process Scheduler",
        slug="process-scheduler",
        description="Implement Round Robin",
        difficulty=QuestionDifficulty.EASY,
        status=QuestionStatus.PUBLISHED,
        created_by=super_admin.id,
    )
    db_session.add(q)
    db_session.commit()

    practical = LabPractical(
        lab_id=lab.id,
        question_id=q.id,
        title="Process Scheduler",
        sequence_number=1,
        is_required=True,
        passing_threshold=100.0,
    )
    db_session.add(practical)
    db_session.commit()

    enr = CourseEnrollment(course_id=course.id, student_id=student.id, status="ENROLLED")
    db_session.add(enr)
    db_session.commit()

    # Student cannot request certificate if practical not completed
    fail_req = client.post(
        "/api/certificates/subject-requests",
        headers=auth_header(student),
        json={"course_id": course.id},
    )
    assert fail_req.status_code == 400

    # Student completes practical
    sub = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=practical.id,
        language="python",
        source_code="pass",
        status=SubmissionStatus.ACCEPTED,
        score=100.0,
        total_test_cases=1,
        passed_test_cases=1,
    )
    db_session.add(sub)
    db_session.commit()

    # Now student progress indicates ELIGIBLE
    prog_res = client.get(
        "/api/certificates/student-progress",
        headers=auth_header(student),
    )
    assert prog_res.status_code == 200
    subjs = prog_res.json()["subjects"]
    target_subj = next(s for s in subjs if s["course_id"] == course.id)
    assert target_subj["certificate_status"] == "ELIGIBLE"
    assert target_subj["completion_percentage"] == 100.0

    # Student requests subject certificate
    req_res = client.post(
        "/api/certificates/subject-requests",
        headers=auth_header(student),
        json={"course_id": course.id},
    )
    assert req_res.status_code == 200
    req_id = req_res.json()["id"]

    # Admin reviews pending subject approvals
    approvals_list = client.get(
        "/api/certificates/subject-approvals",
        headers=auth_header(super_admin),
    )
    assert approvals_list.status_code == 200
    assert any(item["id"] == req_id for item in approvals_list.json()["items"])

    # Admin approves and cryptographically signs certificate
    approve_cert = client.post(
        f"/api/certificates/subject-approvals/{req_id}",
        headers=auth_header(super_admin),
        json={"action": "APPROVE", "note": "All requirements verified."},
    )
    assert approve_cert.status_code == 200
    cert_id = approve_cert.json()["certificate_id"]
    assert cert_id is not None

    # Public certificate verification
    pub_res = client.get(f"/api/certificates/{cert_id}/public")
    assert pub_res.status_code == 200
    assert pub_res.json()["student_name"] == "Diploma Student"
    assert pub_res.json()["algorithm"] == "ED25519-SHA256"


# ==============================================================================
# 6. Deletion Management (Parts 13 & 14)
# ==============================================================================

def test_course_and_practical_deletion_impact_and_archival(client, db_session):
    super_admin = make_auth_user(
        db_session,
        name="Admin Del",
        email="admindel@uni.edu",
        enrollment="EMP2599040",
        role=UserRole.ADMIN,
        job_role="SUPER_ADMIN",
    )
    student = make_auth_user(
        db_session,
        name="Student Del",
        email="studentdel@uni.edu",
        enrollment="MUR2599040",
        role=UserRole.STUDENT,
    )

    course = Course(
        name="Compiler Construction",
        code="CS701",
        program="B.Tech (CSE)",
        year_of_study="4th Year",
        semester="Semester 7",
        created_by=super_admin.id,
    )
    db_session.add(course)
    db_session.commit()

    lab = Lab(course_id=course.id, title="Lexical Analyzer", is_published=True, created_by=super_admin.id)
    db_session.add(lab)
    db_session.commit()

    from app.models.question import Question, QuestionDifficulty, QuestionStatus
    q = Question(
        title="Lexer Implementation",
        slug="lexer-implementation",
        description="Tokenize stream",
        difficulty=QuestionDifficulty.HARD,
        status=QuestionStatus.PUBLISHED,
        created_by=super_admin.id,
    )
    db_session.add(q)
    db_session.commit()

    practical = LabPractical(
        lab_id=lab.id,
        question_id=q.id,
        title="Lexer Implementation",
        sequence_number=1,
        is_required=True,
    )
    db_session.add(practical)
    db_session.commit()

    enr = CourseEnrollment(course_id=course.id, student_id=student.id, status="ENROLLED")
    db_session.add(enr)
    db_session.commit()

    # Pre-check deletion preview when no submissions exist
    p_preview = client.get(
        f"/api/v1/practicals/{practical.id}/deletion-preview",
        headers=auth_header(super_admin),
    )
    assert p_preview.status_code == 200
    assert p_preview.json()["action"] == "HARD_DELETE"

    # Add historical submission
    sub = Submission(
        user_id=student.id,
        question_id=q.id,
        practical_id=practical.id,
        language="cpp",
        source_code="int main(){}",
        status=SubmissionStatus.ACCEPTED,
        score=100.0,
    )
    db_session.add(sub)
    db_session.commit()

    # Check deletion preview now that submissions exist
    p_preview_history = client.get(
        f"/api/v1/practicals/{practical.id}/deletion-preview",
        headers=auth_header(super_admin),
    )
    assert p_preview_history.status_code == 200
    assert p_preview_history.json()["action"] == "ARCHIVE"
    assert p_preview_history.json()["historical_submissions_count"] == 1

    # Attempting hard delete without archive flag is rejected with 409
    del_reject = client.delete(
        f"/api/v1/practicals/{practical.id}",
        headers=auth_header(super_admin),
    )
    assert del_reject.status_code == 409

    # Deleting with archive_if_dependent=true performs safe archival
    del_archive = client.delete(
        f"/api/v1/practicals/{practical.id}?archive_if_dependent=true",
        headers=auth_header(super_admin),
    )
    assert del_archive.status_code == 200
    assert del_archive.json()["archived"] is True

    # Course deletion preview also reflects historical activity
    c_preview = client.get(
        f"/api/v1/courses/{course.id}/deletion-preview",
        headers=auth_header(super_admin),
    )
    assert c_preview.status_code == 200
    assert c_preview.json()["recommended_action"] == "ARCHIVE"

    # Course archival with archive_if_dependent=true
    del_course = client.delete(
        f"/api/v1/courses/{course.id}?archive_if_dependent=true",
        headers=auth_header(super_admin),
    )
    assert del_course.status_code == 200
    assert del_course.json()["archived"] is True
