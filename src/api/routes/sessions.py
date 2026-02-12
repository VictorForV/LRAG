"""Chat session management routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.models.requests import SessionCreate, SessionUpdate
from src.api.models.responses import Session
from src.api.dependencies import get_db_pool, get_current_user
from src.api.models.auth import User
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sessions"])


# ============================================================================
# LIST SESSIONS
# ============================================================================

@router.get("/projects/{project_id}/sessions", response_model=List[Session])
async def list_sessions(
    project_id: str,
    limit: int = 50,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> List[Session]:
    """
    List all sessions for a project (verifies user owns the project).

    Args:
        project_id: Project UUID
        limit: Maximum results to return
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        List of sessions

    Raises:
        HTTPException: If user doesn't own the project
    """
    try:
        # Verify user owns the project
        project_exists = await pool.fetchval(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, user.id
        )
        if not project_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

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
            Session(
                id=str(row["id"]),
                project_id=str(row["project_id"]),
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                message_count=row["message_count"] or 0
            )
            for row in rows
        ]

    except Exception as e:
        logger.exception(f"Error listing sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {e}"
        )


# ============================================================================
# GET SESSION
# ============================================================================

@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> Session:
    """
    Get session details by ID (verifies user owns the project).

    Args:
        session_id: Session UUID
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Session details

    Raises:
        HTTPException: If session not found or user doesn't own the project
    """
    try:
        row = await pool.fetchrow(
            """SELECT cs.id, cs.project_id, cs.title, cs.created_at, cs.updated_at,
                      (SELECT COUNT(*) FROM chat_messages WHERE session_id = cs.id) as message_count
               FROM chat_sessions cs
               JOIN projects p ON cs.project_id = p.id
               WHERE cs.id = $1 AND p.user_id = $2""",
            session_id, user.id
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        return Session(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=row["message_count"] or 0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {e}"
        )


# ============================================================================
# CREATE SESSION
# ============================================================================

@router.post("/projects/{project_id}/sessions", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(
    project_id: str,
    session_data: SessionCreate,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> Session:
    """
    Create a new chat session (verifies user owns the project).

    Args:
        project_id: Project UUID
        session_data: Session creation data
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Created session

    Raises:
        HTTPException: If creation fails or user doesn't own the project
    """
    try:
        # Verify user owns the project
        project_exists = await pool.fetchval(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, user.id
        )
        if not project_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        session_id = await pool.fetchval(
            "INSERT INTO chat_sessions (project_id, title) VALUES ($1, $2) RETURNING id",
            project_id,
            session_data.title or "New Chat"
        )

        row = await pool.fetchrow(
            """SELECT id, project_id, title, created_at, updated_at
               FROM chat_sessions WHERE id = $1""",
            session_id
        )

        logger.info(f"Created session: {session_data.title} (project={project_id}, id={session_id})")

        return Session(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e}"
        )


# ============================================================================
# UPDATE SESSION
# ============================================================================

@router.put("/sessions/{session_id}", response_model=Session)
async def update_session(
    session_id: str,
    session_data: SessionUpdate,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> Session:
    """
    Update session title (verifies user owns the project).

    Args:
        session_id: Session UUID
        session_data: Session update data
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Updated session

    Raises:
        HTTPException: If session not found or user doesn't own the project
    """
    try:
        # Update and verify ownership in one query
        result = await pool.execute(
            """UPDATE chat_sessions
               SET title = $1, updated_at = NOW()
               WHERE id = $2 AND project_id IN (SELECT id FROM projects WHERE user_id = $3)""",
            session_data.title,
            session_id,
            user.id
        )

        if "UPDATE 1" not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        return await get_session(session_id, pool)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {e}"
        )


# ============================================================================
# DELETE SESSION
# ============================================================================

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> None:
    """
    Delete a session (verifies user owns the project, cascades to messages).

    Args:
        session_id: Session UUID
        pool: Database connection pool
        user: Current authenticated user

    Raises:
        HTTPException: If deletion fails or user doesn't own the project
    """
    try:
        result = await pool.execute(
            """DELETE FROM chat_sessions
               WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)""",
            session_id, user.id
        )

        if "DELETE 1" not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        logger.info(f"Deleted session: {session_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {e}"
        )
