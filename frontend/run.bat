@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Production
echo ==================================================
echo.

REM Activate venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found!
    pause
    exit /b 1
)

REM Check .env
if not exist .env (
    echo [WARNING] .env not found
)

REM ========================================
REM IMPORTANT: Production mode ONLY
REM ========================================

REM Check if frontend is built
if not exist frontend\dist (
    echo.
    echo ==================================================
    echo [ERROR] Frontend not built!
    echo ==================================================
    echo.
    echo This is PRODUCTION mode.
    echo Please run one of:
    echo   1. update.bat  - to build from source
    echo   2. cd frontend ^&^& npm run build
    echo.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo Starting Production Server
echo ==================================================
echo.
echo Application: http://localhost:8888
echo Press Ctrl+C to stop
echo.
echo ==================================================

REM Single server (FastAPI serves built frontend)
uvicorn src.web_api:app --host 0.0.0.0 --port 8888

pause
