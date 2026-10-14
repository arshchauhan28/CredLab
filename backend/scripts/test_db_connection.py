#!/usr/bin/env python
"""
Standalone Database Connection Test Script.
Runs a test query against the configured PostgreSQL database and reports connection status.
Usage:
    python scripts/test_db_connection.py
"""

import sys
import os

# Add parent directory to path to enable app imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.config import settings
from app.core.database import check_database_connection


def main():
    print("=" * 60)
    print(" Secure Coding Assessment Platform - Database Diagnostic")
    print("=" * 60)
    print(f"Target Server   : {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
    print(f"Database Name   : {settings.POSTGRES_DB}")
    print(f"User            : {settings.POSTGRES_USER}")
    # Mask password for security
    print("Password        : ********")
    print(f"Driver          : PostgreSQL with psycopg (v3)")
    print("-" * 60)
    print("Testing connection...")

    result = check_database_connection()

    if result.get("connected"):
        print("\n[SUCCESS] PostgreSQL connection succeeded!")
        print(f"Message: {result.get('message')}")
        print("Ready for SQLAlchemy ORM and Alembic migrations.")
        sys.exit(0)
    else:
        print("\n[FAILED] PostgreSQL connection failed.")
        print(f"Message : {result.get('message')}")
        if result.get("error_type"):
            print(f"Error   : {result.get('error_type')}")
        if result.get("details"):
            print(f"Details : {result.get('details')}")
        print("\nTroubleshooting tips:")
        print("1. Check if PostgreSQL service or Docker container is running.")
        print("2. Verify credentials in backend/.env match your PostgreSQL installation.")
        print(f"3. Verify that database '{settings.POSTGRES_DB}' has been created.")
        print("   (Run: CREATE DATABASE secure_coding_db; in PostgreSQL)")
        sys.exit(1)


if __name__ == "__main__":
    main()
