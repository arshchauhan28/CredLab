#!/usr/bin/env python
"""
Development Faculty Provisioning Script.
Securely creates or promotes a FACULTY user in the database without exposing any public registration bypass.
Usage:
    python scripts/create_dev_faculty.py --name "Prof Turing" --email "faculty@example.com" --password "FacultyPassword123"
"""

import argparse
import sys
import os

# Enable importing app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def create_or_update_faculty(name: str, email: str, password: str):
    db = SessionLocal()
    clean_email = email.strip().lower()
    try:
        user = db.query(User).filter(User.email == clean_email).first()
        hashed = hash_password(password)

        if user:
            print(f"[INFO] User '{clean_email}' already exists. Updating to FACULTY role...")
            user.role = UserRole.FACULTY
            user.approval_status = "APPROVED"
            user.name = name
            user.password_hash = hashed
            user.is_active = True
            db.commit()
            db.refresh(user)
            print(f"[SUCCESS] User '{user.email}' updated to FACULTY (ID: {user.id}).")
        else:
            print(f"[INFO] Creating new FACULTY user '{clean_email}'...")
            faculty_user = User(
                name=name,
                email=clean_email,
                password_hash=hashed,
                role=UserRole.FACULTY,
                approval_status="APPROVED",
                is_active=True,
            )
            db.add(faculty_user)
            db.commit()
            db.refresh(faculty_user)
            print(f"[SUCCESS] FACULTY user '{faculty_user.email}' successfully created (ID: {faculty_user.id}).")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to provision faculty user: {exc}")
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create or update a faculty user for development.")
    parser.add_argument("--name", default="Faculty Professor", help="Faculty's full name")
    parser.add_argument("--email", default="faculty@example.com", help="Faculty's email address")
    parser.add_argument("--password", default="FacultyPassword123", help="Faculty's password (min 8 chars)")

    args = parser.parse_args()

    if len(args.password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        sys.exit(1)

    print("=" * 60)
    print(" LabOS Sentinel - Dev Faculty Provisioner")
    print("=" * 60)
    create_or_update_faculty(args.name, args.email, args.password)


if __name__ == "__main__":
    main()
