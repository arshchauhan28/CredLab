"""
One-time CredLab SUPER_ADMIN bootstrap script.

Creates the initial approved administrator using the application's
existing SQLAlchemy models and Argon2 password hashing.

Run from the backend directory.

Do not commit this script or any credentials to GitHub.
"""

import getpass
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.authorized_enrollment import AuthorizedEnrollment


def main() -> None:
    print("\n=== CredLab Initial SUPER_ADMIN Setup ===\n")

    # Collect information without storing passwords in the source code.
    name = input("Administrator full name: ").strip()
    email = input("Administrator email: ").strip().lower()
    enrollment_number = input(
        "Administrator employee ID (EMP + 7 digits): "
    ).strip().upper()

    if len(name) < 2:
        sys.exit("ERROR: Enter a valid full name.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        sys.exit("ERROR: Enter a valid email address.")

    if not re.fullmatch(r"EMP\d{7}", enrollment_number):
        sys.exit(
            "ERROR: Employee ID must contain EMP followed by "
            "exactly seven digits."
        )

    password = getpass.getpass(
        "Choose a NEW administrator password (minimum 12 characters): "
    )
    confirmation = getpass.getpass("Confirm administrator password: ")

    if len(password) < 12:
        sys.exit("ERROR: Password must contain at least 12 characters.")

    if password != confirmation:
        sys.exit("ERROR: Passwords do not match.")

    print(
        "\nThis script will create an active, approved SUPER_ADMIN "
        "account in the database configured for this backend."
    )
    print("Name:", name)
    print("Email:", email)
    print("Employee ID:", enrollment_number)

    confirmation_text = input(
        "\nType CREATE SUPER ADMIN to continue: "
    ).strip()

    if confirmation_text != "CREATE SUPER ADMIN":
        sys.exit("Cancelled. No changes were made.")

    db = SessionLocal()

    try:
        # Never overwrite or elevate an existing account.
        existing_email = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if existing_email:
            sys.exit(
                "ERROR: This email already belongs to an account. "
                "No changes were made."
            )

        existing_enrollment_user = (
            db.query(User)
            .filter(
                User.enrollment_number == enrollment_number
            )
            .first()
        )

        if existing_enrollment_user:
            sys.exit(
                "ERROR: This employee ID already belongs to an account. "
                "No changes were made."
            )

        # Find an existing authorization or prepare a new one.
        authorization = (
            db.query(AuthorizedEnrollment)
            .filter(
                AuthorizedEnrollment.enrollment_number
                == enrollment_number
            )
            .with_for_update()
            .first()
        )

        if authorization is not None:
            if authorization.claimed_by_user_id is not None:
                sys.exit(
                    "ERROR: This employee ID has already been claimed. "
                    "No changes were made."
                )

            print(
                "\nAn unclaimed authorization exists. "
                "It will be configured for the initial SUPER_ADMIN."
            )

            authorization.expected_role = UserRole.ADMIN
            authorization.admin_job_role = "SUPER_ADMIN"
            authorization.is_active = True

        else:
            authorization = AuthorizedEnrollment(
                enrollment_number=enrollment_number,
                expected_role=UserRole.ADMIN,
                admin_job_role="SUPER_ADMIN",
                is_active=True,
                course_id=None,
                claimed_by_user_id=None,
            )

            db.add(authorization)
            db.flush()

        # Use the application's own Argon2 password hashing.
        user = User(
            name=name,
            email=email,
            enrollment_number=enrollment_number,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            admin_job_role="SUPER_ADMIN",
            is_active=True,
            approval_status="APPROVED",
        )

        db.add(user)
        db.flush()

        # Claim the authorization with the new account.
        authorization.claimed_by_user_id = user.id

        # Both changes succeed or fail together.
        db.commit()

        print("\nSUCCESS: Initial SUPER_ADMIN created.")
        print("User ID:", user.id)
        print("Name:", user.name)
        print("Email:", user.email)
        print("Employee ID:", user.enrollment_number)
        print("Account role: ADMIN")
        print("Administrative role: SUPER_ADMIN")
        print("Approval status: APPROVED")
        print("Active:", user.is_active)
        print("\nYou can now test signing in through CredLab.")

    except SQLAlchemyError:
        db.rollback()
        print(
            "\nERROR: The database operation failed. "
            "The transaction was rolled back."
        )
        print(
            "Check the database configuration, migrations, and "
            "backend logs before trying again."
        )
        raise

    finally:
        db.close()
        password = None
        confirmation = None


if __name__ == "__main__":
    main()