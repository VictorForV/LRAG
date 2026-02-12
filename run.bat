@echo off
setlocal enabledelayedexpansion
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

REM Check PostgreSQL is actually accepting connections
echo [*] Checking PostgreSQL connection...
if exist "postgres\pgsql\bin\psql.exe" (
    set "PSQL=postgres\pgsql\bin\psql.exe"
) else if exist "postgres\bin\psql.exe" (
    set "PSQL=postgres\bin\psql.exe"
) else (
    echo [WARN] psql.exe not found, skipping connection check
)

if defined PSQL (
    "!PSQL!" -U postgres -c "SELECT 1;" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] PostgreSQL is not responding on port 5432
        echo [*] Trying to start PostgreSQL...
        if exist "postgres\pgsql\bin\pg_ctl.exe" (
            postgres\pgsql\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
            timeout /t 3 /nobreak >nul
        ) else if exist "postgres\bin\pg_ctl.exe" (
            postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
            timeout /t 3 /nobreak >nul
        )
        echo [OK] PostgreSQL restarted
    ) else (
        echo [OK] PostgreSQL is responding
    )
)

echo.
echo [*] Starting backend...
echo [*] Logs will appear below...
echo.

REM Activate virtual environment and run uvicorn
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn src.web_api:app --host 0.0.0.0 --port 8888
) else if exist "python\python.exe" (
    python\python.exe -m uvicorn src.web_api:app --host 0.0.0.0 --port 8888
) else (
    echo [ERROR] Python not found in .venv\Scripts\ or python\
    pause
    exit /b 1
)

if errorlevel 1 (
    echo.
    echo [ERROR] Backend failed to start!
    echo.
    pause
)