"""FastAPI dependencies for dependency injection."""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Request
from pathlib import Path

from src.settings import Settings, load_settings
from src.dependencies import db_pool_context, AgentDependencies
from src.api.models.auth import User
import asyncpg


# ============================================================================
# SETTINGS DEPENDENCY
# ============================================================================

async def get_settings() -> Settings:
    """
    Get application settings.

    Returns:
        Settings: Application settings

    Raises:
        HTTPException: If settings cannot be loaded
    """
    try:
        return load_settings()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load settings: {e}"
        )


# ============================================================================
# DATABASE POOL DEPENDENCY
# ============================================================================

async def get_db_pool(settings: Settings = Depends(get_settings)):
    """
    Get database connection pool.

    Yields:
        asyncpg.Pool: Database connection pool

    Raises:
        HTTPException: If database connection fails
    """
    try:
        async with db_pool_context(settings.database_url) as pool:
            yield pool
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {e}"
        )


# ============================================================================
# AGENT DEPENDENCIES
# ============================================================================

async def get_agent_dependencies(
    project_id: str,
    session_id: str,
    settings: Settings = Depends(get_settings)
) -> AsyncGenerator[AgentDependencies, None]:
    """
    Get agent dependencies with project context.

    Args:
        project_id: Project UUID
        session_id: Session UUID
        settings: Application settings

    Yields:
        AgentDependencies: Initialized agent dependencies

    Raises:
        HTTPException: If dependencies cannot be initialized
    """
    deps = AgentDependencies(
        project_id=project_id,
        session_id=session_id,
        settings=settings
    )

    try:
        await deps.initialize()
        yield deps
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize agent: {e}"
        )
    finally:
        await deps.cleanup()


# ============================================================================
# PATH VALIDATION
# ============================================================================

def ensure_uploads_dir() -> Path:
    """
    Ensure uploads directory exists.

    Returns:
        Path: Uploads directory path
    """
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    return uploads_dir


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

def hashlib_sha256(data: str) -> str:
    """
    Calculate SHA256 hash of string.

    Args:
        data: String to hash

    Returns:
        Hexadecimal hash string
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


async def get_current_user(
    request: Request,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> User:
    """
    Dependency to get current authenticated user from session cookie.

    Args:
        request: FastAPI request
        pool: Database connection pool

    Returns:
        Current user

    Raises:
        HTTPException: If not authenticated
    """
    # Get session token from cookie
    session_token = request.cookies.get("session_token")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    token_hash = hashlib_sha256(session_token)

    # Look up session with user
    row = await pool.fetchrow(
        """SELECT u.id, u.username, u.created_at, u.updated_at
           FROM user_sessions us
           JOIN users u ON us.user_id = u.id
           WHERE us.token_hash = $1 AND us.expires_at > NOW()""",
        token_hash
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    return User(
        id=str(row["id"]),
        username=row["username"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )


async def get_current_user_optional(
    request: Request,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> Optional[User]:
    """
    Optional version of get_current_user that returns None instead of raising.

    Args:
        request: FastAPI request
        pool: Database connection pool

    Returns:
        Current user or None if not authenticated
    """
    try:
        return await get_current_user(request, pool)
    except HTTPException:
        return None
