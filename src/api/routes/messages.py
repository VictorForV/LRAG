"""Chat message management routes."""

import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.models.requests import MessageCreate
from src.api.models.responses import Message
from src.api.dependencies import get_db_pool
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["messages"])


def parse_metadata(metadata: Any) -> Dict[str, Any]:
    """
    Safely parse metadata from database to dict.

    Args:
        metadata: Metadata from database (can be dict, str, or None)

    Returns:
        Dict with metadata
    """
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except json.JSONDecodeError:
            return {}
    return {}


# ============================================================================
# GET SESSION MESSAGES
# ============================================================================

@router.get("/sessions/{session_id}/messages", response_model=List[Message])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[Message]:
    """
    Get all messages for a session.

    Args:
        session_id: Session UUID
        limit: Maximum messages to return
        pool: Database connection pool

    Returns:
        List of messages ordered by creation time
    """
    try:
        rows = await pool.fetch(
            """SELECT id, session_id, role, content, metadata, created_at
               FROM chat_messages
               WHERE session_id = $1
               ORDER BY created_at ASC
               LIMIT $2""",
            session_id, limit
        )

        return [
            Message(
                id=str(row["id"]),
                session_id=str(row["session_id"]),
                role=row["role"],
                content=row["content"],
                metadata=parse_metadata(row["metadata"]),
                created_at=row["created_at"]
            )
            for row in rows
        ]

    except Exception as e:
        logger.exception(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {e}"
        )


# ============================================================================
# ADD MESSAGE
# ============================================================================

@router.post("/sessions/{session_id}/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def add_message(
    session_id: str,
    message_data: MessageCreate,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> Message:
    """
    Add a message to a session.

    Args:
        session_id: Session UUID
        message_data: Message data
        pool: Database connection pool

    Returns:
        Created message

    Raises:
        HTTPException: If session not found or creation fails
    """
    try:
        # Verify session exists
        session_exists = await pool.fetchval(
            "SELECT id FROM chat_sessions WHERE id = $1",
            session_id
        )
        if not session_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        message_id = await pool.fetchval(
            """INSERT INTO chat_messages (session_id, role, content, metadata)
               VALUES ($1, $2, $3, $4::jsonb) RETURNING id""",
            session_id,
            message_data.role,
            message_data.content,
            json.dumps(message_data.metadata or {})
        )

        row = await pool.fetchrow(
            """SELECT id, session_id, role, content, metadata, created_at
               FROM chat_messages WHERE id = $1""",
            message_id
        )

        return Message(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            role=row["role"],
            content=row["content"],
            metadata=parse_metadata(row["metadata"]),
            created_at=row["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error adding message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {e}"
        )


# ============================================================================
# CLEAR SESSION MESSAGES
# ============================================================================

@router.delete("/sessions/{session_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
async def clear_session_messages(
    session_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> None:
    """
    Delete all messages from a session.

    Args:
        session_id: Session UUID
        pool: Database connection pool

    Returns:
        Number of messages deleted
    """
    try:
        result = await pool.execute(
            "DELETE FROM chat_messages WHERE session_id = $1",
            session_id
        )

        count = int(result.split()[-1])
        logger.info(f"Cleared {count} messages from session {session_id}")

    except Exception as e:
        logger.exception(f"Error clearing messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear messages: {e}"
        )
