"""Pydantic models for API responses."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# HEALTH RESPONSE
# ============================================================================

class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status")
    database_connected: bool = Field(..., description="Database connection status")
    version: str = Field(default="1.0.0", description="API version")


# ============================================================================
# PROJECT RESPONSE
# ============================================================================

class Project(BaseModel):
    """Response model for a project."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    doc_count: int = Field(default=0, description="Number of documents")
    session_count: int = Field(default=0, description="Number of sessions")


# ============================================================================
# SESSION RESPONSE
# ============================================================================

class Session(BaseModel):
    """Response model for a chat session."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Session ID")
    project_id: str = Field(..., description="Project ID")
    title: str = Field(..., description="Session title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages")


# ============================================================================
# MESSAGE RESPONSE
# ============================================================================

class Message(BaseModel):
    """Response model for a chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")
    created_at: datetime = Field(..., description="Creation timestamp")


# ============================================================================
# DOCUMENT RESPONSE
# ============================================================================

class Document(BaseModel):
    """Response model for a document."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Document source file")
    uri: Optional[str] = Field(None, description="Document URI")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    project_id: Optional[str] = Field(None, description="Project ID")
    first_ingested: datetime = Field(..., description="First ingestion timestamp")
    last_ingested: datetime = Field(..., description="Last ingestion timestamp")
    ingestion_count: int = Field(default=1, description="Number of times ingested")
    chunk_count: Optional[int] = Field(None, description="Number of chunks")


# ============================================================================
# UPLOAD RESULT
# ============================================================================

class UploadResult(BaseModel):
    """Response model for file upload result."""

    filename: str = Field(..., description="Uploaded filename")
    success: bool = Field(..., description="Whether upload succeeded")
    chunks: int = Field(default=0, description="Number of chunks created")
    status: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# CHAT STREAMING EVENTS
# ============================================================================

class ChatChunkEvent(BaseModel):
    """Server-Sent Event for chat streaming."""

    event: str = Field(..., description="Event type: start, chunk, done, error")
    content: str = Field(default="", description="Chunk content or error message")
    session_id: Optional[str] = Field(None, description="Session ID")
    message_id: Optional[str] = Field(None, description="Saved message ID")


# ============================================================================
# SETTINGS RESPONSE
# ============================================================================

class SettingsResponse(BaseModel):
    """Response model for application settings."""

    llm_model: str = Field(..., description="LLM model")
    embedding_model: str = Field(..., description="Embedding model")
    audio_model: str = Field(..., description="Audio model")
    database_name: str = Field(..., description="Database name")
    llm_api_key_configured: bool = Field(..., description="Whether LLM API key is set")
    embedding_api_key_configured: bool = Field(..., description="Whether embedding API key is set")
    llm_provider: str = Field(..., description="LLM provider")
    embedding_dimension: int = Field(..., description="Embedding vector dimension")
