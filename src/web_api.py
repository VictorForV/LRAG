"""FastAPI application for PostgreSQL RAG Agent."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.api.routes import projects, sessions, messages, documents, chat, settings
from src.api.models.responses import HealthResponse
from src.settings import Settings, load_settings
import asyncpg

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("=" * 50)
    logger.info("Starting FastAPI application")
    logger.info("=" * 50)

    # Startup
    try:
        settings = load_settings()
        logger.info(f"Loaded settings: database={settings.database_name}")

        # Test database connection
        pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await pool.close()
        logger.info("Database connection successful")

    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")


# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

app = FastAPI(
    title="PostgreSQL RAG Agent API",
    description="RAG Knowledge Base with PostgreSQL + pgvector",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# GLOBAL ERROR HANDLERS
# ============================================================================

@app.exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle internal server errors."""
    logger.exception(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error": str(exc)}
    )


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 404 errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Resource not found"}
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Service status
    """
    settings = load_settings()

    # Check database connection
    db_connected = False
    try:
        pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await pool.close()
        db_connected = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        database_connected=db_connected,
        version="1.0.0"
    )


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

app.include_router(projects.router)
app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(settings.router)


# ============================================================================
# STATIC FILES (production)
# ============================================================================

frontend_dist = Path("frontend/dist")

if frontend_dist.exists():
    # Serve frontend static files in production
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend index.html for SPA routing."""
        file_path = frontend_dist / full_path

        # Try to serve the file directly, otherwise fallback to index.html
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        else:
            return FileResponse(str(frontend_dist / "index.html"))

    logger.info("Frontend static files configured")
else:
    logger.info("Frontend dist directory not found - running in API-only mode")


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "PostgreSQL RAG Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.web_api:app",
        host="0.0.0.0",
        port=8888,
        reload=True,
        log_level="info"
    )
