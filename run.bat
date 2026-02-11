@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Web UI
echo ==================================================
echo.

REM Check PostgreSQL status
if exist postgres\bin\pg_ctl.exe (
    echo [*] Checking PostgreSQL status...
    postgres\bin\pg_ctl.exe -D postgres\data status >nul 2>&1
    if errorlevel 0 (
        echo [OK] PostgreSQL already running
    ) else (
        echo [*] Starting PostgreSQL...
        postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
        timeout /t 3 /nobreak >nul
        echo [+] PostgreSQL started
    )
) else (
    echo [WARNING] PostgreSQL not found - run install.bat
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
echo Waiting for backend to start...
echo.

REM Start backend with auto-restart on error
:retry
python -m uvicorn src.web_api:app --host 0.0.0.0 --port 8888
if errorlevel 1 (
    echo.
    echo [*] Backend crashed, restarting in 5 seconds...
    timeout /t 5 /nobreak >nul
    goto retry
)

REM Cleanup - stop PostgreSQL
if exist postgres\bin\pg_ctl.exe (
    echo.
    echo [*] Stopping PostgreSQL...
    postgres\bin\pg_ctl.exe -D postgres\data stop
    echo [OK] PostgreSQL stopped
)

pause
