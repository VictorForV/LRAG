"""Dependencies for PostgreSQL RAG Agent."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, AsyncIterator
import logging
import asyncpg
import httpx
import openai
import hashlib
from pathlib import Path
from contextlib import asynccontextmanager
from src.settings import load_settings

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies injected into the agent context."""

    # Core dependencies
    db_pool: Optional[asyncpg.Pool] = None
    openai_client: Optional[openai.AsyncOpenAI] = None
    settings: Optional[Any] = None
    user_settings: Optional[Any] = None  # User-specific settings from database

    # Session context
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    query_history: list = field(default_factory=list)

    async def initialize(self) -> None:
        """
        Initialize external connections.

        Raises:
            Exception: If connection fails
        """
        if not self.settings:
            self.settings = load_settings()
            logger.info(f"settings_loaded, database={self.settings.database_name}")

        # Initialize PostgreSQL connection pool
        if not self.db_pool:
            try:
                self.db_pool = await asyncpg.create_pool(
                    self.settings.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60
                )
                # Test connection
                async with self.db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                logger.info(f"postgresql_connected, database={self.settings.database_name}")
            except Exception as e:
                logger.exception(f"postgresql_connection_failed, error={e}")
                raise

        # Initialize OpenAI client for LLM (not embeddings)
        if not self.openai_client:
            # Build proxy configuration if user has proxy settings
            http_client = None
            if self.user_settings and self.user_settings.get("http_proxy_host"):
                proxy_host = self.user_settings["http_proxy_host"]
                proxy_port = self.user_settings["http_proxy_port"]
                proxy_username = self.user_settings.get("http_proxy_username")
                proxy_password = self.user_settings.get("http_proxy_password")

                # Build proxy URL
                if proxy_username and proxy_password:
                    proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                else:
                    proxy_url = f"http://{proxy_host}:{proxy_port}"

                logger.info(f"Using HTTP proxy: {proxy_host}:{proxy_port}")
                http_client = httpx.AsyncClient(proxy=proxy_url, timeout=60.0)

            # Use user settings if available, otherwise fall back to global settings
            api_key = (self.user_settings.get("llm_api_key") or self.settings.llm_api_key) if self.user_settings else self.settings.llm_api_key
            base_url = (self.user_settings.get("llm_base_url") or self.settings.llm_base_url) if self.user_settings else self.settings.llm_base_url
            model = (self.user_settings.get("llm_model") or self.settings.llm_model) if self.user_settings else self.settings.llm_model

            self.openai_client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
            logger.info(f"openai_client_initialized, model={model}, proxy={bool(http_client)}")

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None
            logger.info("postgresql_connection_closed")

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenRouter.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        # Build proxy configuration if user has proxy settings
        proxy_url = None
        if self.user_settings and self.user_settings.get("http_proxy_host"):
            proxy_host = self.user_settings["http_proxy_host"]
            proxy_port = self.user_settings["http_proxy_port"]
            proxy_username = self.user_settings.get("http_proxy_username")
            proxy_password = self.user_settings.get("http_proxy_password")

            # Build proxy URL
            if proxy_username and proxy_password:
                proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
            else:
                proxy_url = f"http://{proxy_host}:{proxy_port}"

        # Use user settings if available, otherwise fall back to global settings
        api_key = (self.user_settings.get("embedding_api_key") or self.settings.embedding_api_key) if self.user_settings else self.settings.embedding_api_key
        base_url = (self.user_settings.get("embedding_base_url") or self.settings.embedding_base_url or self.settings.llm_base_url) if self.user_settings else (self.settings.embedding_base_url or self.settings.llm_base_url)
        model = (self.user_settings.get("embedding_model") or self.settings.embedding_model) if self.user_settings else self.settings.embedding_model

        # Direct HTTP request to OpenRouter for embeddings
        async with httpx.AsyncClient(timeout=60.0, proxy=proxy_url) as client:
            response = await client.post(
                f"{base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": text,
                }
            )
            response.raise_for_status()
            data = response.json()

            # OpenRouter format: { "data": [ { "embedding": [...] }, ... ] }
            if "data" not in data:
                raise ValueError(f"Unexpected response format: {data}")

            embeddings = [item["embedding"] for item in data["data"]]

            if not embeddings:
                raise ValueError(f"No embeddings in response: {data}")

            return embeddings[0]

    def set_user_preference(self, key: str, value: Any) -> None:
        """Set a user preference for the session."""
        self.user_preferences[key] = value

    def add_to_history(self, query: str) -> None:
        """Add a query to the search history."""
        self.query_history.append(query)
        if len(self.query_history) > 10:
            self.query_history.pop(0)


