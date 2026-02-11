@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Web UI
echo ==================================================
echo.

REM Start portable PostgreSQL
if exist postgres\bin\pg_ctl.exe (
    echo [*] Starting PostgreSQL...
    postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    timeout /t 2 /nobreak >nul
    echo [+] PostgreSQL running
)

REM Activate venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run: install.bat
    pause
    exit /b 1
)

REM Check .env
if not exist .env (
    echo [WARNING] .env not found
    echo.
)

set PYTHONPATH=%~dp0

echo.
echo ==================================================
echo   Starting Web Server...
echo ==================================================
echo.
echo Browser: http://localhost:8888
echo Press Ctrl+C to stop
echo.

python -m uvicorn src.web_api:app --host 0.0.0.0 --port 8888

REM Stop PostgreSQL
if exist postgres\bin\pg_ctl.exe (
    postgres\bin\pg_ctl.exe -D postgres\data stop
)

pause
