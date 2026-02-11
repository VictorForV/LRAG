"""Document management routes with file upload support."""

import json
import logging
import os
import tempfile
import hashlib
from typing import List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from src.api.models.responses import Document, UploadResult
from src.api.dependencies import get_db_pool
from src.settings import Settings
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


# ============================================================================
# GET PROJECT DOCUMENTS
# ============================================================================

@router.get("/projects/{project_id}/documents", response_model=List[Document])
async def get_project_documents(
    project_id: str,
    limit: int = 100,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[Document]:
    """
    Get all documents for a project.

    Args:
        project_id: Project UUID
        limit: Maximum documents to return
        pool: Database connection pool

    Returns:
        List of documents
    """
    try:
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
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> Document:
    """
    Get document details by ID.

    Args:
        document_id: Document UUID
        pool: Database connection pool

    Returns:
        Document details

    Raises:
        HTTPException: If document not found
    """
    try:
        row = await pool.fetchrow(
            """SELECT d.id, d.title, d.source, d.uri, d.metadata, d.project_id,
                      d.first_ingested, d.last_ingested, d.ingestion_count,
                      (SELECT COUNT(*) FROM chunks WHERE document_id = d.id) as chunk_count
               FROM documents d
               WHERE d.id = $1""",
            document_id
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
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> None:
    """
    Delete a document and all related data (chunks, entities, relations).

    Args:
        document_id: Document UUID
        pool: Database connection pool

    Raises:
        HTTPException: If deletion fails
    """
    try:
        result = await pool.execute("DELETE FROM documents WHERE id = $1", document_id)

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
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[UploadResult]:
    """
    Upload and process files for a project.

    Args:
        project_id: Project UUID
        files: List of files to upload
        pool: Database connection pool

    Returns:
        List of upload results

    Raises:
        HTTPException: If upload fails
    """
    results = []
    temp_dir = tempfile.mkdtemp()

    try:
        # Verify project exists
        project_exists = await pool.fetchval(
            "SELECT id FROM projects WHERE id = $1",
            project_id
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
                    project_id=project_id
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
