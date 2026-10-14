# Database Setup & Configuration

This directory contains database management resources and initialization scripts for the **Secure Coding Assessment Platform**.

## Overview
- **Database Engine**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0+
- **Database Driver**: `psycopg` (v3)
- **Migration Tool**: Alembic

---

## 1. Quick Database Initialization

### Using Local PostgreSQL:
Connect to your local PostgreSQL server with `psql` or pgAdmin:

```bash
psql -U postgres -f database/init.sql
```

Or run directly in the `psql` shell:
```sql
CREATE DATABASE secure_coding_db;
```

### Using Docker (Alternative):
If you prefer running PostgreSQL via Docker:
```bash
docker run --name secure-coding-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres_dev_password \
  -e POSTGRES_DB=secure_coding_db \
  -p 5432:5432 \
  -d postgres:16-alpine
```

---

## 2. Connecting the Backend
Update `backend/.env` with your credentials:
```env
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=secure_coding_db
```

---

## 3. Testing Database Connectivity
Run the diagnostic script inside `backend/`:
```bash
python scripts/test_db_connection.py
```

---

## 4. Alembic Migrations
When schema changes or models are added in future chunks:

```bash
# Generate a new migration
alembic revision --autogenerate -m "Add initial tables"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```
