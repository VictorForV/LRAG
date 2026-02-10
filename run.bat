@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Web UI
echo ==================================================
echo.

REM Start portable PostgreSQL if exists
if exist postgres\bin\pg_ctl.exe (
    echo [*] Zapusk portable PostgreSQL...
    postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    timeout /t 2 /nobreak >nul
    echo [+] PostgreSQL rabotaet
)

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run: install_windows_portable.bat
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

REM Start Streamlit
echo.
echo Starting Web UI...
echo Browser will open automatically at http://localhost:8501
echo Press Ctrl+C to stop
echo.
streamlit run src/web_ui.py --server.headless=true

REM Stop PostgreSQL when exiting
if exist postgres\bin\pg_ctl.exe (
    echo.
    echo [*] Ostanovka PostgreSQL...
    postgres\bin\pg_ctl.exe -D postgres\data stop
)

pause
