-- PostgreSQL schema for RAG with pgvector
-- Run this to create the required tables

-- Projects table - for organizing documents into projects (MUST BE FIRST!)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents table - stores source documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    uri TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    file_hash TEXT,
    first_ingested TIMESTAMPTZ DEFAULT NOW(),
    last_ingested TIMESTAMPTZ DEFAULT NOW(),
    ingestion_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks table - stores document chunks with embeddings
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(4096),  -- Qwen3-embedding-8b dimension
    chunk_index INTEGER NOT NULL,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Chat',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Entities table - for named entity extraction
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,  -- ORG, PER, DATE, MONEY, DOC_REF, etc.
    entity_name TEXT NOT NULL,
    entity_text TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Relations table - for document relationships
CREATE TABLE IF NOT EXISTS relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,  -- AMENDS, REFERENCES, PARTIES_TO, etc.
    confidence FLOAT DEFAULT 1.0,
    reasoning TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_document_id, target_document_id, relation_type)
);

-- Create indexes for better search performance
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_chunks_content_gin ON chunks USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON chat_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_entities_document_id ON entities(document_id);
CREATE INDEX IF NOT EXISTS idx_entities_name_type ON entities(entity_name, entity_type);
CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_document_id);

-- Function for semantic search (updated for project filtering)
CREATE OR REPLACE FUNCTION semantic_search(
    query_vector vector(4096),
    match_count INTEGER DEFAULT 10,
    p_project_id UUID DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    metadata JSONB,
    document_title TEXT,
    document_source TEXT,
    project_id UUID
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.content,
        1 - (c.embedding <=> query_vector) as similarity,
        c.metadata,
        d.title,
        d.source,
        d.project_id
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE (p_project_id IS NULL OR d.project_id = p_project_id)
    ORDER BY c.embedding <=> query_vector
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function for text search (updated for project filtering)
CREATE OR REPLACE FUNCTION text_search(
    query_text TEXT,
    match_count INTEGER DEFAULT 10,
    p_project_id UUID DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    metadata JSONB,
    document_title TEXT,
    document_source TEXT,
    project_id UUID
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.content,
        ts_rank(to_tsvector('english', c.content), query) as similarity,
        c.metadata,
        d.title,
        d.source,
        d.project_id
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE to_tsvector('english', c.content) @@ query
      AND (p_project_id IS NULL OR d.project_id = p_project_id)
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function for hybrid search with RRF (updated for project filtering)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_vector vector(4096),
    query_text TEXT,
    match_count INTEGER DEFAULT 10,
    text_weight FLOAT DEFAULT 0.3,
    p_project_id UUID DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    combined_score FLOAT,
    vector_similarity FLOAT,
    text_similarity FLOAT,
    metadata JSONB,
    document_title TEXT,
    document_source TEXT,
    project_id UUID
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic AS (
        SELECT
            c.id,
            1 - (c.embedding <=> query_vector) as score,
            ROW_NUMBER() OVER (ORDER BY c.embedding <=> query_vector) as rank
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE (p_project_id IS NULL OR d.project_id = p_project_id)
        LIMIT match_count * 2
    ),
    text AS (
        SELECT
            c.id,
            ts_rank(to_tsvector('english', c.content), query_text) as score,
            ROW_NUMBER() OVER (ORDER BY ts_rank(to_tsvector('english', c.content), query_text) DESC) as rank
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE to_tsvector('english', c.content) @@ query_text
          AND (p_project_id IS NULL OR d.project_id = p_project_id)
        LIMIT match_count * 2
    ),
    rrf AS (
        SELECT
            COALESCE(s.id, t.id) as id,
            COALESCE(1.0 / (60 + s.rank), 0.0) +
            COALESCE(1.0 / (60 + t.rank), 0.0) as combined_score,
            s.score as vector_score,
            t.score as text_score
        FROM semantic s
        FULL OUTER JOIN text t ON s.id = t.id
    )
    SELECT
        c.id,
        c.document_id,
        c.content,
        rrf.combined_score,
        COALESCE(rrf.vector_score, 0.0),
        COALESCE(rrf.text_score, 0.0),
        c.metadata,
        d.title,
        d.source,
        d.project_id
    FROM rrf
    JOIN chunks c ON rrf.id = c.id
    JOIN documents d ON c.document_id = d.id
    ORDER BY rrf.combined_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Helper function to get project stats
CREATE OR REPLACE FUNCTION get_project_stats(p_project_id UUID)
RETURNS TABLE (
    doc_count BIGINT,
    chunk_count BIGINT,
    session_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM documents WHERE project_id = p_project_id),
        (SELECT COUNT(*) FROM chunks c
         JOIN documents d ON c.document_id = d.id
         WHERE d.project_id = p_project_id),
        (SELECT COUNT(*) FROM chat_sessions WHERE project_id = p_project_id);
END;
$$ LANGUAGE plpgsql;

-- Helper function to update project timestamp
CREATE OR REPLACE FUNCTION update_project_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE projects SET updated_at = NOW()
    WHERE id = NEW.project_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to update project timestamps
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
