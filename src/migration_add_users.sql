-- Migration: Multi-User Authentication System
-- This migration adds user management and per-user settings
-- Run this after the base schema.sql

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User settings for per-user API keys
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    llm_api_key TEXT,
    llm_model TEXT,
    llm_base_url TEXT,
    llm_provider TEXT,
    embedding_api_key TEXT,
    embedding_model TEXT,
    embedding_base_url TEXT,
    embedding_provider TEXT,
    embedding_dimension INTEGER,
    audio_model TEXT,
    search_preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add user_id to projects (nullable for existing data)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Remove unique constraint on project name
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_name_key;

-- Add composite unique constraint on (user_id, name)
-- Allow NULL user_id for existing projects
ALTER TABLE projects ADD CONSTRAINT projects_user_name_unique UNIQUE (user_id, name);

-- Session tokens for authentication
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for user tables
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Update existing projects to have NULL user_id
-- This allows existing projects to be migrated later
UPDATE projects SET user_id = NULL WHERE user_id IS NULL;

-- Helper function to verify project ownership
CREATE OR REPLACE FUNCTION verify_project_ownership(p_project_id UUID, p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    project_user_id UUID;
BEGIN
    SELECT user_id INTO project_user_id FROM projects WHERE id = p_project_id;

    IF project_user_id IS NULL THEN
        -- Project has no owner (legacy data)
        RETURN FALSE;
    END IF;

    RETURN project_user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Update triggers to set user_id when creating projects
CREATE OR REPLACE FUNCTION set_project_user_id()
RETURNS TRIGGER AS $$
BEGIN
    -- If user_id is not set and we have a session context, it would be set by the application
    -- This is a placeholder for any additional logic needed
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Comment on tables
COMMENT ON TABLE users IS 'User accounts for authentication';
COMMENT ON TABLE user_settings IS 'Per-user settings including API keys';
COMMENT ON TABLE user_sessions IS 'Active session tokens for authentication';

-- Migration complete
SELECT 'Migration completed successfully. Note: Existing projects have user_id=NULL and need to be migrated to a default user.' as message;
