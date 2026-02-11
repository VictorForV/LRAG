"""FastAPI dependencies for dependency injection."""

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from pathlib import Path

from src.settings import Settings, load_settings
from src.dependencies import db_pool_context, AgentDependencies


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
