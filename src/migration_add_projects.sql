-- Migration to add project support to existing database
-- Run this AFTER the base schema.sql if tables already exist

-- Add new columns to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_hash TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS first_ingested TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_ingested TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ingestion_count INTEGER DEFAULT 1;

-- Create missing indexes
CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON chat_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id, created_at);

-- Drop and recreate triggers (they failed before)
DROP TRIGGER IF EXISTS update_project_timestamp_on_document ON documents;
DROP TRIGGER IF EXISTS update_project_timestamp_on_session ON chat_sessions;

-- Recreate functions
CREATE OR REPLACE FUNCTION update_project_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE projects SET updated_at = NOW()
    WHERE id = NEW.project_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate triggers
CREATE TRIGGER update_project_timestamp_on_document
AFTER INSERT OR UPDATE ON documents
FOR EACH ROW
WHEN (NEW.project_id IS NOT NULL)
EXECUTE FUNCTION update_project_timestamp();

CREATE TRIGGER update_project_timestamp_on_session
AFTER INSERT OR UPDATE ON chat_sessions
FOR EACH ROW
WHEN (NEW.project_id IS NOT NULL)
EXECUTE FUNCTION update_project_timestamp();

-- Update existing documents to have a project (optional - creates default project)
-- Uncomment if you want to assign existing docs to a default project:
/*
DO $$
DECLARE
    default_project_id UUID;
BEGIN
    -- Get or create default project
    SELECT id INTO default_project_id FROM projects WHERE name = 'Default' LIMIT 1;

    IF default_project_id IS NULL THEN
        INSERT INTO projects (name, description)
        VALUES ('Default', 'Default project for existing documents')
        RETURNING id INTO default_project_id;
    END IF;

    -- Update existing documents without a project
    UPDATE documents
    SET project_id = default_project_id
    WHERE project_id IS NULL;
END $$;
*/