@asynccontextmanager
async def db_pool_context(database_url: str) -> AsyncIterator[asyncpg.Pool]:
    """
    Context manager for database pool.

    Usage:
        async with db_pool_context(url) as pool:
            await pool.fetch("SELECT ...")
    """
    pool = None
    try:
        pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        yield pool
    finally:
        if pool:
            await pool.close()


# ============================================================================
# PROJECT MANAGEMENT FUNCTIONS
# ============================================================================

async def create_project(
    pool: asyncpg.Pool,
    name: str,
    description: Optional[str] = None
) -> str:
    """
    Create a new project.

    Args:
        pool: Database connection pool
        name: Project name (must be unique)
        description: Optional project description

    Returns:
        Project ID as string

    Raises:
        asyncpg.UniqueViolationError: If project name already exists
    """
    project_id = await pool.fetchval(
        "INSERT INTO projects (name, description) VALUES ($1, $2) RETURNING id",
        name, description
    )
    logger.info(f"Created project: {name} (id={project_id})")
    return str(project_id)


async def get_project(pool: asyncpg.Pool, project_id: str) -> Optional[Dict[str, Any]]:
    """
    Get project details by ID.

    Args:
        pool: Database connection pool
        project_id: Project UUID

    Returns:
        Project dict or None if not found
    """
    row = await pool.fetchrow(
        "SELECT id, name, description, created_at, updated_at FROM projects WHERE id = $1",
        project_id
    )
    if row:
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    return None


