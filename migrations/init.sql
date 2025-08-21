-- PostgreSQL initialization script for Knowledge Database
-- This script runs automatically when the PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Create custom types if needed
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'languagecode') THEN
        CREATE TYPE languagecode AS ENUM ('en', 'ko', 'ja', 'zh', 'es', 'fr', 'de');
    END IF;
END$$;

-- Grant permissions (database should already exist via Docker env)
-- GRANT ALL PRIVILEGES ON DATABASE knowledge_db TO postgres;

-- Performance optimizations for pgvector
SET max_parallel_workers_per_gather = 4;
SET max_parallel_workers = 8;
SET max_parallel_maintenance_workers = 4;

COMMENT ON DATABASE knowledge_db IS 'Knowledge Database for AI-powered search and knowledge management';
