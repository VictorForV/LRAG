"""Search tools for PostgreSQL RAG Agent with pgvector."""

import asyncio
import logging
import json
from typing import Optional, List
from pydantic_ai import RunContext
from pydantic import BaseModel, Field

from src.dependencies import AgentDependencies

logger = logging.getLogger(__name__)


# Get embedding dimension from settings
async def get_embedding_dimension() -> int:
    """Get the embedding dimension from settings."""
    from src.settings import load_settings
    settings = load_settings()
    return settings.embedding_dimension


class SearchResult(BaseModel):
    """Model for search results."""

    chunk_id: str = Field(..., description="Chunk UUID as string")
    document_id: str = Field(..., description="Parent document UUID as string")
    content: str = Field(..., description="Chunk text content")
    similarity: float = Field(..., description="Relevance score (0-1)")
    metadata: dict = Field(default_factory=dict, description="Chunk metadata")
    document_title: str = Field(..., description="Title from document lookup")
    document_source: str = Field(..., description="Source from document lookup")
    project_id: Optional[str] = Field(default=None, description="Project UUID")


def _parse_metadata(metadata_value) -> dict:
    """Parse metadata from PostgreSQL JSONB to dict."""
    if isinstance(metadata_value, dict):
        return metadata_value
    elif isinstance(metadata_value, str):
        try:
            return json.loads(metadata_value)
        except:
            return {}
    else:
        return {}


async def semantic_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: Optional[int] = None,
    project_id: Optional[str] = None
) -> List[SearchResult]:
    """
    Perform pure semantic search using pgvector cosine similarity.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)
        project_id: Optional project UUID to filter results

    Returns:
        List of search results ordered by similarity
    """
    try:
        deps = ctx.deps

        if match_count is None:
            match_count = deps.settings.default_match_count

        match_count = min(match_count, deps.settings.max_match_count)

        # Use project_id from context if not provided
        if project_id is None:
            project_id = deps.project_id

        # Generate embedding for query
        query_embedding = await deps.get_embedding(query)

        # Convert to pgvector format
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Call semantic_search function with project filter
        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(
                "SELECT * FROM semantic_search($1::vector, $2, $3)",
                embedding_str,
                match_count,
                project_id
            )

        search_results = [
            SearchResult(
                chunk_id=str(row["chunk_id"]),
                document_id=str(row["document_id"]),
                content=row["content"],
                similarity=float(row["similarity"]),
                metadata=_parse_metadata(row.get("metadata")),
                document_title=row["document_title"],
                document_source=row["document_source"],
                project_id=str(row["project_id"]) if row.get("project_id") else None
            )
            for row in results
        ]

        logger.info(f"semantic_search_completed: query={query}, results={len(search_results)}")

        return search_results

    except Exception as e:
        logger.exception(f"semantic_search_error: query={query}, error={e}")
        return []


async def text_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: Optional[int] = None,
    project_id: Optional[str] = None
) -> List[SearchResult]:
    """
    Perform full-text search using PostgreSQL GIN index.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)
        project_id: Optional project UUID to filter results

    Returns:
        List of search results ordered by text relevance
    """
    try:
        deps = ctx.deps

        if match_count is None:
            match_count = deps.settings.default_match_count

        match_count = min(match_count, deps.settings.max_match_count)

        # Use project_id from context if not provided
        if project_id is None:
            project_id = deps.project_id

        # Convert query to tsquery
        ts_query = " | ".join(query.split())

        # Call text_search function with project filter
        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(
                "SELECT * FROM text_search($1::tsquery, $2, $3)",
                ts_query,
                match_count,
                project_id
            )

        search_results = [
            SearchResult(
                chunk_id=str(row["chunk_id"]),
                document_id=str(row["document_id"]),
                content=row["content"],
                similarity=float(row["similarity"]),
                metadata=_parse_metadata(row.get("metadata")),
                document_title=row["document_title"],
                document_source=row["document_source"],
                project_id=str(row["project_id"]) if row.get("project_id") else None
            )
            for row in results
        ]

        logger.info(f"text_search_completed: query={query}, results={len(search_results)}")

        return search_results

    except Exception as e:
        logger.exception(f"text_search_error: query={query}, error={e}")
        return []


async def hybrid_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: Optional[int] = None,
    text_weight: Optional[float] = None,
    project_id: Optional[str] = None
) -> List[SearchResult]:
    """
    Perform hybrid search combining semantic and keyword matching using RRF.

    Uses PostgreSQL function with built-in Reciprocal Rank Fusion.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)
        text_weight: Weight for text matching (not used in RRF, kept for compatibility)
        project_id: Optional project UUID to filter results

    Returns:
        List of search results sorted by combined RRF score
    """
    try:
        deps = ctx.deps

        if match_count is None:
            match_count = deps.settings.default_match_count

        match_count = min(match_count, deps.settings.max_match_count)

        if text_weight is None:
            text_weight = deps.settings.default_text_weight

        # Use project_id from context if not provided
        if project_id is None:
            project_id = deps.project_id

        # Generate embedding for query
        query_embedding = await deps.get_embedding(query)
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Convert query to tsquery
        ts_query = " | ".join(query.split())

        logger.info(f"hybrid_search starting: query='{query}', match_count={match_count}")

        # Call hybrid_search function with RRF and project filter
        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(
                "SELECT * FROM hybrid_search($1::vector, $2::tsquery, $3, $4, $5)",
                embedding_str,
                ts_query,
                match_count,
                text_weight,
                project_id
            )

        search_results = [
            SearchResult(
                chunk_id=str(row["chunk_id"]),
                document_id=str(row["document_id"]),
                content=row["content"],
                similarity=float(row["combined_score"]),
                metadata=_parse_metadata(row.get("metadata")),
                document_title=row["document_title"],
                document_source=row["document_source"],
                project_id=str(row["project_id"]) if row.get("project_id") else None
            )
            for row in results
        ]

        logger.info(
            f"hybrid_search_completed: query='{query}', returned={len(search_results)}"
        )

        return search_results

    except Exception as e:
        logger.exception(f"hybrid_search_error: query={query}, error={e}")
        # Fallback to semantic search
        try:
            logger.info("Falling back to semantic search only")
            return await semantic_search(ctx, query, match_count, project_id)
        except:
            return []
