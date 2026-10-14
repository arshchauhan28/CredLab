import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.database import engine, Base
import app.models  # ensure all models are registered
from sqlalchemy import text, inspect

def add_columns():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    existing_cols = {c["name"] for c in inspector.get_columns("users")}
    with engine.connect() as conn:
        for col in ['student_id_number', 'academic_course', 'academic_year', 'semester']:
            if col not in existing_cols:
                try:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} VARCHAR;"))
                    print(f"Added column {col} to users table.")
                except Exception as e:
                    print(f"Error adding {col}: {e}")
            else:
                print(f"Column {col} already exists in users table.")
        conn.commit()
    print("Academic profile columns verified successfully.")

if __name__ == "__main__":
    add_columns()

