"""
Graph-based search tools for RAG system.

Enables finding documents by entities and relationships.
"""

import logging
from typing import List, Optional, Dict, Any
from pydantic_ai import RunContext
from pydantic import BaseModel, Field

from src.dependencies import AgentDependencies

logger = logging.getLogger(__name__)


class GraphResult(BaseModel):
    """Result from graph search."""

    document_id: str = Field(..., description="Document UUID")
    document_title: str = Field(..., description="Document title")
    document_source: str = Field(..., description="Document source file")
    entity_type: str = Field(..., description="Type of entity that matched")
    entity_name: str = Field(..., description="Entity that was found")
    content_snippet: str = Field(..., description="Relevant content snippet")


async def search_by_entity(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    entity_type: Optional[str] = None,
    match_count: int = 10
) -> List[GraphResult]:
    """
    Search documents by named entity (organization, person, etc.).

    Args:
        ctx: Agent runtime context with dependencies
        entity_name: Name of the entity to search for (e.g., "ООО Веллес")
        entity_type: Optional entity type filter (ORG, PER, DATE, MONEY, DOC_REF)
        match_count: Maximum number of results to return

    Returns:
        List of documents containing the entity
    """
    try:
        deps = ctx.deps

        query = """
            SELECT DISTINCT
                d.id as document_id,
                d.title as document_title,
                d.source as document_source,
                e.entity_type,
                e.entity_name,
                SUBSTRING(d.content, 1, 500) as content_snippet
            FROM entities e
            JOIN documents d ON e.document_id = d.id
            WHERE e.entity_name ILIKE $1
        """

        params = [f"%{entity_name}%"]

        if entity_type:
            query += " AND e.entity_type = $2"
            params.append(entity_type)

        query += f" LIMIT {match_count}"

        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(query, *params)

        graph_results = [
            GraphResult(
                document_id=str(row["document_id"]),
                document_title=row["document_title"],
                document_source=row["document_source"],
                entity_type=row["entity_type"],
                entity_name=row["entity_name"],
                content_snippet=row["content_snippet"] or ""
            )
            for row in results
        ]

        logger.info(
            f"search_by_entity: entity={entity_name}, type={entity_type}, "
            f"results={len(graph_results)}"
        )

        return graph_results

    except Exception as e:
        logger.exception(f"search_by_entity_error: entity={entity_name}, error={e}")
        return []


async def get_document_entities(
    ctx: RunContext[AgentDependencies],
    document_id: str
) -> List[Dict[str, Any]]:
    """
    Get all entities extracted from a specific document.

    Args:
        ctx: Agent runtime context with dependencies
        document_id: Document UUID

    Returns:
        List of entities with their types and names
    """
    try:
        deps = ctx.deps

        query = """
            SELECT entity_type, entity_name, entity_text
            FROM entities
            WHERE document_id = $1
            ORDER BY entity_type, entity_name
        """

        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(query, document_id)

        entities = [
            {
                "type": row["entity_type"],
                "name": row["entity_name"],
                "text": row["entity_text"]
            }
            for row in results
        ]

        logger.info(f"get_document_entities: document_id={document_id}, entities={len(entities)}")

        return entities

    except Exception as e:
        logger.exception(f"get_document_entities_error: document_id={document_id}, error={e}")
        return []


