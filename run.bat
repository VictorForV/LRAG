@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   Starting RAG Application
echo ==================================================
echo.

REM Check if PostgreSQL is running using pg_ctl
pg_ctl.exe status -D postgres\data >nul 2>&1
if errorlevel 0 (
    echo [INFO] PostgreSQL is already running
) else (
    echo [*] PostgreSQL not running, starting...
    pg_ctl.exe -D postgres\data -l postgres\log.txt start
    timeout /t 2 /nobreak >nul
    echo [OK] PostgreSQL started
)

REM Start FastAPI backend
echo [*] Starting backend...
start "" python -m uvicorn src.web_api:app --host 0.0.0.0 --port 8888" /B

echo.
echo ==================================================
echo   Application started!
echo ==================================================
echo.
echo Backend: http://localhost:8888
echo.
echo Press Ctrl+C to stop...
pause >nul