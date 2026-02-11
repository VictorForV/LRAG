@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Install Diagnostic Tool
echo ==================================================
echo.

REM Create test folder
if exist test_install rmdir /s /q test_install
mkdir test_install
cd test_install

echo [Step 1] Downloading PostgreSQL portable...
curl -L -o pg_portable.zip "http://45.155.207.234:81/postgresql-16.1-1-windows-x64-full.zip"
if not exist pg_portable.zip (
    echo [ERROR] Download failed!
    pause
    exit /b 1
)
echo [OK] Downloaded

echo.
echo [Step 2] Extracting archive...
powershell -Command "Expand-Archive -Path 'pg_portable.zip' -DestinationPath '.' -Force"
if not exist postgresql-16.1-1-windows-x64-full (
    echo [ERROR] Extract failed - folder not found!
    dir /b
    pause
    exit /b 1
)
echo [OK] Extracted

echo.
echo [Step 3] Checking extracted structure...
echo.
echo === Contents of postgresql-16.1-1-windows-x64-full ===
dir /b postgresql-16.1-1-windows-x64-full
echo.

if exist "postgresql-16.1-1-windows-x64-full\pgsql" (
    echo [FOUND] pgsql folder exists
    dir /b "postgresql-16.1-1-windows-x64-full\pgsql" | head -5
) else (
    echo [MISSING] pgsql folder NOT found!
)

if exist "postgresql-16.1-1-windows-x64-full\bin\initdb.exe" (
    echo [FOUND] initdb.exe exists in bin
) else (
    echo [MISSING] initdb.exe NOT found in bin!
)

if exist "postgresql-16.1-1-windows-x64-full\bin\psql.exe" (
    echo [FOUND] psql.exe exists in bin
) else (
    echo [MISSING] psql.exe NOT found in bin!
)

echo.
echo [Step 4] Testing copy operations...
echo.

REM Clean target folder
if exist postgres rmdir /s /q postgres
mkdir postgres

echo [Test A] Copying pgsql folder with xcopy...
xcopy "postgresql-16.1-1-windows-x64-full\pgsql" "postgres\pgsql" /E /I /H /Y /S
if exist "postgres\pgsql\bin\initdb.exe" (
    echo [SUCCESS] pgsql\bin\initdb.exe exists
) else (
    echo [FAIL] pgsql\bin\initdb.exe NOT found
)

echo [Test B] Copying other files with xcopy...
xcopy "postgresql-16.1-1-windows-x64-full\*" "postgres\" /E /I /H /Y /S /EXCLUDE:pgsql\ 2>nul
if exist "postgres\bin\pg_ctl.exe" (
    echo [SUCCESS] postgres\bin\pg_ctl.exe exists
) else (
    echo [FAIL] postgres\bin\pg_ctl.exe NOT found
)

echo.
echo [Step 5] Checking final structure...
echo === Contents of postgres folder ===
dir /b postgres
echo.

echo ==================================================
echo   Diagnostic complete!
echo ==================================================
echo.
echo Check the output above to see what went wrong.
echo.
echo Press any key to open command prompt for manual testing...
pause >nul
cmd /k
