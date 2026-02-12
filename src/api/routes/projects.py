"""Project management routes."""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.models.requests import ProjectCreate, ProjectUpdate
from src.api.models.responses import Project
from src.api.dependencies import get_db_pool, get_current_user
from src.api.models.auth import User
from src.settings import Settings
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ============================================================================
# LIST PROJECTS
# ============================================================================

@router.get("", response_model=List[Project])
async def list_projects(
    search: Optional[str] = None,
    limit: int = 100,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> List[Project]:
    """
    List all projects for current user with optional search.

    Args:
        search: Optional search term for name/description
        limit: Maximum results to return
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        List of projects with stats
    """
    try:
        if search:
            rows = await pool.fetch(
                """SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                          COUNT(DISTINCT d.id) as doc_count,
                          COUNT(DISTINCT s.id) as session_count
                   FROM projects p
                   LEFT JOIN documents d ON d.project_id = p.id
                   LEFT JOIN chat_sessions s ON s.project_id = p.id
                   WHERE p.user_id = $1 AND (p.name ILIKE $2 OR p.description ILIKE $2)
                   GROUP BY p.id
                   ORDER BY p.updated_at DESC
                   LIMIT $3""",
                user.id, f"%{search}%", limit
            )
        else:
            rows = await pool.fetch(
                """SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                          COUNT(DISTINCT d.id) as doc_count,
                          COUNT(DISTINCT s.id) as session_count
                   FROM projects p
                   LEFT JOIN documents d ON d.project_id = p.id
                   LEFT JOIN chat_sessions s ON s.project_id = p.id
                   WHERE p.user_id = $1
                   GROUP BY p.id
                   ORDER BY p.updated_at DESC
                   LIMIT $2""",
                user.id, limit
            )

        return [
            Project(
                id=str(row["id"]),
                name=row["name"],
                description=row["description"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                doc_count=row["doc_count"] or 0,
                session_count=row["session_count"] or 0
            )
            for row in rows
        ]

    except Exception as e:
        logger.exception(f"Error listing projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {e}"
        )


# ============================================================================
# GET PROJECT
# ============================================================================

@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> Project:
    """
    Get project details by ID (verifies user owns the project).

    Args:
        project_id: Project UUID
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Project details

    Raises:
        HTTPException: If project not found or user doesn't own it
    """
    try:
        row = await pool.fetchrow(
            """SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                      COUNT(DISTINCT d.id) as doc_count,
                      COUNT(DISTINCT s.id) as session_count
               FROM projects p
               LEFT JOIN documents d ON d.project_id = p.id
               LEFT JOIN chat_sessions s ON s.project_id = p.id
               WHERE p.id = $1 AND p.user_id = $2
               GROUP BY p.id""",
            project_id, user.id
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        return Project(
            id=str(row["id"]),
            name=row["name"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            doc_count=row["doc_count"] or 0,
            session_count=row["session_count"] or 0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {e}"
        )


# ============================================================================
# CREATE PROJECT
# ============================================================================

@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> Project:
    """
    Create a new project for the current user.

    Args:
        project_data: Project creation data
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Created project

    Raises:
        HTTPException: If project name already exists or creation fails
    """
    try:
        project_id = await pool.fetchval(
            "INSERT INTO projects (name, description, user_id) VALUES ($1, $2, $3) RETURNING id",
            project_data.name,
            project_data.description,
            user.id
        )

        row = await pool.fetchrow(
            """SELECT id, name, description, created_at, updated_at
               FROM projects WHERE id = $1""",
            project_id
        )

        logger.info(f"Created project: {project_data.name} (id={project_id})")

        return Project(
            id=str(row["id"]),
            name=row["name"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            doc_count=0,
            session_count=0
        )

    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project '{project_data.name}' already exists"
        )
    except Exception as e:
        logger.exception(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {e}"
        )


# ============================================================================
# UPDATE PROJECT
# ============================================================================

@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> Project:
    """
    Update project details (verifies user owns the project).

    Args:
        project_id: Project UUID
        project_data: Project update data
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Updated project

    Raises:
        HTTPException: If project not found or update fails
    """
    try:
        updates = []
        params = []
        param_count = 1

        if project_data.name is not None:
            updates.append(f"name = ${param_count}")
            params.append(project_data.name)
            param_count += 1

        if project_data.description is not None:
            updates.append(f"description = ${param_count}")
            params.append(project_data.description)
            param_count += 1

        if not updates:
            # No updates, return existing project
            return await get_project(project_id, pool, user)

        params.append(project_id)
        params.append(user.id)
        query = f"UPDATE projects SET {', '.join(updates)}, updated_at = NOW() WHERE id = ${param_count} AND user_id = ${param_count + 1}"

        result = await pool.execute(query, *params)

        if "UPDATE 1" not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        return await get_project(project_id, pool)

    except HTTPException:
        raise
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project '{project_data.name}' already exists"
        )
    except Exception as e:
        logger.exception(f"Error updating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {e}"
        )


# ============================================================================
# DELETE PROJECT
# ============================================================================

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> None:
    """
    Delete a project (verifies user owns the project, cascades to sessions, documents).

    Args:
        project_id: Project UUID
        pool: Database connection pool
        user: Current authenticated user

    Raises:
        HTTPException: If deletion fails or user doesn't own the project
    """
    try:
        result = await pool.execute("DELETE FROM projects WHERE id = $1 AND user_id = $2", project_id, user.id)

        if "DELETE 1" not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        logger.info(f"Deleted project: {project_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {e}"
        )
