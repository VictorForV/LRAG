@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo   PostgreSQL Portable Setup
echo ==================================================
echo.

if exist postgres\bin\psql.exe (
    echo [OK] PostgreSQL already installed
    pause
    exit /b 0
)

echo [*] Creating portable PostgreSQL...
echo     This will take a few minutes...
echo.

mkdir postgres\data 2>nul

echo [1/3] Downloading PostgreSQL binaries...
echo     Using PostgreSQL 16.3 for Windows x64
echo.

REM Direct link to PostgreSQL binaries (no auth required)
set "PG_URL=https://get.enterprisedb.com/postgresql/postgresql-16.3-1-windows-x64-binaries.zip"

powershell -Command "$ProgressPreference = 'SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PG_URL%' -OutFile 'pg_binaries.zip'"

if not exist pg_binaries.zip (
    echo [X] Download failed!
    echo.
    echo Try downloading manually:
    echo https://www.enterprisedb.com/download-postgresql-binaries
    echo.
    echo Extract to postgres\ folder
    pause
    exit /b 1
)

echo [2/3] Extracting (this may take a few minutes)...
powershell -Command "Expand-Archive -Path 'pg_binaries.zip' -DestinationPath 'postgres' -Force"
del pg_binaries.zip

REM Find bin folder
set "PG_BIN="
if exist postgres\bin\psql.exe set "PG_BIN=postgres\bin"
for /d %%i in (postgres\postgresql-*) do if not defined PG_BIN set "PG_BIN=%%i\bin"

if not exist "!PG_BIN!\psql.exe" (
    echo [X] PostgreSQL bin not found!
    pause
    exit /b 1
)

echo [3/3] Initializing database...
"!PG_BIN!\initdb.exe" -D postgres\data -U postgres -A trust -E utf8 --locale=C

echo.
echo [OK] PostgreSQL installed successfully!
echo.
pause
