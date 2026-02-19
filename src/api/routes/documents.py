"""Document management routes with file upload support."""

import json
import logging
import os
import tempfile
import hashlib
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks

from src.api.models.responses import Document, UploadResult
from src.api.models.jobs import JobStatus
from src.api.dependencies import get_db_pool, get_current_user
from src.api.models.auth import User
from src.settings import Settings, load_settings
from src.api.models.requests import ProjectCreate
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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


async def process_file_background(
    job_id: str,
    file_path: str,
    filename: str,
    project_id: str,
    user_id: str
) -> None:
    """
    Background task to process uploaded file.

    Args:
        job_id: Job UUID
        file_path: Path to uploaded file
        filename: Original filename
        project_id: Project UUID
        user_id: User UUID
    """
    settings = load_settings()
    pool = None

    try:
        # Connect to database
        pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)

        # Update job status to processing
        await pool.execute(
            """UPDATE ingestion_jobs
               SET status = 'processing', started_at = NOW(), progress = 10
               WHERE id = $1""",
            job_id
        )

        # Load user settings
        user_settings_row = await pool.fetchrow(
            """SELECT llm_api_key, llm_model, llm_base_url, llm_provider,
                      embedding_api_key, embedding_model, embedding_base_url,
                      http_proxy_host, http_proxy_port, http_proxy_username, http_proxy_password
               FROM user_settings WHERE user_id = $1""",
            user_id
        )

        # Check if file already exists
        file_hash = calculate_file_hash(file_path)
        existing = await pool.fetchrow(
            """SELECT id FROM documents
               WHERE source = $1 AND file_hash = $2 AND project_id = $3""",
            filename, file_hash, project_id
        )

        if existing:
            logger.warning(f"File {filename} already exists (duplicate)")
            await pool.execute(
                """UPDATE ingestion_jobs
                   SET status = 'failed',
                       progress = 100,
                       error_message = 'Файл с таким содержимым уже существует в проекте',
                       completed_at = NOW()
                   WHERE id = $1""",
                job_id
            )
            os.remove(file_path)
            return

        # Process document
        await pool.execute(
            """UPDATE ingestion_jobs SET progress = 30 WHERE id = $1""", job_id
        )

        from src.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig

        config = IngestionConfig(project_id=project_id, incremental=True)
        temp_dir = os.path.dirname(file_path)

        pipeline = DocumentIngestionPipeline(
            config=config,
            documents_folder=temp_dir,
            clean_before_ingest=False,
            project_id=project_id,
            user_settings=user_settings_row
        )
        await pipeline.initialize()

        await pool.execute(
            """UPDATE ingestion_jobs SET progress = 50 WHERE id = $1""", job_id
        )

        # Ingest file
        doc_result = await pipeline._ingest_single_document(file_path)
        await pipeline.close()

        if doc_result.errors:
            # Failed
            await pool.execute(
                """UPDATE ingestion_jobs
                   SET status = 'failed', error_message = $2, completed_at = NOW(), progress = 0
                   WHERE id = $1""",
                job_id, doc_result.errors[0]
            )
        else:
            # Success
            await pool.execute(
                """UPDATE ingestion_jobs
                   SET status = 'completed', chunks_created = $2, completed_at = NOW(), progress = 100
                   WHERE id = $1""",
                job_id, doc_result.chunks_created
            )

        # Clean up file
        os.remove(file_path)

    except Exception as e:
        logger.exception(f"Background processing failed for job {job_id}: {e}")
        if pool:
            await pool.execute(
                """UPDATE ingestion_jobs
                   SET status = 'failed', error_message = $2, completed_at = NOW()
                   WHERE id = $1""",
                job_id, str(e)
            )
        # Clean up file on error
        try:
            os.remove(file_path)
        except:
            pass

    finally:
        if pool:
            await pool.close()


# ============================================================================
# GET PROJECT DOCUMENTS
# ============================================================================

