#!/usr/bin/env python
"""
Development Admin Provisioning Script.
Securely creates or promotes an ADMIN user in the database without exposing any public endpoint.
Usage:
    python scripts/create_dev_admin.py --name "Admin User" --email "admin@example.com" --password "AdminPassword123"
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


def create_or_update_admin(name: str, email: str, password: str):
    db = SessionLocal()
    clean_email = email.strip().lower()
    try:
        user = db.query(User).filter(User.email == clean_email).first()
        hashed = hash_password(password)

        if user:
            print(f"[INFO] User '{clean_email}' already exists. Promoting to ADMIN...")
            user.role = UserRole.ADMIN
            user.admin_job_role = "SUPER_ADMIN"
            user.approval_status = "APPROVED"
            user.name = name
            user.password_hash = hashed
            user.is_active = True
            db.commit()
            db.refresh(user)
            print(f"[SUCCESS] User '{user.email}' updated to SUPER_ADMIN (ID: {user.id}).")
        else:
            print(f"[INFO] Creating new SUPER_ADMIN user '{clean_email}'...")
            admin_user = User(
                name=name,
                email=clean_email,
                password_hash=hashed,
                role=UserRole.ADMIN,
                admin_job_role="SUPER_ADMIN",
                approval_status="APPROVED",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"[SUCCESS] SUPER_ADMIN user '{admin_user.email}' successfully created (ID: {admin_user.id}).")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to provision admin user: {exc}")
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create or update an administrative user for development.")
    parser.add_argument("--name", default="Platform Administrator", help="Admin's full name")
    parser.add_argument("--email", default="admin@example.com", help="Admin's email address")
    parser.add_argument("--password", default="AdminSecurePassword123", help="Admin's password (min 8 chars)")

    args = parser.parse_args()

    if len(args.password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        sys.exit(1)

    print("=" * 60)
    print(" Secure Coding Assessment Platform - Dev Admin Provisioner")
    print("=" * 60)
    create_or_update_admin(args.name, args.email, args.password)


if __name__ == "__main__":
    main()
