@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo   PostgreSQL Portable Setup
echo ==================================================
echo.

if exist postgres (
    echo [X] Postgres folder already exists
    echo     Delete it first if you want to reinstall
    pause
    exit /b 0
)

echo [*] Creating portable PostgreSQL...
echo     This will take a few minutes...
echo.

mkdir postgres\data

echo [1/3] Downloading PostgreSQL...
powershell -Command "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://sbp.enterprisedb.com/getfile.jsp?fileid=1259243' -OutFile 'pg_binaries.zip' -UserAgent [Microsoft.PowerShell.Commands.PSUserAgent]::Chrome"

if not exist pg_binaries.zip (
    echo [X] Download failed!
    pause
    exit /b 1
)

echo [2/3] Extracting...
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
echo [OK] PostgreSQL ready!
echo.
pause