@router.get("/projects/{project_id}/documents", response_model=List[Document])
async def get_project_documents(
    project_id: str,
    limit: int = 100,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> List[Document]:
    """
    Get all documents for a project (verifies user owns the project).

    Args:
        project_id: Project UUID
        limit: Maximum documents to return
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        List of documents

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
            """SELECT d.id, d.title, d.source, d.uri, d.metadata, d.project_id,
                      d.first_ingested, d.last_ingested, d.ingestion_count,
                      (SELECT COUNT(*) FROM chunks WHERE document_id = d.id) as chunk_count
               FROM documents d
               WHERE d.project_id = $1
               ORDER BY d.last_ingested DESC
               LIMIT $2""",
            project_id, limit
        )

        return [
            Document(
                id=str(row["id"]),
                title=row["title"],
                source=row["source"],
                uri=row["uri"],
                metadata=parse_metadata(row["metadata"]),
                project_id=str(row["project_id"]) if row["project_id"] else None,
                first_ingested=row["first_ingested"],
                last_ingested=row["last_ingested"],
                ingestion_count=row["ingestion_count"],
                chunk_count=row["chunk_count"]
            )
            for row in rows
        ]

    except Exception as e:
        logger.exception(f"Error getting documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get documents: {e}"
        )


# ============================================================================
# GET DOCUMENT
# ============================================================================

@router.get("/documents/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> Document:
    """
    Get document details by ID (verifies user owns the project).

    Args:
        document_id: Document UUID
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        Document details

    Raises:
        HTTPException: If document not found or user doesn't own the project
    """
    try:
        row = await pool.fetchrow(
            """SELECT d.id, d.title, d.source, d.uri, d.metadata, d.project_id,
                      d.first_ingested, d.last_ingested, d.ingestion_count,
                      (SELECT COUNT(*) FROM chunks WHERE document_id = d.id) as chunk_count
               FROM documents d
               JOIN projects p ON d.project_id = p.id
               WHERE d.id = $1 AND p.user_id = $2""",
            document_id, user.id
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        return Document(
            id=str(row["id"]),
            title=row["title"],
            source=row["source"],
            uri=row["uri"],
            metadata=parse_metadata(row["metadata"]),
            project_id=str(row["project_id"]) if row["project_id"] else None,
            first_ingested=row["first_ingested"],
            last_ingested=row["last_ingested"],
            ingestion_count=row["ingestion_count"],
            chunk_count=row["chunk_count"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {e}"
        )


# ============================================================================
# DELETE DOCUMENT
# ============================================================================

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> None:
    """
    Delete a document (verifies user owns the project, cascades to chunks, entities, relations).

    Args:
        document_id: Document UUID
        pool: Database connection pool
        user: Current authenticated user

    Raises:
        HTTPException: If deletion fails or user doesn't own the project
    """
    try:
        result = await pool.execute(
            """DELETE FROM documents
               WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)""",
            document_id, user.id
        )

        if "DELETE 1" not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        logger.info(f"Deleted document: {document_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {e}"
        )


# ============================================================================
# UPLOAD FILES
# ============================================================================

@router.post("/projects/{project_id}/upload", response_model=List[UploadResult])
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> List[UploadResult]:
    """
    Upload and process files for a project (verifies user owns the project).

    Args:
        project_id: Project UUID
        files: List of files to upload
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        List of upload results

    Raises:
        HTTPException: If upload fails or user doesn't own the project
    """
    results = []
    temp_dir = tempfile.mkdtemp()

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

        for file in files:
            try:
                logger.info(f"Processing file: {file.filename} ({file.size})")

                # Save to temp file
                temp_path = os.path.join(temp_dir, file.filename)
                with open(temp_path, "wb") as f:
                    content = await file.read()
                    f.write(content)

                # Calculate file hash
                file_hash = calculate_file_hash(temp_path)

                # Check if already exists
                existing = await pool.fetchrow(
                    """SELECT id, title, ingestion_count
                       FROM documents
                       WHERE source = $1 AND file_hash = $2 AND project_id = $3""",
                    file.filename, file_hash, project_id
                )

                if existing:
                    logger.info(f"File {file.filename} already exists, skipping")
                    # Update ingestion metadata
                    await pool.execute(
                        "UPDATE documents SET last_ingested = NOW(), ingestion_count = ingestion_count + 1 WHERE id = $1",
                        existing["id"]
                    )
                    results.append(UploadResult(
                        filename=file.filename,
                        success=True,
                        chunks=0,
                        status="skipped (already exists)"
                    ))
                    os.remove(temp_path)
                    continue

                # Load user-specific settings for embeddings and proxy
                user_settings_row = await pool.fetchrow(
                    """SELECT llm_api_key, llm_model, llm_base_url, llm_provider,
                              embedding_api_key, embedding_model, embedding_base_url,
                              http_proxy_host, http_proxy_port, http_proxy_username, http_proxy_password
                       FROM user_settings WHERE user_id = $1""",
                    user.id
                )

                # Process document using ingestion pipeline
                from src.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig

                config = IngestionConfig(
                    project_id=project_id,
                    incremental=True
                )

                pipeline = DocumentIngestionPipeline(
                    config=config,
                    documents_folder=temp_dir,
                    clean_before_ingest=False,
                    project_id=project_id,
                    user_settings=user_settings_row
                )
                await pipeline.initialize()

                # Ingest single file
                doc_result = await pipeline._ingest_single_document(temp_path)
                await pipeline.close()

                results.append(UploadResult(
                    filename=file.filename,
                    success=len(doc_result.errors) == 0,
                    chunks=doc_result.chunks_created,
                    status="processed",
                    error=doc_result.errors[0] if doc_result.errors else None
                ))

                # Clean up temp file
                os.remove(temp_path)

            except Exception as e:
                logger.exception(f"Failed to process {file.filename}: {e}")
                results.append(UploadResult(
                    filename=file.filename,
                    success=False,
                    error=str(e)
                ))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {e}"
        )
    finally:
        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except:
            pass

    return results


# ============================================================================
# ASYNC UPLOAD FILES (with background processing)
# ============================================================================

@router.post("/projects/{project_id}/upload-async", response_model=List[JobStatus])
async def upload_files_async(
    project_id: str,
    files: List[UploadFile] = File(...),
    pool: asyncpg.Pool = Depends(get_db_pool),
    user: User = Depends(get_current_user)
) -> List[JobStatus]:
    """
    Upload files and process them in background.
    Returns immediately with job IDs for status tracking.

    Args:
        project_id: Project UUID
        files: List of files to upload
        pool: Database connection pool
        user: Current authenticated user

    Returns:
        List of job statuses

    Raises:
        HTTPException: If upload fails or user doesn't own the project
    """
    job_statuses = []
    temp_dir = tempfile.mkdtemp(prefix="rag_upload_")

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

        for file in files:
            try:
                logger.info(f"Uploading file: {file.filename} ({file.size} bytes)")

                # Save file to temp directory
                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)

                # Create job record
                job_id = await pool.fetchval(
                    """INSERT INTO ingestion_jobs
                       (project_id, user_id, filename, file_size, status, progress)
                       VALUES ($1, $2, $3, $4, 'pending', 0)
                       RETURNING id""",
                    project_id, user.id, file.filename, file.size or 0
                )

                # Start background processing
                asyncio.create_task(
                    process_file_background(
                        str(job_id), file_path, file.filename, project_id, user.id
                    )
                )

                job_statuses.append(JobStatus(
                    job_id=str(job_id),
                    filename=file.filename,
                    status="pending",
                    progress=0,
                    chunks_created=0
                ))

                logger.info(f"Created job {job_id} for {file.filename}")

            except Exception as e:
                logger.exception(f"Failed to start job for {file.filename}: {e}")
                job_statuses.append(JobStatus(
                    job_id="",
                    filename=file.filename,
                    status="failed",
                    progress=0,
                    chunks_created=0,
                    error_message=str(e)
                ))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {e}"
        )

    return job_statuses
