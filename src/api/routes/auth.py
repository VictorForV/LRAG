"""Authentication routes for login, logout, and user management."""

import logging
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.api.models.auth import User, UserLogin, LoginResponse, TokenResponse, UserSettings, UserSettingsUpdate
from src.api.dependencies import get_db_pool
from src.settings import Settings
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# Session configuration
SESSION_EXPIRE_DAYS = 30


# ============================================================================
# UTILITY FUNCTIONS
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


# ============================================================================
# DEPENDENCY: GET CURRENT USER
# ============================================================================

async def get_current_user_dep(
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


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLogin,
    response: Response,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> LoginResponse:
    """
    Authenticate user and create session.

    Args:
        credentials: Login credentials
        response: FastAPI response for setting cookies
        pool: Database connection pool

    Returns:
        Login response with token and user info

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Find user by username
        row = await pool.fetchrow(
            """SELECT id, username, password_hash, created_at, updated_at
               FROM users WHERE username = $1""",
            credentials.username.lower()
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Verify password
        stored_hash = row["password_hash"]
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')

        password_bytes = credentials.password.encode('utf-8')

        if not bcrypt.checkpw(password_bytes, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Generate session token
        session_token = secrets.token_urlsafe(32)
        token_hash = hashlib_sha256(session_token)

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRE_DAYS)

        # Store session in database
        session_id = await pool.fetchval(
            """INSERT INTO user_sessions (user_id, token_hash, expires_at)
               VALUES ($1, $2, $3) RETURNING id""",
            row["id"], token_hash, expires_at
        )

        # Set HTTP-only cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False,  # Set True in production with HTTPS
            samesite="lax",
            max_age=SESSION_EXPIRE_DAYS * 24 * 60 * 60,
            path="/"
        )

        user = User(
            id=str(row["id"]),
            username=row["username"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

        logger.info(f"User logged in: {row['username']}")

        return LoginResponse(
            access_token=session_token,
            token_type="bearer",
            user=user
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {e}"
        )


# ============================================================================
# LOGOUT
# ============================================================================

@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> dict:
    """
    Logout user and delete session.

    Args:
        response: FastAPI response for clearing cookies
        request: FastAPI request to read cookie
        pool: Database connection pool

    Returns:
        Success message
    """
    try:
        # Get session token from cookie
        session_token = request.cookies.get("session_token")

        if session_token:
            token_hash = hashlib_sha256(session_token)

            # Delete session from database
            await pool.execute(
                "DELETE FROM user_sessions WHERE token_hash = $1",
                token_hash
            )

            logger.info(f"User logged out (token deleted)")

        # Clear cookie
        response.delete_cookie(
            key="session_token",
            path="/",
            httponly=True,
            samesite="lax"
        )

        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.exception(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {e}"
        )


# ============================================================================
# GET CURRENT USER
# ============================================================================

@router.get("/me", response_model=User)
async def get_current_user_info(
    user: User = Depends(get_current_user_dep)
) -> User:
    """
    Get current authenticated user information.

    Args:
        user: Current user from dependency

    Returns:
        Current user information
    """
    return user


# ============================================================================
# VERIFY TOKEN
# ============================================================================

@router.get("/verify", response_model=TokenResponse)
async def verify_token(
    request: Request,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> TokenResponse:
    """
    Verify session token and return user info if valid.

    Args:
        request: FastAPI request to read cookie
        pool: Database connection pool

    Returns:
        Token validation response
    """
    try:
        # Get session token from cookie
        session_token = request.cookies.get("session_token")

        if not session_token:
            return TokenResponse(valid=False, user=None)

        token_hash = hashlib_sha256(session_token)

        # Look up session
        row = await pool.fetchrow(
            """SELECT us.expires_at, u.id, u.username, u.created_at, u.updated_at
               FROM user_sessions us
               JOIN users u ON us.user_id = u.id
               WHERE us.token_hash = $1 AND us.expires_at > NOW()""",
            token_hash
        )

        if not row:
            return TokenResponse(valid=False, user=None)

        user = User(
            id=str(row["id"]),
            username=row["username"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

        return TokenResponse(valid=True, user=user)

    except Exception as e:
        logger.exception(f"Token verification error: {e}")
        return TokenResponse(valid=False, user=None)


# ============================================================================
# USER SETTINGS
# ============================================================================

@router.get("/settings", response_model=UserSettings)
async def get_user_settings(
    user: User = Depends(get_current_user_dep),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> UserSettings:
    """
    Get current user's settings.

    Args:
        user: Current user from dependency
        pool: Database connection pool

    Returns:
        User settings

    Raises:
        HTTPException: If settings not found
    """
    try:
        row = await pool.fetchrow(
            """SELECT id, user_id, llm_api_key, llm_model, llm_base_url, llm_provider,
                      embedding_api_key, embedding_model, embedding_base_url, embedding_provider,
                      embedding_dimension, audio_model, http_proxy_host, http_proxy_port,
                      http_proxy_username, http_proxy_password, search_preferences, created_at, updated_at
               FROM user_settings WHERE user_id = $1""",
            user.id
        )

        if not row:
            # Create default settings for user
            row = await pool.fetchrow(
                """INSERT INTO user_settings (user_id)
                   VALUES ($1) RETURNING *""",
                user.id
            )

        # Mask API keys and proxy password in response
        llm_api_key = mask_api_key(row["llm_api_key"])
        embedding_api_key = mask_api_key(row["embedding_api_key"])
        proxy_password = mask_api_key(row["http_proxy_password"])

        # Parse search_preferences from JSONB (can be dict, str, or None)
        search_prefs = row["search_preferences"]
        if isinstance(search_prefs, str):
            import json
            try:
                search_prefs = json.loads(search_prefs)
            except:
                search_prefs = {}
        elif search_prefs is None:
            search_prefs = {}

        return UserSettings(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            llm_api_key=llm_api_key,
            llm_model=row["llm_model"],
            llm_base_url=row["llm_base_url"],
            llm_provider=row["llm_provider"],
            embedding_api_key=embedding_api_key,
            embedding_model=row["embedding_model"],
            embedding_base_url=row["embedding_base_url"],
            embedding_provider=row["embedding_provider"],
            embedding_dimension=row["embedding_dimension"],
            audio_model=row["audio_model"],
            http_proxy_host=row["http_proxy_host"],
            http_proxy_port=row["http_proxy_port"],
            http_proxy_username=row["http_proxy_username"],
            http_proxy_password=proxy_password,
            search_preferences=search_prefs,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    except Exception as e:
        logger.exception(f"Error getting user settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {e}"
        )


@router.put("/settings", response_model=UserSettings)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    user: User = Depends(get_current_user_dep),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> UserSettings:
    """
    Update current user's settings.

    Args:
        settings_update: Settings to update
        user: Current user from dependency
        pool: Database connection pool

    Returns:
        Updated user settings

    Raises:
        HTTPException: If update fails
    """
    try:
        # Build update query
        updates = []
        params = []
        param_count = 1

        for field, value in settings_update.model_dump(exclude_unset=True).items():
            updates.append(f"{field} = ${param_count}")
            params.append(value)
            param_count += 1

        if not updates:
            return await get_user_settings(user, pool)

        params.append(user.id)
        query = f"""UPDATE user_settings SET {', '.join(updates)}, updated_at = NOW()
                   WHERE user_id = ${param_count}
                   RETURNING *"""

        row = await pool.fetchrow(query, *params)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Settings not found"
            )

        # Mask API keys and proxy password in response
        llm_api_key = mask_api_key(row["llm_api_key"])
        embedding_api_key = mask_api_key(row["embedding_api_key"])
        proxy_password = mask_api_key(row["http_proxy_password"])

        # Parse search_preferences from JSONB (can be dict, str, or None)
        search_prefs = row["search_preferences"]
        if isinstance(search_prefs, str):
            import json
            try:
                search_prefs = json.loads(search_prefs)
            except:
                search_prefs = {}
        elif search_prefs is None:
            search_prefs = {}

        return UserSettings(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            llm_api_key=llm_api_key,
            llm_model=row["llm_model"],
            llm_base_url=row["llm_base_url"],
            llm_provider=row["llm_provider"],
            embedding_api_key=embedding_api_key,
            embedding_model=row["embedding_model"],
            embedding_base_url=row["embedding_base_url"],
            embedding_provider=row["embedding_provider"],
            embedding_dimension=row["embedding_dimension"],
            audio_model=row["audio_model"],
            http_proxy_host=row["http_proxy_host"],
            http_proxy_port=row["http_proxy_port"],
            http_proxy_username=row["http_proxy_username"],
            http_proxy_password=proxy_password,
            search_preferences=search_prefs,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating user settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {e}"
        )


# ============================================================================
# DEPENDENCY: GET CURRENT USER
# ============================================================================

async def get_current_user_dep(
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


# ============================================================================
# UTILITY FUNCTIONS
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


def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    """
    Mask API key for display (show first 8 and last 4 characters).

    Args:
        api_key: API key to mask

    Returns:
        Masked API key or None
    """
    if not api_key:
        return None
    if len(api_key) <= 12:
        return "****"
    return f"{api_key[:8]}...{api_key[-4:]}"
