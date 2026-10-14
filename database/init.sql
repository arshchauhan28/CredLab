-- Secure Coding Assessment Platform
-- Initial Database Setup Script for PostgreSQL
-- Run this script as the 'postgres' superuser:
-- psql -U postgres -f init.sql

-- 1. Create development database if not exists
CREATE DATABASE secure_coding_db;

-- 2. Connect to the database
\c secure_coding_db;

-- 3. (Optional) Create dedicated application user
-- CREATE USER coding_admin WITH ENCRYPTED PASSWORD 'replace_with_strong_password';
-- GRANT ALL PRIVILEGES ON DATABASE secure_coding_db TO coding_admin;
-- GRANT ALL ON SCHEMA public TO coding_admin;

-- 4. Enable useful extensions (e.g. uuid-ossp for secure random UUIDs)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

COMMENT ON DATABASE secure_coding_db IS 'Database for Secure Coding Assessment Platform';
