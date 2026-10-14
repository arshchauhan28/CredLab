"""Regression tests for SUPER_ADMIN-only enrollment authorization management."""

from app.core.security import create_access_token, hash_password
from app.models.authorized_enrollment import AuthorizedEnrollment
from app.models.user import User, UserRole


def make_user(db_session, *, role=UserRole.ADMIN, job_role="SUPER_ADMIN", enrollment="EMP2500999"):
    user = User(
        name="Test Admin",
        email=f"{enrollment.lower()}@example.com",
        enrollment_number=enrollment,
        password_hash=hash_password("StrongPassword123"),
        role=role,
        admin_job_role=job_role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user):
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def test_super_admin_can_create_explicit_admin_authorization(client, db_session):
    admin = make_user(db_session)
    response = client.post(
        "/api/authorized-enrollments",
        headers=auth_headers(admin),
        json={
            "enrollment_number": "EMP2501000",
            "expected_role": "ADMIN",
            "admin_job_role": "LAB_ADMIN",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["admin_job_role"] == "LAB_ADMIN"


def test_ordinary_admin_cannot_read_authorization_registry(client, db_session):
    admin = make_user(db_session, job_role="UNIVERSITY_ADMIN", enrollment="EMP2500998")
    response = client.get("/api/authorized-enrollments", headers=auth_headers(admin))
    assert response.status_code == 403


def test_authorization_requires_admin_job_role_for_admin_enrollment(client, db_session):
    admin = make_user(db_session)
    response = client.post(
        "/api/authorized-enrollments",
        headers=auth_headers(admin),
        json={
            "enrollment_number": "EMP2501001",
            "expected_role": "ADMIN",
            "is_active": True,
        },
    )
    assert response.status_code == 422


def test_legacy_admin_authorization_without_job_role_is_not_implicitly_promoted(db_session):
    record = AuthorizedEnrollment(
        enrollment_number="EMP2501002",
        expected_role=UserRole.ADMIN,
        admin_job_role=None,
        is_active=True,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    assert record.admin_job_role is None


def test_platform_submission_list_requires_admin(client):
    response = client.get("/api/submissions/admin/list")
    assert response.status_code == 401


def test_platform_submission_list_returns_paginated_metadata_to_admin(client, db_session):
    admin = make_user(db_session, job_role="UNIVERSITY_ADMIN", enrollment="EMP2500997")
    response = client.get(
        "/api/submissions/admin/list?page=1&page_size=10",
        headers=auth_headers(admin),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["page_size"] == 10
