@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   PostgreSQL RAG Agent - Diagnostic Tool
echo ==================================================
echo.

echo [*] Checking PostgreSQL service...
sc query "postgres" | findstr /I "postgresql" >nul
if errorlevel 1 (
    echo [ERROR] PostgreSQL service NOT running
    echo.
    echo [*] To start PostgreSQL manually:
    echo     postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    echo     OR use install.bat to initialize database
    echo.
    goto :check_env
) else (
    echo [OK] PostgreSQL service is running
)

:check_env
echo.
echo [*] Checking database configuration...
if not exist .env (
    echo [ERROR] .env file NOT found!
    echo.
    echo [*] Copy from .env.example:
    copy .env.example .env >nul
    echo [OK] .env created
)

echo [*] Checking DATABASE_URL in .env...
findstr /C "DATABASE_URL=" .env >nul
if errorlevel 1 (
    echo [WARNING] DATABASE_URL not found in .env
    echo.
    echo [*] Current DATABASE_URL from .env.example:
    findstr /C "DATABASE_URL=" .env.example >nul
)

echo [*] Checking for port specification...
findstr /C "DATABASE_URL=" .env | findstr /I ":5432"" .env >nul
if errorlevel 1 (
    echo [OK] Port 5432 found in connection string
) else (
    echo [WARNING] Port 5432 NOT found in DATABASE_URL
    echo.
    echo [*] Expected format: postgresql://postgres@localhost:5432/database
)

echo.
echo ==================================================
echo   Diagnostic Results:
echo ==================================================
echo.

if exist postgres\bin\pg_ctl.exe (
    echo [OK] PostgreSQL portable found at postgres\bin\pg_ctl.exe
) else (
    echo [ERROR] PostgreSQL portable NOT found at postgres\bin\pg_ctl.exe
    echo [*] You need to run install.bat first
    goto :end
)

if exist .env (
    echo [OK] .env file exists
) else (
    echo [ERROR] .env file NOT found
    echo [*] Run install.bat to create it
    goto :end
)

:end
echo.
echo [*] Checking if PostgreSQL is running...
tasklist /FI "IMAGENAME" postgres /NH /FI "STATUS" eq "RUNNING" 2>nul
if errorlevel 1 (
    echo [OK] PostgreSQL is running
) else (
    echo [WARNING] PostgreSQL is NOT running
)

echo.
echo ==================================================
echo Press any key to open command prompt for manual testing...
pause >nul
cmd /k
