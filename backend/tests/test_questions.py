def test_existing_chunk2_auth_still_works(client, db_session):
    """Registration, enrollment login, and /api/auth/me still function."""
    from app.models.authorized_enrollment import AuthorizedEnrollment
    from app.models.user import UserRole

    # Authorize a student enrollment number for this test.
    authorization = AuthorizedEnrollment(
        enrollment_number="MUR2500091",
        expected_role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(authorization)
    db_session.commit()

    # Register the student.
    reg = client.post(
        "/api/auth/register",
        json={
            "name": "Regression Student",
            "email": "reg_student@example.com",
            "enrollment_number": "MUR2500091",
            "academic_course": "B.Tech CSE",
            "password": "Password123",
        },
    )

    assert reg.status_code == 201
    assert reg.json()["role"] == "STUDENT"

    # Log in using enrollment number.
    login_response = client.post(
        "/api/auth/login",
        json={
            "enrollment_number": "MUR2500091",
            "password": "Password123",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Verify the authenticated user's profile.
    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me.status_code == 200
    assert me.json()["email"] == "reg_student@example.com"
    assert me.json()["enrollment_number"] == "MUR2500091"