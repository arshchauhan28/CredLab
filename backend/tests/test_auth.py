"""
Authentication and User Management Tests.

Covers:
- Enrollment-authorized registration
- Student, faculty, and administrator roles
- Password hashing
- Enrollment-number login
- Prevention of unauthorized registration and privilege escalation
- JWT authentication
- Inactive accounts
- Student academic profile updates
- Existing health and database endpoints
"""

from datetime import timedelta

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.authorized_enrollment import AuthorizedEnrollment
from app.models.user import User, UserRole


# ============================================================================
# Test helpers
# ============================================================================

def authorize_enrollment(
    db_session,
    enrollment_number,
    expected_role=UserRole.STUDENT,
    is_active=True,
    admin_job_role=None,
):
    """Create an enrollment number authorized for registration."""
    authorization = AuthorizedEnrollment(
        enrollment_number=enrollment_number,
        expected_role=expected_role,
        admin_job_role=admin_job_role,
        is_active=is_active,
    )

    db_session.add(authorization)
    db_session.commit()
    db_session.refresh(authorization)

    return authorization


def register_student(
    client,
    db_session,
    *,
    name="Test Student",
    email="student@example.com",
    enrollment_number="MUR2500001",
    password="StrongPassword123",
    academic_course="B.Tech CSE",
):
    """Authorize and register a student."""
    authorize_enrollment(
        db_session,
        enrollment_number,
        UserRole.STUDENT,
    )

    return client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "enrollment_number": enrollment_number,
            "academic_course": academic_course,
            "password": password,
        },
    )


def login(client, enrollment_number, password):
    """Log in using an enrollment number and password."""
    return client.post(
        "/api/auth/login",
        json={
            "enrollment_number": enrollment_number,
            "password": password,
        },
    )