async def find_related_documents(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    max_depth: int = 2
) -> List[Dict[str, Any]]:
    """
    Find documents related through shared entities AND extracted relations.

    Combines two approaches:
    1. Documents mentioning the same entity (company, person)
    2. Documents connected through extracted relations (AMENDS, REFERENCES, etc.)

    Args:
        ctx: Agent runtime context with dependencies
        entity_name: Name of the entity to find related documents for
        max_depth: How many hops to search (default: 2 = direct + indirect relations)

    Returns:
        List of related documents with relationship info
    """
    try:
        deps = ctx.deps

        # Step 1: Find documents with the same entity
        entity_query = """
            SELECT DISTINCT
                d.id as document_id,
                d.title as document_title,
                d.source as document_source,
                e.entity_type,
                e.entity_name
            FROM entities e
            JOIN documents d ON e.document_id = d.id
            WHERE e.entity_name ILIKE $1
            ORDER BY d.title
            LIMIT 20
        """

        # Step 2: Find documents connected through relations
        # First get docs with the entity, then find their relations
        relations_query = """
            WITH entity_docs AS (
                SELECT DISTINCT d.id
                FROM entities e
                JOIN documents d ON e.document_id = d.id
                WHERE e.entity_name ILIKE $1
            )
            SELECT DISTINCT
                d.id as document_id,
                d.title as document_title,
                d.source as document_source,
                'RELATION' as entity_type,
                r.relation_type as entity_name,
                r.confidence as entity_count
            FROM entity_docs ed
            JOIN relations r ON r.source_document_id = ed.id OR r.target_document_id = ed.id
            JOIN documents d ON (r.source_document_id = d.id AND r.target_document_id IN (SELECT id FROM entity_docs))
                           OR (r.target_document_id = d.id AND r.source_document_id IN (SELECT id FROM entity_docs))
            WHERE d.id NOT IN (SELECT id FROM entity_docs)
            ORDER BY r.confidence DESC
            LIMIT 20
        """

        async with deps.db_pool.acquire() as conn:
            # Get documents by entity
            entity_results = await conn.fetch(entity_query, f"%{entity_name}%")

            # Get documents by relation (if max_depth > 1)
            relation_results = []
            if max_depth > 1:
                relation_results = await conn.fetch(relations_query, f"%{entity_name}%")

        # Combine results
        related = []

        for row in entity_results:
            related.append({
                "document_id": str(row["document_id"]),
                "title": row["document_title"],
                "source": row["document_source"],
                "entity_type": row["entity_type"],
                "entity_name": row["entity_name"],
                "strength": 1.0  # Direct entity match
            })

        for row in relation_results:
            # Avoid duplicates
            if not any(r["document_id"] == str(row["document_id"]) for r in related):
                related.append({
                    "document_id": str(row["document_id"]),
                    "title": row["document_title"],
                    "source": row["document_source"],
                    "entity_type": f"RELATION ({row['entity_type']})",
                    "entity_name": f"Connected via {row['entity_name']}",
                    "strength": row["entity_count"]
                })

        logger.info(
            f"find_related_documents: entity={entity_name}, "
            f"entity_docs={len(entity_results)}, relation_docs={len(relation_results)}, "
            f"total={len(related)}"
        )

        return related

    except Exception as e:
        logger.exception(f"find_related_documents_error: entity={entity_name}, error={e}")
        return []


async def search_by_context(
    ctx: RunContext[AgentDependencies],
    entity_names: List[str],
    match_count: int = 10
) -> List[Dict[str, Any]]:
    """
    Search documents that mention multiple entities (contextual search).

    Useful for finding documents that connect multiple entities.

    Args:
        ctx: Agent runtime context with dependencies
        entity_names: List of entity names to search for
        match_count: Maximum number of results to return

    Returns:
        List of documents with entity match counts
    """
    try:
        deps = ctx.deps

        if not entity_names:
            return []

        # Build dynamic query for multiple entities
        placeholders = ",".join([f"${i+1}" for i in range(len(entity_names))])
        query = f"""
            SELECT
                d.id as document_id,
                d.title as document_title,
                d.source as document_source,
                COUNT(DISTINCT e.entity_name) as matched_entities,
                STRING_AGG(DISTINCT e.entity_type, ', ') as entity_types
            FROM entities e
            JOIN documents d ON e.document_id = d.id
            WHERE e.entity_name ILIKE ANY(ARRAY[{placeholders}])
            GROUP BY d.id, d.title, d.source
            HAVING COUNT(DISTINCT e.entity_name) >= 1
            ORDER BY matched_entities DESC
            LIMIT {match_count}
        """

        params = [f"%{name}%" for name in entity_names]

        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(query, *params)

        documents = [
            {
                "document_id": str(row["document_id"]),
                "title": row["document_title"],
                "source": row["document_source"],
                "matched_entities": row["matched_entities"],
                "entity_types": row["entity_types"]
            }
            for row in results
        ]

        logger.info(
            f"search_by_context: entities={entity_names}, "
            f"results={len(documents)}"
        )

        return documents

    except Exception as e:
        logger.exception(f"search_by_context_error: entities={entity_names}, error={e}")
        return []