async def list_projects(
    pool: asyncpg.Pool,
    search: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    List all projects with optional search.

    Args:
        pool: Database connection pool
        search: Optional search term for name/description
        limit: Maximum results to return

    Returns:
        List of project dicts with stats
    """
    if search:
        rows = await pool.fetch(
            """SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                      COUNT(DISTINCT d.id) as doc_count,
                      COUNT(DISTINCT s.id) as session_count
               FROM projects p
               LEFT JOIN documents d ON d.project_id = p.id
               LEFT JOIN chat_sessions s ON s.project_id = p.id
               WHERE p.name ILIKE $1 OR p.description ILIKE $1
               GROUP BY p.id
               ORDER BY p.updated_at DESC
               LIMIT $2""",
            f"%{search}%", limit
        )
    else:
        rows = await pool.fetch(
            """SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                      COUNT(DISTINCT d.id) as doc_count,
                      COUNT(DISTINCT s.id) as session_count
               FROM projects p
               LEFT JOIN documents d ON d.project_id = p.id
               LEFT JOIN chat_sessions s ON s.project_id = p.id
               GROUP BY p.id
               ORDER BY p.updated_at DESC
               LIMIT $1""",
            limit
        )

    return [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "doc_count": row["doc_count"] or 0,
            "session_count": row["session_count"] or 0
        }
        for row in rows
    ]


async def update_project(
    pool: asyncpg.Pool,
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> bool:
    """
    Update project details.

    Args:
        pool: Database connection pool
        project_id: Project UUID
        name: New name (optional)
        description: New description (optional)

    Returns:
        True if updated, False if not found
    """
    updates = []
    params = []
    param_count = 1

    if name is not None:
        updates.append(f"name = ${param_count}")
        params.append(name)
        param_count += 1

    if description is not None:
        updates.append(f"description = ${param_count}")
        params.append(description)
        param_count += 1

    if not updates:
        return False

    params.append(project_id)
    query = f"UPDATE projects SET {', '.join(updates)}, updated_at = NOW() WHERE id = ${param_count}"

    result = await pool.execute(query, *params)
    return "UPDATE 1" in result


async def delete_project(pool: asyncpg.Pool, project_id: str) -> bool:
    """
    Delete a project (cascades to sessions, documents).

    Args:
        pool: Database connection pool
        project_id: Project UUID

    Returns:
        True if deleted, False if not found
    """
    result = await pool.execute("DELETE FROM projects WHERE id = $1", project_id)
    return "DELETE 1" in result


# ============================================================================
# CHAT SESSION FUNCTIONS
# ============================================================================

async def create_session(
    pool: asyncpg.Pool,
    project_id: str,
    title: str = "New Chat"
) -> str:
    """
    Create a new chat session.

    Args:
        pool: Database connection pool
        project_id: Project UUID
        title: Session title

    Returns:
        Session ID as string
    """
    session_id = await pool.fetchval(
        "INSERT INTO chat_sessions (project_id, title) VALUES ($1, $2) RETURNING id",
        project_id, title
    )
    logger.info(f"Created session: {title} (project={project_id}, id={session_id})")
    return str(session_id)


async def get_session(pool: asyncpg.Pool, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get session details by ID.

    Args:
        pool: Database connection pool
        session_id: Session UUID

    Returns:
        Session dict or None if not found
    """
    row = await pool.fetchrow(
        """SELECT id, project_id, title, created_at, updated_at
           FROM chat_sessions WHERE id = $1""",
        session_id
    )
    if row:
        return {
            "id": str(row["id"]),
            "project_id": str(row["project_id"]),
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    return None


async def list_sessions(
    pool: asyncpg.Pool,
    project_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    List all sessions for a project.

    Args:
        pool: Database connection pool
        project_id: Project UUID
        limit: Maximum results to return

    Returns:
        List of session dicts
    """
    rows = await pool.fetch(
        """SELECT id, project_id, title, created_at, updated_at,
                  (SELECT COUNT(*) FROM chat_messages WHERE session_id = cs.id) as message_count
           FROM chat_sessions cs
           WHERE project_id = $1
           ORDER BY updated_at DESC
           LIMIT $2""",
        project_id, limit
    )

    return [
        {
            "id": str(row["id"]),
            "project_id": str(row["project_id"]),
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "message_count": row["message_count"] or 0
        }
        for row in rows
    ]


async def update_session(
    pool: asyncpg.Pool,
    session_id: str,
    title: Optional[str] = None
) -> bool:
    """
    Update session title.

    Args:
        pool: Database connection pool
        session_id: Session UUID
        title: New title

    Returns:
        True if updated, False if not found
    """
    result = await pool.execute(
        "UPDATE chat_sessions SET title = $1, updated_at = NOW() WHERE id = $2",
        title, session_id
    )
    return "UPDATE 1" in result


async def delete_session(pool: asyncpg.Pool, session_id: str) -> bool:
    """
    Delete a session (cascades to messages).

    Args:
        pool: Database connection pool
        session_id: Session UUID

    Returns:
        True if deleted, False if not found
    """
    result = await pool.execute("DELETE FROM chat_sessions WHERE id = $1", session_id)
    return "DELETE 1" in result


async def clear_session_messages(pool: asyncpg.Pool, session_id: str) -> int:
    """
    Delete all messages from a session.

    Args:
        pool: Database connection pool
        session_id: Session UUID

    Returns:
        Number of messages deleted
    """
    result = await pool.execute("DELETE FROM chat_messages WHERE session_id = $1", session_id)
    # Parse "DELETE n" from result
    count = int(result.split()[-1])
    return count


# ============================================================================
# CHAT MESSAGE FUNCTIONS
# ============================================================================

async def add_message(
    pool: asyncpg.Pool,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Add a message to a session.

    Args:
        pool: Database connection pool
        session_id: Session UUID
        role: Message role ('user' or 'assistant')
        content: Message content
        metadata: Optional metadata dict

    Returns:
        Message ID as string
    """
    import json

    message_id = await pool.fetchval(
        """INSERT INTO chat_messages (session_id, role, content, metadata)
           VALUES ($1, $2, $3, $4::jsonb) RETURNING id""",
        session_id, role, content, json.dumps(metadata or {})
    )
    return str(message_id)


async def get_session_messages(
    pool: asyncpg.Pool,
    session_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get all messages for a session.

    Args:
        pool: Database connection pool
        session_id: Session UUID
        limit: Maximum messages to return

    Returns:
        List of message dicts ordered by creation time
    """
    rows = await pool.fetch(
        """SELECT id, session_id, role, content, metadata, created_at
           FROM chat_messages
           WHERE session_id = $1
           ORDER BY created_at ASC
           LIMIT $2""",
        session_id, limit
    )

    return [
        {
            "id": str(row["id"]),
            "session_id": str(row["session_id"]),
            "role": row["role"],
            "content": row["content"],
            "metadata": row["metadata"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


# ============================================================================
# DOCUMENT FUNCTIONS
# ============================================================================

async def get_project_documents(
    pool: asyncpg.Pool,
    project_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get all documents for a project.

    Args:
        pool: Database connection pool
        project_id: Project UUID
        limit: Maximum documents to return

    Returns:
        List of document dicts
    """
    rows = await pool.fetch(
        """SELECT id, title, source, uri, metadata, project_id,
                  first_ingested, last_ingested, ingestion_count, created_at
           FROM documents
           WHERE project_id = $1
           ORDER BY last_ingested DESC
           LIMIT $2""",
        project_id, limit
    )

    return [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "source": row["source"],
            "uri": row["uri"],
            "metadata": row["metadata"],
            "project_id": str(row["project_id"]) if row["project_id"] else None,
            "first_ingested": row["first_ingested"],
            "last_ingested": row["last_ingested"],
            "ingestion_count": row["ingestion_count"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


async def find_document_by_hash(
    pool: asyncpg.Pool,
    file_name: str,
    file_hash: str,
    project_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Find a document by file hash and name.

    Args:
        pool: Database connection pool
        file_name: Original filename
        file_hash: SHA256 hash of file contents
        project_id: Optional project UUID to filter by

    Returns:
        Document dict if found, None otherwise
    """
    if project_id:
        row = await pool.fetchrow(
            """SELECT id, title, source, file_hash, ingestion_count
               FROM documents
               WHERE source = $1 AND file_hash = $2 AND project_id = $3""",
            file_name, file_hash, project_id
        )
    else:
        row = await pool.fetchrow(
            """SELECT id, title, source, file_hash, ingestion_count
               FROM documents
               WHERE source = $1 AND file_hash = $2""",
            file_name, file_hash
        )

    if row:
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "source": row["source"],
            "file_hash": row["file_hash"],
            "ingestion_count": row["ingestion_count"]
        }
    return None


async def update_document_ingestion(
    pool: asyncpg.Pool,
    document_id: str
) -> None:
    """
    Update document ingestion metadata.

    Args:
        pool: Database connection pool
        document_id: Document UUID
    """
    await pool.execute(
        """UPDATE documents
           SET last_ingested = NOW(),
               ingestion_count = ingestion_count + 1
           WHERE id = $1""",
        document_id
    )


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


# ============================================================================
# CHUNK FUNCTIONS
# ============================================================================

async def get_document_chunk_count(
    pool: asyncpg.Pool,
    document_id: str
) -> int:
    """
    Get number of chunks for a document.

    Args:
        pool: Database connection pool
        document_id: Document UUID

    Returns:
        Number of chunks
    """
    count = await pool.fetchval(
        "SELECT COUNT(*) FROM chunks WHERE document_id = $1",
        document_id
    )
    return count or 0


async def delete_document_chunks(pool: asyncpg.Pool, document_id: str) -> int:
    """
    Delete all chunks for a document.

    Args:
        pool: Database connection pool
        document_id: Document UUID

    Returns:
        Number of chunks deleted
    """
    result = await pool.execute(
        "DELETE FROM chunks WHERE document_id = $1",
        document_id
    )
    return int(result.split()[-1])


async def delete_document(pool: asyncpg.Pool, document_id: str) -> bool:
    """
    Delete a document and all related data (chunks, entities, relations).

    Args:
        pool: Database connection pool
        document_id: Document UUID

    Returns:
        True if deleted, False if not found
    """
    result = await pool.execute("DELETE FROM documents WHERE id = $1", document_id)
    return "DELETE 1" in result


# ============================================================================
# DEFAULT PROJECT CREATION
# ============================================================================

async def get_or_create_default_project(pool: asyncpg.Pool) -> str:
    """
    Get or create the default project.

    Args:
        pool: Database connection pool

    Returns:
        Default project ID as string
    """
    # Try to find existing default project
    project_id = await pool.fetchval(
        "SELECT id FROM projects WHERE name = 'Default' LIMIT 1"
    )

    if project_id:
        return str(project_id)

    # Create default project
    return await create_project(pool, "Default", "Default project for unassigned documents")