def create_direct_user(
    db_session,
    *,
    name="Test User",
    email="direct@example.com",
    enrollment_number=None,
    password="StrongPassword123",
    role=UserRole.STUDENT,
    is_active=True,
):
    """Create a user directly for authentication-specific tests."""
    user = User(
        name=name,
        email=email,
        enrollment_number=enrollment_number,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


# ============================================================================
# 1. Student registration tests
# ============================================================================

def test_register_student_successfully(client, db_session):
    response = register_student(
        client,
        db_session,
        name="Ekansh",
        email="ekansh@example.com",
        enrollment_number="MUR2500001",
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Ekansh"
    assert data["email"] == "ekansh@example.com"
    assert data["enrollment_number"] == "MUR2500001"
    assert data["role"] == "STUDENT"
    assert data["is_active"] is True

    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_registration_normalizes_email_and_enrollment_number(
    client,
    db_session,
):
    authorize_enrollment(
        db_session,
        "MUR2500002",
        UserRole.STUDENT,
    )

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Normalized Student",
            "email": "  NORMALIZED@example.com  ",
            "enrollment_number": "mur2500002",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "normalized@example.com"
    assert data["enrollment_number"] == "MUR2500002"


def test_registration_rejects_unauthorized_enrollment(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Unauthorized Student",
            "email": "unauthorized@example.com",
            "enrollment_number": "MUR2500003",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()


def test_registration_rejects_inactive_authorization(
    client,
    db_session,
):
    authorize_enrollment(
        db_session,
        "MUR2500004",
        UserRole.STUDENT,
        is_active=False,
    )

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Inactive Authorization",
            "email": "inactive-auth@example.com",
            "enrollment_number": "MUR2500004",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 403


def test_registration_rejects_enrollment_with_wrong_role(
    client,
    db_session,
):
    """Student registration rejects an EMP enrollment number."""
    authorize_enrollment(
        db_session,
        "EMP2500001",
        UserRole.FACULTY,
    )

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Faculty as Student",
            "email": "faculty-as-student@example.com",
            "enrollment_number": "EMP2500001",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 422

def test_registration_rejects_already_claimed_enrollment(
    client,
    db_session,
):
    first = register_student(
        client,
        db_session,
        email="first-student@example.com",
        enrollment_number="MUR2500005",
    )

    assert first.status_code == 201

    second = client.post(
        "/api/auth/register",
        json={
            "name": "Second Student",
            "email": "second-student@example.com",
            "enrollment_number": "MUR2500005",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
        },
    )

    assert second.status_code == 409


def test_registration_rejects_duplicate_email(
    client,
    db_session,
):
    first = register_student(
        client,
        db_session,
        email="duplicate@example.com",
        enrollment_number="MUR2500006",
    )

    assert first.status_code == 201

    authorize_enrollment(
        db_session,
        "MUR2500007",
        UserRole.STUDENT,
    )

    second = client.post(
        "/api/auth/register",
        json={
            "name": "Duplicate Email",
            "email": "duplicate@example.com",
            "enrollment_number": "MUR2500007",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
        },
    )

    assert second.status_code == 409
    assert "email" in second.json()["detail"].lower()


def test_registration_rejects_invalid_enrollment_format(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Invalid Enrollment",
            "email": "invalid-format@example.com",
            "enrollment_number": "MUR123",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 422


def test_registration_requires_academic_course(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Missing Course",
            "email": "missing-course@example.com",
            "enrollment_number": "MUR2500008",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 422


def test_registration_cannot_assign_admin_role(
    client,
    db_session,
):
    authorize_enrollment(
        db_session,
        "MUR2500009",
        UserRole.STUDENT,
    )

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Role Injection Attempt",
            "email": "role-injection@example.com",
            "enrollment_number": "MUR2500009",
            "academic_course": "B.Tech CSE",
            "password": "StrongPassword123",
            "role": "ADMIN",
        },
    )

    # The schema may ignore unknown fields, but the database-authorized
    # role must remain STUDENT.
    assert response.status_code == 201
    assert response.json()["role"] == "STUDENT"

    user = (
        db_session.query(User)
        .filter(User.email == "role-injection@example.com")
        .first()
    )

    assert user is not None
    assert user.role == UserRole.STUDENT


def test_registration_hashes_password(client, db_session):
    plain_password = "SuperSecretPassword123"

    response = register_student(
        client,
        db_session,
        email="password-check@example.com",
        enrollment_number="MUR2500010",
        password=plain_password,
    )

    assert response.status_code == 201

    user = (
        db_session.query(User)
        .filter(User.email == "password-check@example.com")
        .first()
    )

    assert user is not None
    assert user.password_hash != plain_password
    assert plain_password not in user.password_hash
    assert verify_password(plain_password, user.password_hash)
    assert not verify_password("WrongPassword123", user.password_hash)

    assert user.password_hash.startswith("$argon2id$")


# ============================================================================
# 2. Faculty registration tests
# ============================================================================

def test_register_faculty_successfully(client, db_session):
    authorize_enrollment(
        db_session,
        "EMP2500001",
        UserRole.FACULTY,
    )

    response = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Test Faculty",
            "email": "faculty@example.com",
            "enrollment_number": "EMP2500001",
            "teaching_subjects": ["Python", "Data Structures"],
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Faculty"
    assert data["email"] == "faculty@example.com"
    assert data["enrollment_number"] == "EMP2500001"
    assert data["role"] == "FACULTY"
    assert data["admin_job_role"] is None


def test_faculty_registration_rejects_unauthorized_number(client):
    response = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Unauthorized Faculty",
            "email": "unauthorized-faculty@example.com",
            "enrollment_number": "EMP2500002",
            "teaching_subjects": ["Python"],
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 403


def test_faculty_registration_rejects_student_authorization(
    client,
    db_session,
):
    """Faculty registration rejects a MUR enrollment number."""
    authorize_enrollment(
        db_session,
        "MUR2500011",
        UserRole.STUDENT,
    )

    response = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Wrong Role Faculty",
            "email": "wrong-role-faculty@example.com",
            "enrollment_number": "MUR2500011",
            "teaching_subjects": ["Python"],
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 422


def test_faculty_registration_requires_teaching_subjects(client):
    response = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Missing Subjects",
            "email": "missing-subjects@example.com",
            "enrollment_number": "EMP2500003",
            "teaching_subjects": [],
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 422


# ============================================================================
# 3. Administrator registration tests
# ============================================================================

def test_register_admin_successfully(client, db_session):
    authorize_enrollment(
        db_session,
        "EMP2500004",
        UserRole.ADMIN,
        admin_job_role="UNIVERSITY_ADMIN",
    )

    response = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Test Administrator",
            "email": "admin@example.com",
            "enrollment_number": "EMP2500004",
            "admin_job_role": "UNIVERSITY_ADMIN",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Administrator"
    assert data["email"] == "admin@example.com"
    assert data["enrollment_number"] == "EMP2500004"
    assert data["role"] == "ADMIN"
    assert data["admin_job_role"] == "UNIVERSITY_ADMIN"


def test_admin_registration_rejects_job_role_mismatch(client, db_session):
    authorize_enrollment(
        db_session,
        "EMP2500099",
        UserRole.ADMIN,
        admin_job_role="LAB_ADMIN",
    )
    response = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Mismatched Administrator",
            "email": "mismatch-admin@example.com",
            "enrollment_number": "EMP2500099",
            "admin_job_role": "UNIVERSITY_ADMIN",
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 403
    assert "job role" in response.json()["detail"].lower()


def test_legacy_admin_authorization_requires_explicit_provisioning(client, db_session):
    authorize_enrollment(
        db_session,
        "EMP2500098",
        UserRole.ADMIN,
    )
    response = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Unprovisioned Administrator",
            "email": "unprovisioned-admin@example.com",
            "enrollment_number": "EMP2500098",
            "admin_job_role": "SUPER_ADMIN",
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 403


def test_admin_registration_rejects_unauthorized_number(client):
    response = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Unauthorized Administrator",
            "email": "unauthorized-admin@example.com",
            "enrollment_number": "EMP2500005",
            "admin_job_role": "UNIVERSITY_ADMIN",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 403


def test_admin_registration_rejects_faculty_authorization(
    client,
    db_session,
):
    authorize_enrollment(
        db_session,
        "EMP2500006",
        UserRole.FACULTY,
    )

    response = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Faculty Escalation",
            "email": "faculty-escalation@example.com",
            "enrollment_number": "EMP2500006",
            "admin_job_role": "UNIVERSITY_ADMIN",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 403


def test_admin_registration_rejects_invalid_job_role(
    client,
    db_session,
):
    authorize_enrollment(
        db_session,
        "EMP2500007",
        UserRole.ADMIN,
    )

    response = client.post(
        "/api/auth/register/admin",
        json={
            "name": "Invalid Admin Role",
            "email": "invalid-admin-role@example.com",
            "enrollment_number": "EMP2500007",
            "admin_job_role": "ROOT_SUPREME_ADMIN",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 422


# ============================================================================
# 4. Login tests
# ============================================================================

def test_login_with_correct_enrollment_and_password(
    client,
    db_session,
):
    registration = register_student(
        client,
        db_session,
        name="Login Student",
        email="login@example.com",
        enrollment_number="MUR2500012",
        password="CorrectPassword123",
    )

    assert registration.status_code == 201

    response = login(
        client,
        "MUR2500012",
        "CorrectPassword123",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"
    assert data["user"]["enrollment_number"] == "MUR2500012"
    assert data["user"]["role"] == "STUDENT"

    assert "password" not in data
    assert "password_hash" not in data["user"]


def test_login_rejects_incorrect_password(client, db_session):
    registration = register_student(
        client,
        db_session,
        email="wrong-password@example.com",
        enrollment_number="MUR2500013",
        password="CorrectPassword123",
    )

    assert registration.status_code == 201

    response = login(
        client,
        "MUR2500013",
        "WrongPassword999",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid enrollment number or password."
    )


def test_login_rejects_unknown_enrollment_number(client):
    response = login(
        client,
        "MUR2500014",
        "AnyPassword123",
    )

    assert response.status_code == 401


def test_login_does_not_auto_register_users(client, db_session):
    response = login(
        client,
        "MUR2500015",
        "AnyPassword123",
    )

    assert response.status_code == 401

    user = (
        db_session.query(User)
        .filter(User.enrollment_number == "MUR2500015")
        .first()
    )

    assert user is None


def test_login_rejects_email_based_payload(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "email-login@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 422


def test_password_suffix_cannot_grant_faculty_role(
    client,
    db_session,
):
    response = login(
        client,
        "EMP2500008",
        "SecretPassword-fac",
    )

    assert response.status_code == 401

    assert (
        db_session.query(User)
        .filter(User.enrollment_number == "EMP2500008")
        .first()
        is None
    )


def test_password_suffix_cannot_grant_admin_role(
    client,
    db_session,
):
    response = login(
        client,
        "EMP2500009",
        "SecretPassword-ad",
    )

    assert response.status_code == 401

    assert (
        db_session.query(User)
        .filter(User.enrollment_number == "EMP2500009")
        .first()
        is None
    )


def test_inactive_user_cannot_login(client, db_session):
    create_direct_user(
        db_session,
        name="Inactive Person",
        email="inactive@example.com",
        enrollment_number="MUR2500016",
        password="Password123",
        is_active=False,
    )

    response = login(
        client,
        "MUR2500016",
        "Password123",
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


# ============================================================================
# 5. Authenticated current-user endpoint
# ============================================================================

def test_valid_jwt_accesses_me(client, db_session):
    registration = register_student(
        client,
        db_session,
        name="Me User",
        email="me@example.com",
        enrollment_number="MUR2500017",
        password="Password123",
    )

    assert registration.status_code == 201

    login_response = login(
        client,
        "MUR2500017",
        "Password123",
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Me User"
    assert data["email"] == "me@example.com"
    assert data["role"] == "STUDENT"
    assert data["enrollment_number"] == "MUR2500017"


def test_missing_jwt_returns_401(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert (
        "credentials were not provided"
        in response.json()["detail"].lower()
    )


def test_invalid_jwt_returns_401(client):
    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": "Bearer totally-invalid-bogus-token"
        },
    )

    assert response.status_code == 401


def test_expired_jwt_returns_401(client, db_session):
    user = create_direct_user(
        db_session,
        name="Expired User",
        email="expired@example.com",
        enrollment_number="MUR2500018",
    )

    expired_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": "STUDENT",
        },
        expires_delta=timedelta(minutes=-10),
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_inactive_user_cannot_access_me_with_token(
    client,
    db_session,
):
    user = create_direct_user(
        db_session,
        name="Revoked User",
        email="revoked@example.com",
        enrollment_number="MUR2500019",
        is_active=False,
    )

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": "STUDENT",
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


# ============================================================================
# 6. Student academic profile tests
# ============================================================================

def test_student_academic_profile_update_and_uniqueness(
    client,
    db_session,
):
    first_registration = register_student(
        client,
        db_session,
        name="Alice",
        email="alice_prof@example.com",
        enrollment_number="MUR2500020",
        password="alicepassword",
    )

    assert first_registration.status_code == 201

    first_login = login(
        client,
        "MUR2500020",
        "alicepassword",
    )

    assert first_login.status_code == 200

    first_token = first_login.json()["access_token"]

    assert first_login.json()["user"]["profile_completed"] is False

    profile_data = {
        "student_id_number": "STU-9901",
        "academic_course": "B.Tech CSE",
        "academic_year": "2026-2027",
        "semester": "Semester 1",
    }

    update_response = client.put(
        "/api/auth/profile",
        json=profile_data,
        headers={
            "Authorization": f"Bearer {first_token}"
        },
    )

    assert update_response.status_code == 200

    updated_profile = update_response.json()

    assert updated_profile["student_id_number"] == "STU-9901"
    assert updated_profile["academic_course"] == "B.Tech CSE"
    assert updated_profile["academic_year"] == "2026-2027"
    assert updated_profile["semester"] == "Semester 1"
    assert updated_profile["profile_completed"] is True

    second_registration = register_student(
        client,
        db_session,
        name="Bob",
        email="bob_prof@example.com",
        enrollment_number="MUR2500021",
        password="bobpassword",
    )

    assert second_registration.status_code == 201

    second_login = login(
        client,
        "MUR2500021",
        "bobpassword",
    )

    assert second_login.status_code == 200

    second_token = second_login.json()["access_token"]

    duplicate_response = client.put(
        "/api/auth/profile",
        json=profile_data,
        headers={
            "Authorization": f"Bearer {second_token}"
        },
    )

    assert duplicate_response.status_code == 409
    assert (
        "already registered"
        in duplicate_response.json()["detail"].lower()
    )


def test_non_student_cannot_update_student_profile(
    client,
    db_session,
):
    authorize_enrollment(
        db_session,
        "EMP2500010",
        UserRole.FACULTY,
    )

    registration = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Profile Test Faculty",
            "email": "profile-faculty@example.com",
            "enrollment_number": "EMP2500010",
            "teaching_subjects": ["Python"],
            "password": "Password123",
        },
    )

    assert registration.status_code == 201

    faculty_record = db_session.query(User).filter(User.enrollment_number == "EMP2500010").first()
    if faculty_record:
        faculty_record.approval_status = "APPROVED"
        db_session.commit()

    login_response = login(
        client,
        "EMP2500010",
        "Password123",
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.patch(
        "/api/auth/profile",
        json={
            "student_id_number": "STU-9902",
            "academic_course": "B.Tech CSE",
            "academic_year": "2026-2027",
            "semester": "Semester 1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


# ============================================================================
# 7. Existing health and database endpoints
# ============================================================================

def test_health_endpoint_still_works(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_test_endpoint_still_works(client):
    response = client.get("/api/db-test")

    assert response.status_code == 200
    assert "connected" in response.json()


def test_database_diagnostic_endpoint_requires_auth(client):
    # Unauthenticated request must be rejected
    response = client.get("/api/db-test/diagnostic")
    assert response.status_code == 401

    # Invalid diagnostic key must be rejected
    response = client.get(
        "/api/db-test/diagnostic",
        headers={"X-Diagnostic-Key": "wrong-secret-key"},
    )
    assert response.status_code == 401


def test_database_diagnostic_endpoint_succeeds_with_key(client):
    from app.core.config import settings

    response = client.get(
        "/api/db-test/diagnostic",
        headers={"X-Diagnostic-Key": settings.JWT_SECRET_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert "current_database" in data
    assert "server_version" in data
    assert "table_counts" in data
    assert "password" not in str(data).lower()
    assert "database_url" not in str(data).lower()


def test_faculty_registration_rejected_without_authorization_and_succeeds_when_authorized(client, db_session):
    """
    Regression test for priority bug: Faculty registration rejected when unauthorized (EMP2500045).
    Verifies:
    1. Unauthorized EMP2500045 is rejected with HTTP 403 'This enrollment number is not authorized for registration.'
    2. Non-SUPER_ADMIN cannot manage authorization registry (HTTP 403).
    3. SUPER_ADMIN can provision active faculty authorization for EMP2500045 (HTTP 201).
    4. Faculty registration with EMP2500045 succeeds (HTTP 201) and creates PENDING user + RegistrationApproval in same transaction.
    5. Duplicate registration with same enrollment number fails (HTTP 409).
    6. Pending faculty cannot sign in (HTTP 403).
    7. Administrator approves registration (HTTP 200).
    8. Approved faculty can sign in (HTTP 200) and access protected endpoints.
    """
    from app.models.user import User, UserRole
    from app.models.registration_approval import RegistrationApproval
    from app.models.authorized_enrollment import AuthorizedEnrollment
    from app.core.security import create_access_token, hash_password

    emp_id = "EMP2500045"
    faculty_email = "emp2500045@university.edu"
    faculty_password = "SecureFacultyPassword123!"

    # Step 1: Attempt registration without authorization record
    reg_unauthorized = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Dr. Testing Faculty",
            "email": faculty_email,
            "enrollment_number": emp_id,
            "teaching_subjects": ["Data Structures", "Algorithms"],
            "password": faculty_password,
        },
    )
    assert reg_unauthorized.status_code == 403
    assert reg_unauthorized.json()["detail"] == "This enrollment number is not authorized for registration."

    # Verify no user or approval record was created
    assert db_session.query(User).filter(User.enrollment_number == emp_id).first() is None
    assert db_session.query(RegistrationApproval).count() == 0

    # Step 2: Create a regular admin and a super admin
    regular_admin = User(
        name="Dean Admin",
        email="dean.admin@uni.edu",
        enrollment_number="EMP2500001",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        admin_job_role="DEAN",
        is_active=True,
        approval_status="APPROVED",
    )
    super_admin = User(
        name="Super Administrator",
        email="super.admin@uni.edu",
        enrollment_number="EMP2500002",
        password_hash=hash_password("SuperAdminPass123!"),
        role=UserRole.ADMIN,
        admin_job_role="SUPER_ADMIN",
        is_active=True,
        approval_status="APPROVED",
    )
    db_session.add_all([regular_admin, super_admin])
    db_session.commit()

    regular_admin_token = create_access_token(data={"sub": str(regular_admin.id), "role": "ADMIN"})
    super_admin_token = create_access_token(data={"sub": str(super_admin.id), "role": "ADMIN"})

    # Non-SUPER_ADMIN cannot authorize enrollments
    auth_denied = client.post(
        "/api/authorized-enrollments",
        headers={"Authorization": f"Bearer {regular_admin_token}"},
        json={
            "enrollment_number": emp_id,
            "expected_role": "FACULTY",
            "is_active": True,
        },
    )
    assert auth_denied.status_code == 403

    # Step 3: SUPER_ADMIN provisions the authorization
    auth_created = client.post(
        "/api/authorized-enrollments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "enrollment_number": emp_id,
            "expected_role": "FACULTY",
            "is_active": True,
        },
    )
    assert auth_created.status_code == 201
    auth_data = auth_created.json()
    assert auth_data["enrollment_number"] == emp_id
    assert auth_data["expected_role"] == "FACULTY"
    assert auth_data["claimed_by_user_id"] is None

    # Step 4: Faculty registration now succeeds
    reg_success = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Dr. Testing Faculty",
            "email": faculty_email,
            "enrollment_number": emp_id,
            "teaching_subjects": ["Data Structures", "Algorithms"],
            "password": faculty_password,
        },
    )
    assert reg_success.status_code == 201
    faculty_user_data = reg_success.json()
    assert faculty_user_data["approval_status"] == "PENDING"
    assert faculty_user_data["role"] == "FACULTY"

    # Verify authorization record is now claimed
    auth_record = db_session.query(AuthorizedEnrollment).filter(
        AuthorizedEnrollment.enrollment_number == emp_id
    ).first()
    assert auth_record.claimed_by_user_id == faculty_user_data["id"]

    # Verify registration approval record was created in the database
    approval_record = db_session.query(RegistrationApproval).filter(
        RegistrationApproval.applicant_id == faculty_user_data["id"]
    ).first()
    assert approval_record is not None
    assert approval_record.decision == "PENDING"
    assert approval_record.account_type == "FACULTY"

    # Step 5: Duplicate registration with the claimed enrollment number fails
    dup_reg = client.post(
        "/api/auth/register/faculty",
        json={
            "name": "Duplicate Faculty",
            "email": "other.email@uni.edu",
            "enrollment_number": emp_id,
            "teaching_subjects": ["Operating Systems"],
            "password": faculty_password,
        },
    )
    assert dup_reg.status_code == 409

    # Step 6: Pending faculty cannot sign in
    login_pending = client.post(
        "/api/auth/login",
        json={"enrollment_number": emp_id, "password": faculty_password},
    )
    assert login_pending.status_code == 403
    assert "pending approval" in login_pending.json()["detail"].lower()

    # Step 7: Administrator reviews and approves the registration
    approve_response = client.post(
        f"/api/approvals/{approval_record.id}/approve",
        headers={"Authorization": f"Bearer {regular_admin_token}"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["decision"] == "APPROVED"

    # Step 8: Approved faculty can now sign in
    login_approved = client.post(
        "/api/auth/login",
        json={"enrollment_number": emp_id, "password": faculty_password},
    )
    assert login_approved.status_code == 200
    faculty_token = login_approved.json()["access_token"]
    assert faculty_token

    # Step 9: Approved faculty can access their profile with valid token
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["enrollment_number"] == emp_id
    assert me_response.json()["role"] == "FACULTY"