async def find_by_relation(
    ctx: RunContext[AgentDependencies],
    document_id: str,
    relation_types: Optional[List[str]] = None,
    max_depth: int = 1
) -> List[Dict[str, Any]]:
    """
    Find documents related through extracted relations.

    Uses the relations table to find documents connected by AMENDS,
    REFERENCES, PARTIES_TO, PAYS_FOR, or DELIVERS relationships.

    Args:
        ctx: Agent runtime context with dependencies
        document_id: Document UUID to find relations for
        relation_types: Optional list of relation types to filter (e.g., ["AMENDS", "REFERENCES"])
        max_depth: How many hops to search (default: 1 = direct relations only)

    Returns:
        List of related documents with relationship details
    """
    try:
        deps = ctx.deps

        # Find relations where this document is the source
        query = """
            SELECT
                r.id as relation_id,
                r.relation_type,
                r.confidence,
                r.metadata,
                d.id as document_id,
                d.title as document_title,
                d.source as document_source
            FROM relations r
            JOIN documents d ON r.target_document_id = d.id
            WHERE r.source_document_id = $1
        """

        params = [document_id]

        if relation_types:
            placeholders = ",".join([f"${i+2}" for i in range(len(relation_types))])
            query += f" AND r.relation_type = ANY(ARRAY[{placeholders}])"
            params.extend(relation_types)

        query += " ORDER BY r.confidence DESC LIMIT 50"

        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(query, *params)

        related = [
            {
                "relation_id": str(row["relation_id"]),
                "document_id": str(row["document_id"]),
                "title": row["document_title"],
                "source": row["document_source"],
                "relation_type": row["relation_type"],
                "confidence": row["confidence"],
                "metadata": row["metadata"]
            }
            for row in results
        ]

        logger.info(
            f"find_by_relation: document_id={document_id}, "
            f"relation_types={relation_types}, related={len(related)}"
        )

        return related

    except Exception as e:
        logger.exception(f"find_by_relation_error: document_id={document_id}, error={e}")
        return []


async def search_relations_by_entity(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    relation_type: Optional[str] = None,
    match_count: int = 10
) -> List[Dict[str, Any]]:
    """
    Find relations between documents that both mention the same entity.

    This is useful for discovering contract networks - all documents
    involving the same company, person, or contract reference.

    Args:
        ctx: Agent runtime context with dependencies
        entity_name: Name of the entity (company, person, etc.)
        relation_type: Optional relation type filter
        match_count: Maximum results to return

    Returns:
        List of relations with document details
    """
    try:
        deps = ctx.deps

        # Find documents with this entity
        query = """
            SELECT DISTINCT d.id
            FROM entities e
            JOIN documents d ON e.document_id = d.id
            WHERE e.entity_name ILIKE $1
            LIMIT 20
        """

        async with deps.db_pool.acquire() as conn:
            doc_rows = await conn.fetch(query, f"%{entity_name}%")

            if not doc_rows:
                return []

            doc_ids = [row["id"] for row in doc_rows]

            # Find relations between these documents (same connection)
            # Using UNNEST with proper UUID array handling
            doc_ids_str = ",".join([f"'{doc_id}'" for doc_id in doc_ids])
            rel_query = f"""
                SELECT DISTINCT
                    r.relation_type,
                    r.confidence,
                    d1.title as source_title,
                    d2.title as target_title,
                    r.metadata->>'reasoning' as reasoning
                FROM relations r
                JOIN documents d1 ON r.source_document_id = d1.id
                JOIN documents d2 ON r.target_document_id = d2.id
                WHERE r.source_document_id::text = ANY(ARRAY[{doc_ids_str}]::text[])
                   OR r.target_document_id::text = ANY(ARRAY[{doc_ids_str}]::text[])
                ORDER BY r.confidence DESC
                LIMIT {match_count}
            """

            results = await conn.fetch(rel_query)

            relations = [
                {
                    "relation_type": row["relation_type"],
                    "confidence": row["confidence"],
                    "source_title": row["source_title"],
                    "target_title": row["target_title"],
                    "reasoning": row["reasoning"]
                }
                for row in results
            ]

            logger.info(
                f"search_relations_by_entity: entity={entity_name}, "
                f"relations={len(relations)}"
            )

            return relations

    except Exception as e:
        logger.exception(f"search_relations_by_entity_error: entity={entity_name}, error={e}")
        return []
