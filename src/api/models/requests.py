"""Pydantic models for API requests."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# PROJECT REQUESTS
# ============================================================================

class ProjectCreate(BaseModel):
    """Request model for creating a project."""

    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")


# ============================================================================
# SESSION REQUESTS
# ============================================================================

class SessionCreate(BaseModel):
    """Request model for creating a chat session."""

    title: str = Field(default="New Chat", min_length=1, max_length=200, description="Session title")


class SessionUpdate(BaseModel):
    """Request model for updating a chat session."""

    title: str = Field(..., min_length=1, max_length=200, description="New session title")


# ============================================================================
# MESSAGE REQUESTS
# ============================================================================

class MessageCreate(BaseModel):
    """Request model for adding a message to a session."""

    role: str = Field(..., pattern="^(user|assistant)$", description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")


# ============================================================================
# CHAT REQUESTS
# ============================================================================

class ChatMessage(BaseModel):
    """Chat message in history."""

    role: str = Field(..., pattern="^(user|assistant)$", description="Message role")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for streaming chat."""

    session_id: str = Field(..., description="Session ID")
    project_id: str = Field(..., description="Project ID")
    message: str = Field(..., min_length=1, description="User message")
    message_history: List[ChatMessage] = Field(default_factory=list, description="Chat history")


# ============================================================================
# SETTINGS REQUESTS
# ============================================================================

class SettingsUpdate(BaseModel):
    """Request model for updating application settings."""

    llm_api_key: Optional[str] = Field(None, description="LLM API key")
    llm_model: Optional[str] = Field(None, description="LLM model")
    embedding_api_key: Optional[str] = Field(None, description="Embedding API key")
    embedding_model: Optional[str] = Field(None, description="Embedding model")
    audio_model: Optional[str] = Field(None, description="Audio transcription model")
    database_url: Optional[str] = Field(None, description="Database connection URL")
