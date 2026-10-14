from app.models.user import UserRole

def test_existing_authentication_and_valid_roles_work(client, db_session):
    """Existing registration, enrollment login, and role assignments work."""
    from app.models.authorized_enrollment import AuthorizedEnrollment

    # Authorize this student enrollment number.
    authorization = AuthorizedEnrollment(
        enrollment_number="MUR2500090",
        expected_role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(authorization)
    db_session.commit()

    # Register a student using the new registration contract.
    reg_res = client.post(
        "/api/auth/register",
        json={
            "name": "New Reg",
            "email": "newreg@uni.edu",
            "enrollment_number": "MUR2500090",
            "academic_course": "B.Tech CSE",
            "password": "Password123",
        },
    )

    assert reg_res.status_code == 201
    assert reg_res.json()["role"] == "STUDENT"
    assert reg_res.json()["enrollment_number"] == "MUR2500090"

    # Log in using enrollment number and password.
    login_res = client.post(
        "/api/auth/login",
        json={
            "enrollment_number": "MUR2500090",
            "password": "Password123",
        },
    )

    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Verify the authenticated user's profile.
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_res.status_code == 200
    assert me_res.json()["email"] == "newreg@uni.edu"
    assert me_res.json()["role"] == "STUDENT"
    assert me_res.json()["enrollment_number"] == "MUR2500090"