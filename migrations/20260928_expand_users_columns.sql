-- Expand users columns to match the SQLAlchemy model and store full scrypt hashes.
-- Already applied to the configured development database on 2026-09-28.
-- For other installations, select the SupportFlow database before running.
-- Expected previous schema: email VARCHAR(50), password_hash VARCHAR(50), NOT NULL.
-- Existing rows are preserved. MySQL ALTER TABLE implicitly commits.

ALTER TABLE users
    MODIFY COLUMN password_hash VARCHAR(255) NOT NULL,
    MODIFY COLUMN email VARCHAR(100) NOT NULL;
