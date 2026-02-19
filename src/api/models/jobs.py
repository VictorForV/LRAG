"""Pydantic models for background ingestion jobs."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IngestionJob(BaseModel):
    """Model for file ingestion job."""

    id: str = Field(..., description="Job ID")
    project_id: str = Field(..., description="Project ID")
    user_id: str = Field(..., description="User ID")
    filename: str = Field(..., description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    status: str = Field(..., description="Job status: pending, uploading, processing, completed, failed")
    progress: int = Field(0, description="Progress percentage 0-100")
    chunks_created: int = Field(0, description="Number of chunks created")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class JobStatus(BaseModel):
    """Simplified job status response."""

    job_id: str
    filename: str
    status: str
    progress: int
    chunks_created: int
    error_message: Optional[str] = None
