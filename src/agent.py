"""Main PostgreSQL RAG agent implementation with shared state."""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import Optional

from src.providers import get_llm_model
from src.dependencies import AgentDependencies
from src.prompts import MAIN_SYSTEM_PROMPT
from src.tools import semantic_search, hybrid_search, text_search
from src.graph_tools import (
    search_by_entity,
    find_related_documents,
    get_document_entities,
    find_by_relation,
    search_relations_by_entity
)


class RAGState(BaseModel):
    """Shared state for the RAG agent."""
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    project_name: Optional[str] = None


# Create the RAG agent with default model from settings
# User-specific model will be passed in run() to override
rag_agent = Agent(
    get_llm_model(),  # Default model (will be overridden in run())
    deps_type=AgentDependencies,
    system_prompt=MAIN_SYSTEM_PROMPT
)


@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "hybrid"
) -> str:
    """
    Search the knowledge base for relevant information.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 5)
        search_type: Type of search - "semantic" or "text" or "hybrid" (default: hybrid)

    Returns:
        String containing the retrieved information formatted for the LLM
    """
    try:
        # Get project_id from deps if available
        deps = ctx.deps
        project_id = getattr(deps, 'project_id', None) or getattr(deps, 'project_id', None)

        # Perform the search based on type
        if search_type == "hybrid":
            results = await hybrid_search(
                ctx=ctx,
                query=query,
                match_count=match_count,
                project_id=project_id
            )
        elif search_type == "semantic":
            results = await semantic_search(
                ctx=ctx,
                query=query,
                match_count=match_count,
                project_id=project_id
            )
        else:
            results = await text_search(
                ctx=ctx,
                query=query,
                match_count=match_count,
                project_id=project_id
            )

        # Format results as a simple string
        if not results:
            return "No relevant information found in the knowledge base."

        # Build a formatted response
        response_parts = [f"Found {len(results)} relevant documents:\n"]

        for i, result in enumerate(results, 1):
            response_parts.append(f"\n--- Document {i}: {result.document_title} (relevance: {result.similarity:.2f}) ---")
            response_parts.append(result.content)

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"


@rag_agent.tool
async def search_by_entity_name(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    entity_type: Optional[str] = None,
    match_count: Optional[int] = 5
) -> str:
    """
    Search documents by named entity (organization, person, date, amount, etc.).

    This tool is useful for finding all documents that mention a specific company,
    person, or other entity extracted from the document corpus.

    Args:
        ctx: Agent runtime context with dependencies
        entity_name: Name of the entity to search for (e.g., "ООО Веллес", "Иванов")
        entity_type: Optional entity type filter - "ORG" (organization), "PER" (person),
                     "DATE" (date), "MONEY" (amount), "DOC_REF" (document reference)
        match_count: Maximum number of results to return (default: 5)

    Returns:
        String containing the documents that mention the entity
    """
    try:
        deps = ctx.deps

        # Search by entity
        results = await search_by_entity(
            ctx=ctx,
            entity_name=entity_name,
            entity_type=entity_type,
            match_count=match_count
        )

        if not results:
            return f"No documents found mentioning '{entity_name}'."

        # Build formatted response
        response_parts = [f"Found {len(results)} documents mentioning '{entity_name}':\n"]

        for i, result in enumerate(results, 1):
            response_parts.append(f"\n--- Document {i}: {result.document_title} ({result.entity_type}) ---")
            response_parts.append(f"Entity: {result.entity_name}")
            response_parts.append(result.content_snippet[:300] + "..." if len(result.content_snippet) > 300 else result.content_snippet)

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error searching by entity: {str(e)}"


@rag_agent.tool
async def find_related_by_entity(
    ctx: RunContext[AgentDependencies],
    entity_name: str
) -> str:
    """
    Find documents that are related through a shared entity.

    Useful for finding all documents that mention the same company, person, or reference
    the same document number.

    Args:
        ctx: Agent runtime context with dependencies
        entity_name: Name of the entity to find relations for

    Returns:
        String containing related documents with relationship info
    """
    try:
        deps = ctx.deps

        # Find related documents
        results = await find_related_documents(
            ctx=ctx,
            entity_name=entity_name
        )

        if not results:
            return f"No related documents found for '{entity_name}'."

        # Build formatted response
        response_parts = [f"Found {len(results)} documents related to '{entity_name}':\n"]

        for i, doc in enumerate(results, 1):
            response_parts.append(f"\n--- Document {i}: {doc['title']} ---")
            response_parts.append(f"Entity Type: {doc['entity_type']}")
            response_parts.append(f"Entity: {doc['entity_name']}")
            response_parts.append(f"Source: {doc['source']}")

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error finding related documents: {str(e)}"


@rag_agent.tool
async def find_document_relations(
    ctx: RunContext[AgentDependencies],
    entity_name: str
) -> str:
    """
    Find relations between documents that involve the same entity.

    This tool is useful for discovering contract networks - all documents
    and their relationships (AMENDS, REFERENCES, PARTIES_TO, etc.) that
    involve the same company, person, or contract reference.

    Args:
        ctx: Agent runtime context with dependencies
        entity_name: Name of the entity (company, person, contract number, etc.)

    Returns:
        String containing the relations found with document titles and relationship types
    """
    try:
        deps = ctx.deps

        # Search relations by entity
        results = await search_relations_by_entity(
            ctx=ctx,
            entity_name=entity_name
        )

        if not results:
            return f"No relations found for documents involving '{entity_name}'."

        # Build formatted response
        response_parts = [f"Found {len(results)} relations between documents involving '{entity_name}':\n"]

        for i, rel in enumerate(results, 1):
            response_parts.append(f"\n--- Relation {i}: {rel['relation_type']} ---")
            response_parts.append(f"From: {rel['source_title']}")
            response_parts.append(f"To: {rel['target_title']}")
            response_parts.append(f"Confidence: {rel['confidence']:.2f}")
            if rel.get('reasoning'):
                response_parts.append(f"Reasoning: {rel['reasoning']}")

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error finding document relations: {str(e)}"
