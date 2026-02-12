@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==================================================
echo   Database Initialization
echo ==================================================
echo.

REM Find psql.exe
if exist "postgres\pgsql\bin\psql.exe" (
    set "PSQL=postgres\pgsql\bin\psql.exe"
) else if exist "postgres\bin\psql.exe" (
    set "PSQL=postgres\bin\psql.exe"
) else (
    echo [ERROR] psql.exe not found!
    pause
    exit /b 1
)

echo [*] Checking PostgreSQL connection...
"!PSQL!" -U postgres -c "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL is not running!
    echo [*] Starting PostgreSQL...
    if exist "postgres\pgsql\bin\pg_ctl.exe" (
        postgres\pgsql\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    ) else if exist "postgres\bin\pg_ctl.exe" (
        postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    )
    timeout /t 3 /nobreak >nul
    echo [OK] PostgreSQL started
)

echo.
echo [*] Applying database schema...
"!PSQL!" -U postgres -d rag_kb -f src\schema.sql

if errorlevel 1 (
    echo [ERROR] Schema application failed!
    pause
    exit /b 1
)

echo [OK] Database initialized successfully!
echo.
pause
