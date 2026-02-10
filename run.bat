@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Web UI
echo ==================================================
echo.

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run: install.bat
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found - using defaults
    echo Please configure settings in the Web UI sidebar
    echo.
)

REM Set Python path
set PYTHONPATH=%~dp0

REM Start Streamlit with full logging
echo.
echo ==================================================
echo   Starting Web UI...
echo ==================================================
echo.
echo Browser will open at: http://localhost:8501
echo Press Ctrl+C to stop
echo.
echo ==================================================
echo   LOGS:
echo ==================================================
echo.

streamlit run src/web_ui.py --server.headless=true

echo.
echo ==================================================
echo   Rabota zavershena
echo ==================================================
pause
