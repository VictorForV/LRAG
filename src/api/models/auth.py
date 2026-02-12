"""Pydantic models for user authentication and authorization."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ============================================================================
# USER MODELS
# ============================================================================

class User(BaseModel):
    """User model representing an authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserCreate(BaseModel):
    """Request model for creating a user (admin only)."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=200, description="Password")


class UserLogin(BaseModel):
    """Request model for user login."""

    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


# ============================================================================
# USER SETTINGS MODELS
# ============================================================================

class UserSettings(BaseModel):
    """User-specific settings including API keys."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Settings ID")
    user_id: str = Field(..., description="User ID")
    llm_api_key: Optional[str] = Field(None, description="LLM API key (masked in response)")
    llm_model: Optional[str] = Field(None, description="LLM model")
    llm_base_url: Optional[str] = Field(None, description="LLM base URL")
    llm_provider: Optional[str] = Field(None, description="LLM provider")
    embedding_api_key: Optional[str] = Field(None, description="Embedding API key (masked)")
    embedding_model: Optional[str] = Field(None, description="Embedding model")
    embedding_base_url: Optional[str] = Field(None, description="Embedding base URL")
    embedding_provider: Optional[str] = Field(None, description="Embedding provider")
    embedding_dimension: Optional[int] = Field(None, description="Embedding vector dimension")
    audio_model: Optional[str] = Field(None, description="Audio transcription model")
    search_preferences: dict = Field(default_factory=dict, description="Search preferences")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserSettingsUpdate(BaseModel):
    """Request model for updating user settings."""

    llm_api_key: Optional[str] = Field(None, description="LLM API key")
    llm_model: Optional[str] = Field(None, min_length=1, max_length=200, description="LLM model")
    llm_base_url: Optional[str] = Field(None, description="LLM base URL")
    llm_provider: Optional[str] = Field(None, description="LLM provider")
    embedding_api_key: Optional[str] = Field(None, description="Embedding API key")
    embedding_model: Optional[str] = Field(None, min_length=1, max_length=200, description="Embedding model")
    embedding_base_url: Optional[str] = Field(None, description="Embedding base URL")
    embedding_provider: Optional[str] = Field(None, description="Embedding provider")
    embedding_dimension: Optional[int] = Field(None, ge=1, description="Embedding vector dimension")
    audio_model: Optional[str] = Field(None, max_length=200, description="Audio model")
    search_preferences: Optional[dict] = Field(None, description="Search preferences")


# ============================================================================
# SESSION MODELS
# ============================================================================

class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str = Field(..., description="Session token")
    token_type: str = Field(default="bearer", description="Token type")
    user: User = Field(..., description="User information")


class TokenResponse(BaseModel):
    """Response model for token validation."""

    valid: bool = Field(..., description="Whether token is valid")
    user: Optional[User] = Field(None, description="User information if valid")
