-- ── Database initialization ─────────────────────────────────────
-- This script runs once when the postgres container first starts.

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- fast text search

-- Set timezone
SET timezone = 'UTC';

-- Log
DO $$ BEGIN
  RAISE NOTICE 'Database initialized: can_i_trust';
END $$;
