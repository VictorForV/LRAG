"""Background job status routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from src.api.models.jobs import IngestionJob, JobStatus
from src.api.dependencies import get_db_pool, get_current_user
from src.api.models.auth import User
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> JobStatus:
    """
    Get status of a background ingestion job.

    Args:
        job_id: Job UUID
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Job status

    Raises:
        HTTPException: If job not found or user doesn't have access
    """
    try:
        row = await pool.fetchrow(
            """SELECT id, filename, status, progress, chunks_created, error_message
               FROM ingestion_jobs
               WHERE id = $1 AND user_id = $2""",
            job_id, user.id
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        return JobStatus(
            job_id=str(row["id"]),
            filename=row["filename"],
            status=row["status"],
            progress=row["progress"] or 0,
            chunks_created=row["chunks_created"] or 0,
            error_message=row["error_message"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {e}"
        )


@router.get("/projects/{project_id}/jobs", response_model=List[IngestionJob])
async def get_project_jobs(
    project_id: str,
    limit: int = 50,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> List[IngestionJob]:
    """
    Get all ingestion jobs for a project.

    Args:
        project_id: Project UUID
        limit: Maximum jobs to return
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        List of jobs

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
            """SELECT id, project_id, user_id, filename, file_size, status,
                      progress, chunks_created, error_message,
                      created_at, updated_at, started_at, completed_at
               FROM ingestion_jobs
               WHERE project_id = $1
               ORDER BY created_at DESC
               LIMIT $2""",
            project_id, limit
        )

        return [
            IngestionJob(
                id=str(row["id"]),
                project_id=str(row["project_id"]),
                user_id=str(row["user_id"]),
                filename=row["filename"],
                file_size=row["file_size"],
                status=row["status"],
                progress=row["progress"] or 0,
                chunks_created=row["chunks_created"] or 0,
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"]
            )
            for row in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting project jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get jobs: {e}"
        )
